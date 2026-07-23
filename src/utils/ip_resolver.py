#!/usr/bin/env python3
"""
utils/ip_resolver.py — Authoritative LAN IP resolver for orama-system.

Resolves the Windows GPU machine's IP from all available live + cached sources.
Import this instead of hardcoding IPs anywhere in orama-system.

Priority chain (first non-empty value wins):
  1. AlphaClaw gateway    — query running alphaclaw for its known providers
  2. openclaw.json        — kept fresh by discover.py after every successful scan
  3. discovery.json state — last successful probe state (may be older)
  4. PT LAN discovery     — query Perpetua-Tools' lan_discovery.detect_active_tilting_ip()
  5. LM_STUDIO_WIN_ENDPOINTS env var — operator / start.sh override
  6. Hardcoded 192.168.254.108       — confirmed subnet constant, true last resort

Why this chain matters
──────────────────────
• AlphaClaw (P1) is the most live: if it's running it KNOWS its providers are reachable.
• openclaw.json (P2) is authoritative: discover.py writes it after every successful scan.
• discovery.json (P3) may lag if discover.py ran when Win was offline.
• PT (P4) derives the IP from the local subnet via live network probe (Option B) with a 60s timeout.
• env var (P5) lets start.sh / .env override everything.
• Hardcoded (P6) is the true last-resort, never promoted above live data.

Usage
─────
    from utils.ip_resolver import get_win_ip, get_win_lms_url, get_win_ollama_url

    WIN_IP  = get_win_ip()           # "192.168.254.108"
    LMS_URL = get_win_lms_url()      # "http://192.168.254.108:1234"
    OLL_URL = get_win_ollama_url()   # "http://192.168.254.108:11434"

NOTE (2026-07-19 recovery): this file was accidentally truncated to ~98 lines
by commit ed1ad8e9 ("preserve scheme from tilting endpoint"), which replaced
the whole file with only the functions its patch touched and a literal
"rest of file unchanged (truncated for patch safety)" comment — deleting
get_win_ip(), the P1/P2/P3/P5 sources, the TTL cache, the subnet fallback,
and write_win_ip_to_openclaw_json() while portal_server.py still imported
them. Restored here from the last-good version (ec2d525a) with ed1ad8e9's
one legitimate change — scheme preservation through the PT-tilting source
and the URL builders — re-applied on top.
"""
from __future__ import annotations

import functools
import json
import logging
import os
import socket
import time
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("orama.ip_resolver")

# ── Constants ──────────────────────────────────────────────────────────────────

OPENCLAW_JSON       = Path.home() / ".openclaw" / "openclaw.json"
DISCOVERY_JSON      = Path.home() / ".openclaw" / "state" / "discovery.json"
LMS_PORT            = 1234
OLLAMA_PORT         = 11434
ALPHACLAW_GATEWAY   = "http://localhost:18789"
_FALLBACK_WIN_IP    = "192.168.254.103"   # confirmed Windows RTX 3080 — never stale-IPs here

# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_ip_from_url(url: str) -> str:
    """'http://1.2.3.4:1234/v1' → '1.2.3.4' (scheme-aware; rejects loopback)."""
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "::1"):
        return ""
    return host


# ── TTL cache for get_win_ip() ─────────────────────────────────────────────────
# portal_server polls every 10s; we don't want a 2s HTTP probe + file read each time.
# 30s TTL: fresh enough to catch IP changes quickly, cheap enough to run continuously.
_WIN_IP_CACHE: str = ""
_WIN_IP_CACHE_TS: float = 0.0
_WIN_IP_TTL: float = 30.0   # seconds


# ── Priority 1: AlphaClaw gateway ──────────────────────────────────────────────

def _from_alphaclaw() -> str:
    """
    Query AlphaClaw's own models endpoint.  AlphaClaw knows exactly which
    providers are registered and alive — it's the most live source available.

    AlphaClaw gateway (port 18789) returns OpenAI-compat /v1/models listing.
    We look for model IDs that include 'win' or a known Win-only model name
    to identify the Win provider URL from openclaw.json's provider table.
    """
    # Fast path: just read provider URLs from openclaw.json if gateway is alive
    # (gateway being alive = AlphaClaw is running = its provider config is current)
    try:
        req = urllib.request.Request(
            f"{ALPHACLAW_GATEWAY}/v1/models",
            headers={"Authorization": "Bearer " + _alphaclaw_token()},
        )
        with urllib.request.urlopen(req, timeout=2.0) as r:
            r.read()  # just verify 200; IP comes from openclaw.json below
        # AlphaClaw is running → openclaw.json is its live config
        ip = _from_openclaw_json()
        if ip:
            log.debug("ip_resolver P1 (alphaclaw→openclaw.json): %s", ip)
        return ip
    except Exception:
        return ""


def _alphaclaw_token() -> str:
    try:
        cfg = json.loads(OPENCLAW_JSON.read_text())
        return cfg.get("gateway", {}).get("auth", {}).get("token", "lm-studio")
    except Exception:
        return "lm-studio"


