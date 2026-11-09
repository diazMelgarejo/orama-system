#!/usr/bin/env python3
"""Read-only LAN peer pulse: every cycle record whether both directions of the Mac link look healthy.

One cycle runs the peer probe (this host to the peer: health, authenticated status, WebSocket) and the Mac-drop inbox check
(peer to this host: did a drop arrive, is it intact), then updates a small state file. It never sends a message, never flushes the
outbox, never edits trust, and stores only check names and PASS/FAIL words, not addresses or tokens.

Interval: LAN_PEER_PULSE_SECONDS (default 1800 = 30 minutes, floor 300). Run once with --once.
Peer https: PEER_PORTAL_TLS_ENABLED / PEER_CA_FILE / PEER_CA_SHA256 / PEER_PORTAL_TLS_PORT are inherited from the launcher, exactly as
the launcher's own probe uses them; this script only adds --portal-port when https is enabled.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
_SRC_ROOT = SCRIPTS.parents[4] / "src"
if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from orama_system.lan_peer_files import lan_peer_state_dir  # noqa: E402

DEFAULT_INTERVAL = 1800
MIN_INTERVAL = 300
STATE_NAME = "pulse.json"
_REQUIRED_PASS = ("portal-health", "portal-status", "ws-peer")


def interval_seconds(env: dict[str, str] | None = None) -> int:
    """Return the cycle interval from LAN_PEER_PULSE_SECONDS, clamped to the 300 second floor; default 1800."""
    raw = (env if env is not None else os.environ).get("LAN_PEER_PULSE_SECONDS", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_INTERVAL
    except ValueError:
        value = DEFAULT_INTERVAL
    return max(MIN_INTERVAL, value)


def _tls_enabled(env: dict[str, str]) -> bool:
    """True when peer https is switched on in the environment."""
    return (env.get("PEER_PORTAL_TLS_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")


def probe_command(env: dict[str, str]) -> list[str]:
    """Build the read-only probe command, adding the https port only when peer https is enabled."""
    cmd = [sys.executable, "-X", "utf8", str(SCRIPTS / "probe_lan_peer.py"), "--json",
           "--timeout", "4", "--status-timeout", "5", "--ws-timeout", "3"]
    if _tls_enabled(env):
        port = (env.get("PEER_PORTAL_TLS_PORT") or "").strip()
        cmd += ["--portal-port", port if port.isdigit() and 1 <= int(port) <= 65535 else "8443"]
    return cmd


def inbox_command() -> list[str]:
    """Build the Mac-drop inbox check command (JSON, records what it has seen)."""
    return [sys.executable, "-X", "utf8", str(SCRIPTS / "lan_peer_inbox_check.py"), "--json"]


def _run_json(cmd: list[str]) -> dict[str, Any]:
    """Run *cmd* and return its parsed JSON stdout, or an empty dict when it fails or prints something else."""
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
        data = json.loads(done.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def summarize_probe(result: dict[str, Any]) -> dict[str, Any]:
    """Reduce a probe result to check name -> PASS/FAIL plus an overall ok flag (no details, no addresses)."""
    checks = {str(c.get("name")): str(c.get("status")) for c in result.get("checks", []) if isinstance(c, dict)}
    ok = all(checks.get(name) == "PASS" for name in _REQUIRED_PASS)
    return {"ok": ok, "checks": checks}


def update_state(previous: dict[str, Any], probe: dict[str, Any], inbox: dict[str, Any], now: float) -> tuple[dict[str, Any], list[str]]:
    """Fold one cycle into the state and return (new state, human lines for every change worth logging)."""
    prev_w = previous.get("win_to_mac", {}) if isinstance(previous.get("win_to_mac"), dict) else {}
    ok = bool(probe.get("ok"))
    failures = 0 if ok else int(prev_w.get("consecutive_failures", 0)) + 1
    win_to_mac = {
        "ok": ok,
        "checks": probe.get("checks", {}),
        "last_ok_utc": now if ok else prev_w.get("last_ok_utc"),
        "consecutive_failures": failures,
    }
    newest = inbox.get("newest") if isinstance(inbox.get("newest"), dict) else None
    prev_m = previous.get("mac_to_win", {}) if isinstance(previous.get("mac_to_win"), dict) else {}
    status = str(inbox.get("status", "unknown"))
    mac_to_win = {
        "inbox_status": status,
        "mac_drops": int(inbox.get("mac_drops", 0) or 0),
        "new_since_last_pulse": len(inbox.get("new", []) or []),
        "newest_received_utc": newest.get("received_at") if newest else prev_m.get("newest_received_utc"),
        "integrity_failure": status == "integrity-fail",
    }
    lines: list[str] = []
    if previous and bool(prev_w.get("ok")) != ok:
        lines.append("win_to_mac " + ("recovered: probe passes again" if ok else "FAILED: probe no longer passes"))
    if not previous:
        lines.append("win_to_mac " + ("ok" if ok else "not ok") + " (first pulse)")
    if mac_to_win["new_since_last_pulse"]:
        lines.append(f"mac_to_win: {mac_to_win['new_since_last_pulse']} new Mac drop(s) arrived")
    if mac_to_win["integrity_failure"] and not prev_m.get("integrity_failure"):
        lines.append("mac_to_win: a Mac drop failed its integrity check")
    state = {"updated_utc": now, "win_to_mac": win_to_mac, "mac_to_win": mac_to_win}
    return state, lines


def _load_state(path: Path) -> dict[str, Any]:
    """Load the previous state, or an empty dict when it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    """Write the state atomically (temp file then replace) so a reader never sees a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_cycle(state_path: Path, env: dict[str, str] | None = None, now: float | None = None) -> tuple[dict[str, Any], list[str]]:
    """Run one pulse: probe, inbox check, state update; return the new state and the lines to log."""
    environment = dict(os.environ if env is None else env)
    probe = summarize_probe(_run_json(probe_command(environment)))
    inbox = _run_json(inbox_command())
    state, lines = update_state(_load_state(state_path), probe, inbox, time.time() if now is None else now)
    _write_state(state_path, state)
    return state, lines


def main(argv: list[str] | None = None) -> int:
    """Run one cycle with --once, otherwise loop forever at the configured interval; returns the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true", help="run a single cycle, print the state and exit")
    args = parser.parse_args(argv)
    state_path = lan_peer_state_dir() / STATE_NAME
    while True:
        state, lines = run_cycle(state_path)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for line in lines:
            print(f"{stamp} lan-peer-pulse {line}", flush=True)
        if args.once:
            print(json.dumps(state, indent=2))
            return 0
        time.sleep(interval_seconds())


if __name__ == "__main__":
    sys.exit(main())
