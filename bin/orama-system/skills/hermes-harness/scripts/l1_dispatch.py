#!/usr/bin/env python3
"""l1_dispatch.py — CLI for local L1 preview/launch via portal :8002 (P5-gated).

Ingredients stub until P5 swarm HITL merges to main. Then calls:
  POST /api/l1/preview
  POST /api/l1/launch
  GET  /api/l1/status/{session_id}
  POST /api/l1/stop

Usage:
    python l1_dispatch.py preview --objective "..." --executor codex
    python l1_dispatch.py launch --preview-id ... --approval-token ...
    python l1_dispatch.py status --session-id ...
    python l1_dispatch.py stop --session-id ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

P5_GATE_MSG = (
    "BLOCKED: P5 swarm HITL not on main yet. "
    "Merge docs/plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md first. "
    "See docs/plans/2026-06-29-intra-machine-l1-comms-execution-plan.md"
)

PORTAL_DEFAULT = "http://127.0.0.1:8002"


def _portal_base() -> str:
    return os.environ.get("PORTAL_URL", PORTAL_DEFAULT).rstrip("/")


def _p5_landed() -> bool:
    """Best-effort: true when control_plane_auth exposes operator payload helpers."""
    try:
        from utils.control_plane_auth import sign_operator_payload  # noqa: F401

        return True
    except ImportError:
        return False


def _post(path: str, body: dict) -> dict:
    url = f"{_portal_base()}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = os.environ.get("ORAMA_CONTROL_PLANE_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {path}: {detail}") from exc


def cmd_preview(args: argparse.Namespace) -> int:
    if not _p5_landed():
        print(P5_GATE_MSG, file=sys.stderr)
        return 2
    body = {
        "objective": args.objective,
        "executor_id": args.executor,
        "transport": {"profile": args.profile, "fanout_count": args.fanout},
    }
    print(json.dumps(_post("/api/l1/preview", body), indent=2))
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    if not _p5_landed():
        print(P5_GATE_MSG, file=sys.stderr)
        return 2
    body = {
        "preview_id": args.preview_id,
        "approval_token": args.approval_token,
    }
    print(json.dumps(_post("/api/l1/launch", body), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not _p5_landed():
        print(P5_GATE_MSG, file=sys.stderr)
        return 2
    url = f"{_portal_base()}/api/l1/status/{args.session_id}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        print(json.dumps(json.loads(resp.read().decode("utf-8")), indent=2))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    if not _p5_landed():
        print(P5_GATE_MSG, file=sys.stderr)
        return 2
    print(json.dumps(_post("/api/l1/stop", {"session_id": args.session_id}), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="L1 local dispatch CLI (portal :8002)")
    sub = p.add_subparsers(dest="cmd", required=True)

    prev = sub.add_parser("preview", help="Build L1 preview (requires P5 on main)")
    prev.add_argument("--objective", required=True)
    prev.add_argument("--executor", default="codex", choices=["codex", "cursor", "hermes", "pt-worker"])
    prev.add_argument("--profile", default="interactive")
    prev.add_argument("--fanout", type=int, default=1)
    prev.set_defaults(func=cmd_preview)

    launch = sub.add_parser("launch", help="Launch approved L1 preview")
    launch.add_argument("--preview-id", required=True)
    launch.add_argument("--approval-token", required=True)
    launch.set_defaults(func=cmd_launch)

    st = sub.add_parser("status", help="Session status")
    st.add_argument("--session-id", required=True)
    st.set_defaults(func=cmd_status)

    stop = sub.add_parser("stop", help="Stop L1 children (not full NUCLEAR)")
    stop.add_argument("--session-id", required=True)
    stop.set_defaults(func=cmd_stop)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