# ── Priority 2: openclaw.json ──────────────────────────────────────────────────

def _from_openclaw_json() -> str:
    """
    Read the lmstudio-win provider baseUrl from ~/.openclaw/openclaw.json.
    discover.py patches this file after every successful scan — it's the
    single most authoritative persistent source.
    """
    try:
        cfg = json.loads(OPENCLAW_JSON.read_text())
        url = (cfg
               .get("models", {})
               .get("providers", {})
               .get("lmstudio-win", {})
               .get("baseUrl", ""))
        ip = _extract_ip_from_url(url)
        if ip:
            log.debug("ip_resolver P2 (openclaw.json): %s", ip)
        return ip
    except Exception:
        return ""


# ── Priority 3: discovery.json state ──────────────────────────────────────────

def _from_discovery_json() -> str:
    """
    Read the last successfully probed Win IP from discover.py's state file.
    May lag if Win was offline during the last scan.
    """
    try:
        state = json.loads(DISCOVERY_JSON.read_text())
        ip = state.get("endpoints", {}).get("win", {}).get("ip", "")
        reachable = state.get("endpoints", {}).get("win", {}).get("reachable", False)
        if ip and reachable:
            log.debug("ip_resolver P3 (discovery.json reachable): %s", ip)
            return ip
        if ip:
            log.debug("ip_resolver P3 (discovery.json stale — not reachable): %s — skipped", ip)
        return ""
    except Exception:
        return ""


# ── Priority 4: PT detect_active_tilting_ip ────────────────────────────────────

def _from_pt_tilting() -> str:
    """
    Import PT's lan_discovery.detect_active_tilting_ip() which derives the
    Win IP from the Mac's outbound interface subnet.  Subnet-portable:
    works on 192.168.1.x AND 192.168.254.x without any config.

    Scheme-preserving (ed1ad8e9): detect_active_tilting_ip() may now return a
    full URL with scheme; when it does, the scheme is preserved in the return
    value ("https://1.2.3.4") instead of being stripped to a bare IP.
    """
    import sys as _sys
    _inserted = False
    pt_str = ""
    try:
        _orama_root = Path(__file__).resolve().parents[2]
        _pt_candidates = [
            _orama_root.parent / "perplexity-api" / "Perpetua-Tools",
            Path.home() / "Perpetua-Tools",
        ]
        pt_root = next((p for p in _pt_candidates if p.exists()), None)
        if not pt_root:
            return ""
        pt_str = str(pt_root)
        if pt_str not in _sys.path:
            _sys.path.insert(0, pt_str)
            _inserted = True
        from orchestrator.lan_discovery import detect_active_tilting_ip
        raw = detect_active_tilting_ip()  # now MAY return full URL with scheme
        if not raw:
            return ""

        # Preserve scheme if present
        parsed = urlparse(raw)
        if parsed.scheme and parsed.hostname:
            ip = parsed.hostname
            scheme = parsed.scheme
            result = f"{scheme}://{ip}"
        else:
            ip = _extract_ip_from_url(raw)
            result = ip

        if ip:
            log.debug("ip_resolver P4 (pt-tilting): %s", ip)
        return result

    except Exception:
        return ""
    finally:
        # Remove the path we injected to avoid permanently shadowing other modules
        if _inserted and pt_str in _sys.path:
            _sys.path.remove(pt_str)


# ── Priority 5: env var ────────────────────────────────────────────────────────

def _from_env() -> str:
    """
    Read LM_STUDIO_WIN_ENDPOINTS or WINDOWS_IP env var.
    start.sh exports these after running its own detection chain.
    """
    for key in ("LM_STUDIO_WIN_ENDPOINTS", "LAN_GPU_IP_OVERRIDE", "WINDOWS_IP"):
        val = os.environ.get(key, "").split(",")[0].strip()
        if val:
            if val.startswith("http"):
                ip = _extract_ip_from_url(val)
            else:
                ip = val
            if ip:
                log.debug("ip_resolver P5 (env %s): %s", key, ip)
                return ip
    return ""


# ── Public API ─────────────────────────────────────────────────────────────────

def get_win_ip() -> str:
    """
    Return the Windows GPU machine's LAN IP.
    Runs through all 6 priority levels; never returns empty (falls back to subnet.103).
    Results are TTL-cached (30s) so portal's 10s poll doesn't trigger a 2s HTTP probe
    + file I/O on every single request.  Use invalidate_win_ip_cache() to force refresh.

    Note: the P4 (PT tilting) source is scheme-preserving, so the returned value
    may be "http://<ip>" rather than a bare IP.  get_win_lms_url() /
    get_win_ollama_url() handle both shapes.
    """
    global _WIN_IP_CACHE, _WIN_IP_CACHE_TS
    now = time.monotonic()
    if _WIN_IP_CACHE and (now - _WIN_IP_CACHE_TS) < _WIN_IP_TTL:
        return _WIN_IP_CACHE

    ip = (
        _from_alphaclaw()
        or _from_openclaw_json()
        or _from_discovery_json()
        or _from_pt_tilting()
        or _from_env()
        or _fallback_subnet_103()
    )
    if not ip:
        ip = _FALLBACK_WIN_IP
        log.warning("ip_resolver: all priorities failed — using last-resort %s", ip)

    _WIN_IP_CACHE = ip
    _WIN_IP_CACHE_TS = now
    return ip


