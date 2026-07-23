#!/usr/bin/env python3
"""Pulse check for replies to the start.ps1 agent comms coordination ask.

Compares current Mac peer inbox + local inbox + job queues against a stored
snapshot and reports only what changed. Run from the orama-system repo root.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("ORAMA_SYSTEM_PATH", "").strip()
    if env:
        return Path(env)
    try:
        top = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(top)
    except Exception:
        return Path(__file__).resolve().parents[1]


def state_path() -> Path:
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".openclaw" / "state" / "lan_peer" / "pulse_start_ps1_agent_comms.json"


def run_json(cmd: list[str], cwd: Path) -> dict:
    try:
        out = subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception as exc:
        return {"error": str(exc)}


def snapshot() -> dict:
    sp = state_path()
    if sp.is_file():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_snapshot(data: dict) -> None:
    sp = state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def file_signature(files: list[dict]) -> dict[str, int]:
    return {f["filename"]: f["received_at"] for f in files if "filename" in f}


def main() -> int:
    root = repo_root()
    scripts = root / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
    lpa = [sys.executable, str(scripts / "lan_peer_assign.py")]

    prev = snapshot()
    curr: dict = {}

    peer = run_json(lpa + ["list", "--peer", "--timeout", "10"], root)
    local = run_json(lpa + ["list"], root)
    win_q = run_json([sys.executable, str(scripts / "win_job_queue.py"), "status"], root)
    mac_q = run_json([sys.executable, str(scripts / "mac_job_queue.py"), "status"], root)

    curr["peer_files"] = file_signature(peer.get("files", []))
    curr["local_files"] = file_signature(local.get("files", []))
    curr["win_queue"] = win_q
    curr["mac_queue"] = mac_q

    prev_peer = prev.get("peer_files", {})
    prev_local = prev.get("local_files", {})

    new_peer = {k: v for k, v in curr["peer_files"].items() if k not in prev_peer}
    new_local = {k: v for k, v in curr["local_files"].items() if k not in prev_local}

    changed = (
        new_peer
        or new_local
        or curr["win_queue"] != prev.get("win_queue")
        or curr["mac_queue"] != prev.get("mac_queue")
    )

    if not changed:
        print("no changes")
        save_snapshot(curr)
        return 0

    out = {
        "changed": True,
        "new_peer_files": new_peer,
        "new_local_files": new_local,
        "win_queue": curr["win_queue"],
        "mac_queue": curr["mac_queue"],
    }
    print(json.dumps(out, indent=2))
    save_snapshot(curr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
