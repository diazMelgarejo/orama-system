#!/usr/bin/env python3
"""lm_link_watch.py — persistent Mac↔Win LM Link watcher (gossip + inbox).

Keeps the inference link between the two nodes alive and observable from BOTH
repos (orama-system runs it; Perpetua-Tools reads the same state file via
``scripts/lm_link_status.py``):

- LOCAL backend:  Mac -> Ollama    http://localhost:11434/api/tags
                  Win -> LM Studio http://localhost:1234/v1/models
- PEER backend:   read from ``~/.openclaw/state/last_discovery.json``
  (NEVER hardcoded — Win IP is DHCP-dynamic). Peer Win = LM Studio :1234,
  peer Mac = Ollama :11434.
- STATE:          ``~/.openclaw/state/lm_link.json`` (atomic tmp+rename) —
  the single shared truth both orama and perpetua listen to.
- GOSSIP:         when linked, drop a heartbeat JSON into the local lan_peer
  inbox every LM_LINK_GOSSIP_INTERVAL seconds. Payload carries model ids and
  queue depth only — never prompts, never PII (redaction rule).
- INBOX:          when linked and the local backend is idle, emit one
  ``{"event": "job_available", ...}`` JSON line per queued inbox file to
  stdout; the pulse cron / cline_autoresearcher consumes these. This watcher
  never dispatches inference itself.
- RESILIENCE:     10 consecutive peer failures -> mode "solo-local", recheck
  every LM_LINK_DEGRADED_RETRY seconds (default 900, mirroring
  lan_peer_session.py). Probes never raise; the loop never crashes.

CLI: --once (single cycle, print state, exit) · --status (print state file).
Install persistently on Mac via ``scripts/install_lm_link_watch.sh`` (launchd);
on Windows run ``scripts/lm_link_watch.ps1`` (same state schema).
"""
from __future__ import annotations

import argparse
import json
import os
import platform as _platform
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPTS_DIR.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
from utils.endpoint_policy_core import build_transport_url  # noqa: E402
from utils.model_endpoint_url import ModelEndpointPolicyError, validate_model_endpoint_url  # noqa: E402

STATE_DIR = Path.home() / ".openclaw" / "state"
STATE_FILE = STATE_DIR / "lm_link.json"
DISCOVERY_FILE = STATE_DIR / "last_discovery.json"
INBOX_DIR = STATE_DIR / "lan_peer" / "inbox"

LOOP_INTERVAL = int(os.environ.get("LM_LINK_INTERVAL", "60"))
GOSSIP_INTERVAL = int(os.environ.get("LM_LINK_GOSSIP_INTERVAL", "300"))
DEGRADED_RETRY = int(os.environ.get("LM_LINK_DEGRADED_RETRY", "900"))
MAX_PEER_FAILURES = 10
PROBE_TIMEOUT = 5.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_platform() -> str:
    return "windows" if _platform.system().lower().startswith("win") else "macos"


def _probe(url: str) -> tuple[bool, list[str]]:
    """Probe an inference endpoint; return (up, model_ids). Never raises."""
    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return False, []
    try:
        if "models" in body:  # ollama /api/tags
            return True, [m.get("name", "?") for m in body["models"]][:12]
        if "data" in body:  # lm studio /v1/models
            return True, [m.get("id", "?") for m in body["data"]][:12]
    except Exception:
        pass
    return True, []


def local_url(plat: str) -> str:
    return ("http://localhost:1234/v1/models" if plat == "windows"
            else "http://localhost:11434/api/tags")


def peer_url(plat: str) -> str | None:
    """Resolve the peer inference endpoint from discovery state. Never hardcode."""
    try:
        d = json.loads(DISCOVERY_FILE.read_text(encoding="utf-8"))
        eps = d.get("endpoints", {})
        if plat == "windows":
            ip = eps.get("mac", {}).get("ip", "")
            if not ip or ip == "localhost":
                return None  # Mac IP unknown from Win side; ps1 handles better
            base = build_transport_url(ip, 11434)
            return _approved_peer_url(base, "/api/tags")
        ip = eps.get("win", {}).get("ip", "")
        if not ip:
            return None
        base = build_transport_url(ip, 1234)
        return _approved_peer_url(base, "/v1/models")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
        return None


def _approved_peer_url(base_url: str | None, path: str) -> str | None:
    """Return a policy-approved peer endpoint, or no endpoint on rejection."""
    if base_url is None:
        return None
    try:
        return f"{validate_model_endpoint_url(base_url)}{path}"
    except ModelEndpointPolicyError:
        return None


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), suffix=".lmlink.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
        os.replace(tmp, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _local_idle(plat: str) -> bool:
    """Best-effort idle check; reuse cline_autoresearcher when importable."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cline_autoresearcher import local_backend_idle  # type: ignore
        return bool(local_backend_idle(plat).get("idle", False))
    except Exception:
        return True  # reachable == assumed ready


def queue_files() -> list[Path]:
    if not INBOX_DIR.is_dir():
        return []
    return sorted(p for p in INBOX_DIR.glob("*.md") if not p.name.startswith("gossip-"))


def drop_gossip(plat: str, models: list[str], depth: int) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"ts": _now_iso(), "platform": plat,
               "local_model_ids": models, "queue_depth": depth}
    (INBOX_DIR / f"gossip-{plat}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")


def cycle(prev: dict) -> dict:
    plat = detect_platform()
    local_up, models = _probe(local_url(plat))
    purl = peer_url(plat)
    peer_up = _probe(purl)[0] if purl else False

    fails = 0 if peer_up else int(prev.get("consecutive_peer_failures", 0)) + 1
    if peer_up and local_up:
        mode = "linked"
    elif local_up:
        mode = "solo-local" if fails >= MAX_PEER_FAILURES else "peer-degraded"
    else:
        mode = "down"

    state = {
        "schema": 1, "platform": plat, "local_up": local_up, "peer_up": peer_up,
        "peer_url": purl or "", "mode": mode,
        "consecutive_peer_failures": fails,
        "last_change_iso": (_now_iso() if mode != prev.get("mode") else
                            prev.get("last_change_iso", _now_iso())),
        "last_gossip_iso": prev.get("last_gossip_iso", ""),
        "updated_iso": _now_iso(),
    }

    if mode == "linked":
        last = prev.get("last_gossip_iso", "")
        due = True
        if last:
            try:
                dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                due = (datetime.now(timezone.utc) - dt).total_seconds() >= GOSSIP_INTERVAL
            except Exception:
                pass
        q = queue_files()
        if due:
            drop_gossip(plat, models, len(q))
            state["last_gossip_iso"] = _now_iso()
        if q and _local_idle(plat):
            for p in q:
                print(json.dumps({"event": "job_available", "file": p.name,
                                  "platform": plat, "ts": _now_iso()}), flush=True)

    save_state(state)
    return state


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--once", action="store_true", help="one cycle, print state, exit")
    ap.add_argument("--status", action="store_true", help="print current state file")
    args = ap.parse_args(argv)

    if args.status:
        print(json.dumps(load_state(), indent=2, sort_keys=True))
        return 0
    if args.once:
        print(json.dumps(cycle(load_state()), indent=2, sort_keys=True))
        return 0

    state = load_state()
    while True:
        try:
            state = cycle(state)
        except Exception as exc:  # the loop must never die
            print(json.dumps({"event": "watch_error", "error": str(exc)[:200],
                              "ts": _now_iso()}), flush=True)
        sleep_for = DEGRADED_RETRY if state.get("mode") == "solo-local" else LOOP_INTERVAL
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
