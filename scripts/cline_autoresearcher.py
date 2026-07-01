#!/usr/bin/env python3
"""
cline_autoresearcher.py — ClinePass AutoResearcher resilience controller.

When the platform's native gateway (Hermes on Windows, OpenClaw on macOS) is
paused, not running, or rate-limited/quota-reached, the local Cline Bot takes
over as AutoResearcher — dispatching to the local coder backend (LM Studio
Win / Ollama Mac) directly when it's idle, falling back to ClinePass credits
(the `cline` CLI itself) if the local backend attempt fails.

Peer resilience (Mac<->Win co-orchestration) is delegated to the existing
lan_peer_session.py state machine: 10x consecutive peer-unreachable failures
demote to solo mode; solo mode re-checks the peer every 15 minutes
(LAN_PEER_DEGRADED_RETRY_SECONDS, default 900s).

Usage:
    python scripts/cline_autoresearcher.py --platform windows --check --json
    python scripts/cline_autoresearcher.py --platform macos --status --json
    python scripts/cline_autoresearcher.py --platform windows --dispatch --task "..."
"""
from __future__ import annotations

import argparse
import json
import os
import platform as _platform_mod
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

LMS_WIN_ENDPOINT = os.getenv("LM_STUDIO_WIN_ENDPOINTS", "http://localhost:1234").split(",")[0].strip()
LMS_WIN_MODEL = os.getenv(
    "LM_STUDIO_WIN_MODEL",
    "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2",
)
LMS_API_KEY = os.getenv("LM_STUDIO_API_TOKEN", "lm-studio")
OLLAMA_MAC_ENDPOINT = os.getenv("OLLAMA_MAC_ENDPOINT", "http://127.0.0.1:11434")
OLLAMA_MAC_MODEL = os.getenv("OLLAMA_MAC_MODEL", "qwen3.5:9b-nvfp4")

WIN_PULSE_LOCK = Path.home() / ".openclaw" / "state" / "lan_peer" / "win_pulse.lock"
WIN_COORD_PAUSE_FILE = Path.home() / ".openclaw" / "state" / "lan_peer" / "coord_pulse_pause.json"
MAC_PULSE_LOCK = Path.home() / ".openclaw" / "state" / "lan_peer" / "mac_pulse.lock"
MAC_GATEWAY_PAUSE_FILE = Path.home() / ".openclaw" / "state" / "lan_peer" / "openclaw_gateway_pause.json"

_LAN_PEER_SESSION = (
    REPO_ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "lan_peer_session.py"
)


# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform() -> str:
    if os.name == "nt" or _platform_mod.system() == "Windows":
        return "windows"
    return "macos"


def _is_windows(plat: Optional[str] = None) -> bool:
    return (plat or detect_platform()) == "windows"


# ── Cline CLI discovery ───────────────────────────────────────────────────────

def _find_cline() -> Optional[str]:
    bin_name = "cline.exe" if _is_windows() else "cline"
    found = shutil.which(bin_name)
    if found:
        return found
    if not _is_windows():
        found = shutil.which("cline")
        if found:
            return found
    candidates = []
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "cline" / "cline.exe")
        candidates.append(Path(local_appdata) / "cline" / "bin" / "cline.exe")
    home = Path.home()
    candidates.append(home / ".local" / "bin" / "cline")
    candidates.append(home / "bin" / "cline")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def cline_available() -> Dict[str, Any]:
    cline_bin = _find_cline()
    if not cline_bin:
        return {"available": False, "bin": None, "reason": "cline CLI not found on PATH or known install dirs"}
    return {"available": True, "bin": cline_bin, "reason": "cline CLI found"}


# ── Hermes CLI discovery (Windows gateway) ────────────────────────────────────

def _find_hermes() -> Optional[str]:
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        return hermes_bin
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        scripts_dir = Path(local_appdata) / "hermes" / "hermes-agent" / "venv" / "Scripts"
        for name in ("hermes.exe", "hermes"):
            candidate = scripts_dir / name
            if candidate.exists():
                return str(candidate)
    hermes_home = os.getenv("HERMES_HOME")
    if hermes_home:
        for rel in (
            Path("hermes-agent") / "venv" / "Scripts" / "hermes.exe",
            Path("hermes-agent") / "venv" / "bin" / "hermes",
        ):
            candidate = Path(hermes_home) / rel
            if candidate.exists():
                return str(candidate)
    return None