def invalidate_win_ip_cache() -> None:
    """Force the next get_win_ip() call to re-probe all sources.

    Clears the cached VALUE as well as the timestamp: with only the
    timestamp reset, `now - 0.0 < TTL` could still hold in the first
    TTL-seconds of the monotonic clock's life, briefly serving a stale
    value (peer-review finding, 2026-07-19 — gemma-4-26b, verified real
    though marginal). Clearing both makes invalidation unconditional.
    """
    global _WIN_IP_CACHE, _WIN_IP_CACHE_TS
    _WIN_IP_CACHE = ""
    _WIN_IP_CACHE_TS = 0.0


def _fallback_subnet_103() -> str:
    """
    Derive subnet from Mac's outbound interface and append .103.
    Subnet-portable: works regardless of network topology.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))   # no packets sent
            local_ip = s.getsockname()[0]
        parts = local_ip.split(".")
        if len(parts) == 4 and not local_ip.startswith("127."):
            win_ip = ".".join(parts[:3]) + ".103"
            log.debug("ip_resolver P6 (subnet.103): local=%s → win=%s", local_ip, win_ip)
            return win_ip
    except Exception:
        pass
    return _FALLBACK_WIN_IP


def get_win_lms_url(port: int = LMS_PORT) -> str:
    """Full LM Studio URL for the Windows machine: http://<win-ip>:1234
    (scheme-aware: preserves an https:// scheme if the resolver returned one)."""
    val = get_win_ip()
    parsed = urlparse(val)
    if parsed.scheme and parsed.hostname:
        return f"{parsed.scheme}://{parsed.hostname}:{port}"
    return f"http://{val}:{port}"


def get_win_ollama_url(port: int = OLLAMA_PORT) -> str:
    """Full Ollama URL for the Windows machine: http://<win-ip>:11434
    (scheme-aware: preserves an https:// scheme if the resolver returned one)."""
    val = get_win_ip()
    parsed = urlparse(val)
    if parsed.scheme and parsed.hostname:
        return f"{parsed.scheme}://{parsed.hostname}:{port}"
    return f"http://{val}:{port}"


# ── Gossip writer (called by discover.py / portal after live probes) ───────────

def write_win_ip_to_openclaw_json(win_ip: str) -> bool:
    """
    Write a freshly-discovered Win IP back into openclaw.json so all
    processes on the next startup pick it up from Priority 2.
    Idempotent: no-op if the IP hasn't changed.
    """
    if not win_ip or win_ip == "localhost" or win_ip.startswith("127."):
        return False
    # win_ip can legitimately arrive scheme-bearing (get_win_ip()'s own
    # documented return shape, e.g. "https://10.1.2.3") -- strip any scheme
    # before building the URL below, or a scheme-bearing input silently
    # produces a broken URL with the scheme duplicated ("http" + "://"
    # + the original "https://10.1.2.3" value, unparsed).
    # Same urlparse(...).hostname pattern already used by get_win_lms_url /
    # get_win_ollama_url for scheme-aware handling.
    parsed = urlparse(win_ip)
    win_host = parsed.hostname if parsed.scheme and parsed.hostname else win_ip
    try:
        cfg = json.loads(OPENCLAW_JSON.read_text())
        providers = cfg.setdefault("models", {}).setdefault("providers", {})
        current_url = providers.get("lmstudio-win", {}).get("baseUrl", "")
        new_url = f"http://{win_host}:{LMS_PORT}/v1"
        if current_url == new_url:
            return False  # already up to date
        providers.setdefault("lmstudio-win", {})["baseUrl"] = new_url
        from datetime import datetime, timezone
        import tempfile
        cfg.setdefault("meta", {})["lastTouchedAt"] = datetime.now(timezone.utc).isoformat()
        # Atomic write: NamedTemporaryFile avoids mktemp TOCTOU race
        with tempfile.NamedTemporaryFile(
            mode="w", dir=OPENCLAW_JSON.parent, suffix=".tmp", delete=False
        ) as tf:
            tf.write(json.dumps(cfg, indent=2))
            tmp = Path(tf.name)
        tmp.replace(OPENCLAW_JSON)
        invalidate_win_ip_cache()   # flush cache so next get_win_ip() reads new value
        log.info("ip_resolver: wrote Win IP %s → openclaw.json", win_ip)
        return True
    except Exception as exc:
        log.warning("ip_resolver: failed to write Win IP to openclaw.json: %s", exc)
        return False


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    print(f"Win IP:      {get_win_ip()}")
    print(f"LMS URL:     {get_win_lms_url()}")
    print(f"Ollama URL:  {get_win_ollama_url()}")
