#!/usr/bin/env python3
"""mac_job_queue.py — sequential Mac orchestrator job queue (one active per role).

Mirrors win_job_queue.py for Mac-side inbox processing: Win deliverables and
mac-* assignment cards. Used by coord_pulse.sh idle gate.

Usage:
    python mac_job_queue.py enqueue
    python mac_job_queue.py status
    python mac_job_queue.py next orchestrator
    python mac_job_queue.py complete orchestrator --note "done"
    python mac_job_queue.py run-once
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from orama_system.lan_peer_files import lan_peer_state_dir, list_inbox, read_inbox_file  # noqa: E402

ROLES = ("orchestrator", "researcher")
_QUEUE_PATH = lan_peer_state_dir() / "mac_job_queue.json"

_SKIP_TOPICS = re.compile(
    r"(ops/co-orchestration-active|ops/warmup|ops/peer-file|WHERE_TO_LOOK)",
    re.I,
)
_SKIP_FILES = re.compile(
    r"(win-cycle-\d+-ack|win-bucket-drain-ack|mac-cycle-\d+-ack)",
    re.I,
)
_RESEARCHER = re.compile(
    r"(autoresearch/|gpu-|hypothesis|h[45]-)",
    re.I,
)


def _empty_state() -> dict[str, Any]:
    return {role: {"active": None, "pending": [], "done": []} for role in ROLES}


def load_queue() -> dict[str, Any]:
    if _QUEUE_PATH.is_file():
        data = json.loads(_QUEUE_PATH.read_text(encoding="utf-8"))
        for role in ROLES:
            data.setdefault(role, {"active": None, "pending": [], "done": []})
        return data
    return _empty_state()


def save_queue(state: dict[str, Any]) -> None:
    _QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _QUEUE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def is_actionable_assignment(filename: str, topic: str, source: str) -> bool:
    """Queue Win→Mac deliverables and explicit mac-* task cards."""
    name = filename.lower()
    if _SKIP_FILES.search(name):
        return False
    if _SKIP_TOPICS.search(topic) or _SKIP_TOPICS.search(filename):
        return False
    if source == "win" and name.startswith("win-"):
        return True
    if name.startswith("mac-orchestrator-") or name.startswith("mac-researcher-"):
        return True
    return False


def classify_role(filename: str, topic: str) -> str | None:
    blob = f"{filename} {topic}"
    if _RESEARCHER.search(blob):
        return "researcher"
    return "orchestrator"


def _priority(meta: dict[str, Any], body: str) -> int:
    m = re.search(r"Priority:\s*(\d+)", body)
    if m:
        return int(m.group(1))
    return 10


def _job_id(filename: str) -> str:
    return filename


def prune_pending(state: dict[str, Any]) -> list[str]:
    removed: list[str] = []
    for role in ROLES:
        kept: list[dict[str, Any]] = []
        for job in state[role]["pending"]:
            filename = str(job.get("filename") or job.get("id") or "")
            topic = str(job.get("topic") or "")
            source = str(job.get("source") or "")
            if is_actionable_assignment(filename, topic, source):
                kept.append(job)
            else:
                removed.append(filename)
        state[role]["pending"] = kept
    return removed


def enqueue_from_inbox(state: dict[str, Any]) -> list[dict[str, Any]]:
    prune_pending(state)
    known: set[str] = set()
    for role in ROLES:
        if state[role]["active"]:
            known.add(state[role]["active"]["id"])
        for bucket in ("pending", "done"):
            for item in state[role][bucket]:
                known.add(item["id"])

    added: list[dict[str, Any]] = []
    for meta in list_inbox():
        filename = str(meta.get("filename") or "")
        topic = str(meta.get("topic") or "")
        source = str(meta.get("source") or "")
        if not is_actionable_assignment(filename, topic, source):
            continue
        role = classify_role(filename, topic)
        if not role:
            continue
        jid = _job_id(filename)
        if jid in known:
            continue
        try:
            body, _ = read_inbox_file(filename)
        except (ValueError, FileNotFoundError):
            body = ""
        job = {
            "id": jid,
            "filename": filename,
            "topic": topic,
            "source": source,
            "fanout_id": meta.get("fanout_id") or "",
            "priority": _priority(meta, body),
            "enqueued_at": int(time.time()),
        }
        state[role]["pending"].append(job)
        known.add(jid)
        added.append({**job, "role": role})
    for role in ROLES:
        state[role]["pending"].sort(key=lambda j: (j["priority"], j["enqueued_at"]))
    return added


def is_idle(state: dict[str, Any] | None = None) -> bool:
    state = state or load_queue()
    for role in ROLES:
        if state[role]["active"] or state[role]["pending"]:
            return False
    return True


def cmd_enqueue(_args: argparse.Namespace) -> int:
    state = load_queue()
    added = enqueue_from_inbox(state)
    save_queue(state)
    print(json.dumps({"added": added, "status": cmd_status_data(state)}, indent=2))
    return 0


def cmd_status_data(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"idle": is_idle(state)}
    for role in ROLES:
        out[role] = {
            "active": state[role]["active"],
            "pending_count": len(state[role]["pending"]),
            "pending": [j["id"] for j in state[role]["pending"]],
            "done_count": len(state[role]["done"]),
        }
    return out


def cmd_status(_args: argparse.Namespace) -> int:
    state = load_queue()
    print(json.dumps(cmd_status_data(state), indent=2))
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    role = args.role
    if role not in ROLES:
        raise SystemExit(f"role must be one of {ROLES}")
    state = load_queue()
    if state[role]["active"]:
        print(json.dumps({"status": "busy", "active": state[role]["active"]}, indent=2))
        return 0
    if not state[role]["pending"]:
        print(json.dumps({"status": "idle", "active": None}, indent=2))
        return 0
    job = state[role]["pending"].pop(0)
    job["started_at"] = int(time.time())
    state[role]["active"] = job
    save_queue(state)
    body, meta = read_inbox_file(job["filename"])
    print(
        json.dumps(
            {"status": "claimed", "job": job, "meta": meta, "body_preview": body[:500]},
            indent=2,
        )
    )
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    role = args.role
    state = load_queue()
    active = state[role]["active"]
    if not active:
        raise SystemExit(f"no active job for {role}")
    active["completed_at"] = int(time.time())
    if args.note:
        active["note"] = args.note
    state[role]["done"].append(active)
    state[role]["active"] = None
    save_queue(state)
    print(json.dumps({"status": "completed", "job": active}, indent=2))
    return 0


def cmd_run_once(_args: argparse.Namespace) -> int:
    state = load_queue()
    enqueue_from_inbox(state)
    claimed: dict[str, Any] = {}
    for role in ROLES:
        if state[role]["active"] or not state[role]["pending"]:
            continue
        job = state[role]["pending"].pop(0)
        job["started_at"] = int(time.time())
        state[role]["active"] = job
        claimed[role] = job
    save_queue(state)
    print(json.dumps({"claimed": claimed, "status": cmd_status_data(state)}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mac sequential orchestrator job queue")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("enqueue").set_defaults(func=cmd_enqueue)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("run-once").set_defaults(func=cmd_run_once)

    nxt = sub.add_parser("next")
    nxt.add_argument("role", choices=ROLES)
    nxt.set_defaults(func=cmd_next)

    done = sub.add_parser("complete")
    done.add_argument("role", choices=ROLES)
    done.add_argument("--note", default="")
    done.set_defaults(func=cmd_complete)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