# ── Gateway status (per platform) ─────────────────────────────────────────────

def _read_pause_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"paused": False}
    try:
        # utf-8-sig: PowerShell's Set-Content -Encoding UTF8 writes a BOM;
        # plain utf-8 leaves it in the string and json.loads chokes on it,
        # silently falling to the except branch below (paused: False) --
        # exactly the class of bug documented elsewhere this session.
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"paused": False}


def _hermes_gateway_running() -> bool:
    hermes_bin = _find_hermes()
    if not hermes_bin:
        return False
    try:
        proc = subprocess.run(
            [hermes_bin, "gateway", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return "Gateway is running" in (proc.stdout or "")
    except Exception:
        return False


def _openclaw_gateway_running() -> bool:
    """Best-effort process probe for the OpenClaw gateway on macOS."""
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "openclaw"],
            capture_output=True, text=True, timeout=5,
        )
        return bool((proc.stdout or "").strip())
    except Exception:
        return False


def gateway_status(plat: Optional[str] = None) -> Dict[str, Any]:
    """Returns {paused, running, rate_limited, reason} for the platform's native gateway."""
    plat = plat or detect_platform()
    if _is_windows(plat):
        pause = _read_pause_file(WIN_COORD_PAUSE_FILE)
        running = _hermes_gateway_running()
        return {
            "paused": bool(pause.get("paused", False)),
            "running": running,
            "rate_limited": False,
            "reason": pause.get("reason", ""),
            "gateway": "hermes",
        }
    pause = _read_pause_file(MAC_GATEWAY_PAUSE_FILE)
    running = _openclaw_gateway_running()
    return {
        "paused": bool(pause.get("paused", False)),
        "running": running,
        "rate_limited": False,
        "reason": pause.get("reason", ""),
        "gateway": "openclaw",
    }


# ── Local backend idle probe (per platform) ───────────────────────────────────

def _probe_http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def local_backend_idle(plat: Optional[str] = None) -> Dict[str, Any]:
    """Returns {idle, reachable, reason} for the platform's local coder backend."""
    plat = plat or detect_platform()
    if _is_windows(plat):
        reachable = _probe_http_ok(f"{LMS_WIN_ENDPOINT}/v1/models")
        if not reachable:
            return {"idle": False, "reachable": False, "reason": "LM Studio Win not reachable"}
        if WIN_PULSE_LOCK.exists():
            return {"idle": False, "reachable": True, "reason": "GPU lock held (win_pulse.lock)"}
        return {"idle": True, "reachable": True, "reason": "LM Studio Win idle"}

    reachable = _probe_http_ok(f"{OLLAMA_MAC_ENDPOINT}/api/tags")
    if not reachable:
        return {"idle": False, "reachable": False, "reason": "ollama not reachable"}
    if MAC_PULSE_LOCK.exists():
        return {"idle": False, "reachable": True, "reason": "coder lock held (mac_pulse.lock)"}
    return {"idle": True, "reachable": True, "reason": "ollama idle"}


# ── Fallback decision ─────────────────────────────────────────────────────────

def _fallback_reason(
    gw: Dict[str, Any], backend: Dict[str, Any], cline: Dict[str, Any], should_fallback: bool
) -> str:
    if not should_fallback:
        if gw.get("running") and not gw.get("paused") and not gw.get("rate_limited"):
            return "gateway running — no fallback needed"
        if not backend.get("idle", False):
            return f"local backend not idle: {backend.get('reason', '')}"
        if not cline.get("available", False):
            return f"Cline unavailable: {cline.get('reason', '')}"
        return "fallback inactive"
    return (
        "ClinePass fallback active — "
        f"gateway paused={gw.get('paused')} running={gw.get('running')} "
        f"rate_limited={gw.get('rate_limited')}, local backend idle, Cline available"
    )


