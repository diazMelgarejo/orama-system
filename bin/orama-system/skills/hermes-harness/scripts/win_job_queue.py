#!/usr/bin/env python3
"""win_job_queue.py — sequential Win subagent job queue (one active job per role).

Routes Mac orchestrator inbox assignments to win-coder or win-autoresearcher.
Processes one job at a time per role; LM Studio GPU slot is single-tenant.

Usage:
    python win_job_queue.py enqueue          # scan local inbox → pending queues
    python win_job_queue.py status
    python win_job_queue.py next autoresearcher
    python win_job_queue.py complete autoresearcher --note "dropped gpu-results-h5-cross.md"
    python win_job_queue.py run-once         # claim+print next for each role (no execution)
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

ROLES = ("autoresearcher", "coder")
_QUEUE_PATH = lan_peer_state_dir() / "win_job_queue.json"

# Pending jobs with hard prereqs — pulse and `next` skip until unblocked in coord_pulse.ps1
BLOCKED_PENDING: frozenset[str] = frozenset(
    {
        "win-coder-l1-comms-autoplan-backlog.md",
    }
)

# Topic/filename → role (first match wins)
_ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "autoresearcher",
        re.compile(
            r"(autoresearch/|gpu-run|gpu-done|h5-|h4-|hypothesis)",
            re.I,
        ),
    ),
    (
        "coder",
        re.compile(
            r"(code-review/|bridge|portal-fix|branch-policy|frugal-spawn|coder)",
            re.I,
        ),
    ),
]

_SKIP_TOPICS = re.compile(
    r"(self-improve/|ops/co-orchestration-active|ops/warmup|ops/peer-file|WHERE_TO_LOOK)",
    re.I,
)


def _empty_state() -> dict[str, Any]:
    return {
        role: {"active": None, "pending": [], "done": []}
        for role in ROLES
    }


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
    """Only queue explicit Win subagent task cards from Mac orchestrator."""
    name = filename.lower()
    if name.startswith("win-autoresearcher-") or name.startswith("win-coder-"):
        return True
    if name.startswith("win-autoresearch-") and "gpu" in topic:
        return True
    if source == "mac" and name.startswith("mac-"):
        return False
    if name.startswith("hypothesis-") or name.startswith("code-review-win"):
        return False
    return False


def classify_role(filename: str, topic: str) -> str | None:
    blob = f"{filename} {topic}"
    if _SKIP_TOPICS.search(topic) or _SKIP_TOPICS.search(filename):
        return None
    for role, pattern in _ROLE_RULES:
        if pattern.search(blob):
            return role
    return None


def _priority(meta: dict[str, Any], body: str) -> int:
    m = re.search(r"\*?\*?Priority\*?\*?:\s*(\d+)", body)
    if m:
        return int(m.group(1))
    fanout = str(meta.get("fanout_id") or "")
    if "coord-004" in fanout:
        return 1
    if "coord-003" in fanout:
        return 2
    return 10


def _job_id(filename: str) -> str:
    return filename


def prune_pending(state: dict[str, Any]) -> list[str]:
    """Drop pending jobs that fail is_actionable_assignment (stale inbox noise)."""
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
    known = set()
    for role in ROLES:
        if state[role]["active"]:
            known.add(state[role]["active"]["id"])
        for bucket in ("pending", "done"):
            for item in state[role][bucket]:
                known.add(item["id"])

    added: list[dict[str, Any]] = []
    for meta in list_inbox():
        assignee = str(meta.get("assignee") or "").strip().lower()
        if assignee not in ("win", ""):
            continue
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


def cmd_enqueue(_args: argparse.Namespace) -> int:
    state = load_queue()
    added = enqueue_from_inbox(state)
    save_queue(state)
    print(json.dumps({"added": added, "status": cmd_status_data(state)}, indent=2))
    return 0


def cmd_status_data(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
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


def _claim_next_pending(state: dict[str, Any], role: str) -> dict[str, Any] | None:
    """Pop first actionable pending job (skips BLOCKED_PENDING)."""
    pending: list[dict[str, Any]] = state[role]["pending"]
    for idx, job in enumerate(pending):
        if job["id"] in BLOCKED_PENDING:
            continue
        return pending.pop(idx)
    return None


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
    job = _claim_next_pending(state, role)
    if not job:
        print(
            json.dumps(
                {
                    "status": "idle",
                    "active": None,
                    "note": "pending jobs blocked or empty",
                },
                indent=2,
            )
        )
        return 0
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


def cmd_prune(_args: argparse.Namespace) -> int:
    state = load_queue()
    removed = prune_pending(state)
    save_queue(state)
    print(json.dumps({"removed": removed, "status": cmd_status_data(state)}, indent=2))
    return 0


def cmd_complete_pending(args: argparse.Namespace) -> int:
    """Move a pending job to done without claiming (reconcile already-finished work)."""
    state = load_queue()
    role = args.role
    jid = args.job_id
    found: dict[str, Any] | None = None
    for job in state[role]["pending"]:
        if job["id"] == jid:
            found = job
            break
    if not found:
        raise SystemExit(f"pending job not found: {jid} in {role}")
    state[role]["pending"] = [j for j in state[role]["pending"] if j["id"] != jid]
    found["completed_at"] = int(time.time())
    if args.note:
        found["note"] = args.note
    state[role]["done"].append(found)
    save_queue(state)
    print(json.dumps({"status": "reconciled", "job": found}, indent=2))
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
    """Enqueue then claim next job per role if idle (orchestrator tick)."""
    state = load_queue()
    enqueue_from_inbox(state)
    claimed: dict[str, Any] = {}
    for role in ROLES:
        if state[role]["active"] or not state[role]["pending"]:
            continue
        job = _claim_next_pending(state, role)
        if not job:
            continue
        job["started_at"] = int(time.time())
        state[role]["active"] = job
        claimed[role] = job
    save_queue(state)
    print(json.dumps({"claimed": claimed, "status": cmd_status_data(state)}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Win sequential subagent job queue")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("enqueue", help="Add inbox jobs to pending queues").set_defaults(
        func=cmd_enqueue
    )
    sub.add_parser("prune", help="Remove non-actionable jobs from pending").set_defaults(
        func=cmd_prune
    )
    sub.add_parser("status", help="Show queue state").set_defaults(func=cmd_status)
    sub.add_parser("run-once", help="Enqueue + claim one job per idle role").set_defaults(
        func=cmd_run_once
    )

    nxt = sub.add_parser("next", help="Claim next pending job for role")
    nxt.add_argument("role", choices=ROLES)
    nxt.set_defaults(func=cmd_next)

    done = sub.add_parser("complete", help="Mark active job done")
    done.add_argument("role", choices=ROLES)
    done.add_argument("--note", default="", help="Completion note / deliverable")
    done.set_defaults(func=cmd_complete)

    recon = sub.add_parser("complete-pending", help="Mark a pending job done (reconcile)")
    recon.add_argument("role", choices=ROLES)
    recon.add_argument("job_id", help="Pending job id (filename)")
    recon.add_argument("--note", default="", help="Completion note")
    recon.set_defaults(func=cmd_complete_pending)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