def should_fallback_to_cline(plat: Optional[str] = None) -> Dict[str, Any]:
    plat = plat or detect_platform()
    gw = gateway_status(plat)
    backend = local_backend_idle(plat)
    cline = cline_available()

    gateway_down = bool(gw.get("paused")) or (not gw.get("running")) or bool(gw.get("rate_limited"))
    fallback = gateway_down and bool(backend.get("idle")) and bool(cline.get("available"))

    return {
        "should_fallback": fallback,
        "reason": _fallback_reason(gw, backend, cline, fallback),
        "gateway": gw,
        "local_backend": backend,
        "cline": cline,
        "platform": plat,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

def dispatch_cline(task: str, plat: Optional[str] = None) -> Dict[str, Any]:
    """Run the `cline` CLI directly (ClinePass credits tier)."""
    cline = cline_available()
    if not cline.get("available"):
        return {"ok": False, "output": cline.get("reason", "cline unavailable"), "elapsed": 0}
    t0 = time.time()
    try:
        proc = subprocess.run(
            [cline["bin"], "task", task],
            capture_output=True, text=True, timeout=300, cwd=str(REPO_ROOT),
        )
        elapsed = time.time() - t0
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"ok": proc.returncode == 0, "output": output, "elapsed": elapsed}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "cline task timed out (5min)", "elapsed": time.time() - t0}
    except Exception as exc:
        return {"ok": False, "output": str(exc), "elapsed": time.time() - t0}


def dispatch_autoresearcher(plat: str, task: str) -> Dict[str, Any]:
    """Two-tier ClinePass AutoResearcher dispatch.

    Tier 1 ("local-backend"): Cline is configured with the local coder backend
    (LM Studio Win / Ollama Mac) as its preferred provider — a first
    successful dispatch_cline() call means Cline resolved the task against
    the local model, not paid credits.
    Tier 2 ("cline-pass-credits"): if the first attempt fails (local backend
    dropped, model unloaded mid-task, etc.), retry once — Cline's own
    provider fallback chain (cline-workspace.json) may route the retry to
    ClinePass-hosted credits instead.
    """
    check = should_fallback_to_cline(plat)
    if not check["should_fallback"]:
        return {
            "ok": False,
            "fallback_active": False,
            "output": f"ClinePass AutoResearcher fallback is not active: {check['reason']}",
        }

    local_attempt = dispatch_cline(task, plat)
    if local_attempt.get("ok"):
        return {
            "ok": True,
            "fallback_active": True,
            "fallback_tier": "local-backend",
            "output": local_attempt.get("output", ""),
            "elapsed": local_attempt.get("elapsed"),
        }

    cline_attempt = dispatch_cline(task, plat)
    return {
        "ok": bool(cline_attempt.get("ok")),
        "fallback_active": True,
        "fallback_tier": "cline-pass-credits",
        "output": cline_attempt.get("output", ""),
        "elapsed": cline_attempt.get("elapsed"),
        "local_backend_attempt": local_attempt,
    }


# ── Peer session (co-orchestration resilience) ────────────────────────────────

def peer_session_status() -> Dict[str, Any]:
    if not _LAN_PEER_SESSION.exists():
        return {"ok": False, "mode": "unknown", "failure_count": 0, "max_failures": 10}
    try:
        proc = subprocess.run(
            [sys.executable, str(_LAN_PEER_SESSION), "status"],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(proc.stdout)
    except Exception:
        return {"ok": False, "mode": "unknown", "failure_count": 0, "max_failures": 10}


# ── Full status ────────────────────────────────────────────────────────────────

def full_status(plat: Optional[str] = None) -> Dict[str, Any]:
    plat = plat or detect_platform()
    check = should_fallback_to_cline(plat)
    peer = peer_session_status()
    now = time.time()
    solo_mode = peer.get("mode", "").endswith("-only")
    return {
        "platform": plat,
        "timestamp": now,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "autoresearcher": check,
        "peer_session": peer,
        "solo_mode": solo_mode,
        "peer_unreachable_count": peer.get("failure_count", 0),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["windows", "macos"], default=None)
    parser.add_argument("--check", action="store_true", help="Check whether fallback should be active")
    parser.add_argument("--status", action="store_true", help="Full status incl. peer session")
    parser.add_argument("--dispatch", action="store_true", help="Dispatch a task via ClinePass fallback")
    parser.add_argument("--task", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plat = args.platform or detect_platform()

    if args.dispatch:
        if not args.task:
            print("ERROR: --dispatch requires --task", file=sys.stderr)
            return 2
        result = dispatch_autoresearcher(plat, args.task)
    elif args.status:
        result = full_status(plat)
    else:
        result = should_fallback_to_cline(plat)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)
    return 0 if result.get("ok", True) or result.get("should_fallback") is not None else 1


if __name__ == "__main__":
    sys.exit(main())
