#!/usr/bin/env python3
"""lan_peer_send.py -- send ONE file to the LAN peer and report delivery evidence (the supported send helper).

Wraps ``lan_peer_assign.py drop --peer``. It adds what a bare drop lacks: it reads the peer-TLS and token settings only
from its own environment (it never opens an env or credential file), passes the child process just that allowlist
plus basic process settings, masks addresses and token-like strings in its output, and treats the drop's own JSON as
the only evidence of delivery (``ok``, ``received_at`` and a byte count equal to the file size). A failed send leaves a queued outbox record; this tool
never resolves or flushes it: reconcile that record explicitly with ``lan_peer_assign.py outbox-resolve``.

Exit codes: 0 delivered with matching evidence, 2 not delivered. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_ENV = (
    "PEER_CA_FILE", "PEER_PORTAL_TLS_ENABLED", "PEER_PORTAL_TLS_PORT", "PEER_CA_SHA256",
    "ORAMA_CONTROL_PLANE_TOKEN", "ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "ORAMA_CONTROL_PLANE_TOKEN_PEER",
)
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
_ASSIGN = Path(__file__).resolve().parent / "lan_peer_assign.py"


def mask(text: str) -> str:
    """Hide IPv4 addresses and long token-like strings."""
    return _TOKEN.sub("<tok>", _IP.sub("<ip>", text or ""))


BASIC_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONUTF8", "PORTAL_PORT", "LAN_PEER_HTTP_TIMEOUT")


def child_env(environ: dict) -> dict:
    """Return the environment for the drop process: the peer-TLS and token allowlist plus basic process settings only."""
    return {k: v for k, v in environ.items() if v and (k in ALLOWED_ENV or k in BASIC_ENV)}


def verdict(payload: dict, expected_bytes: int) -> dict:
    """Return the delivery verdict from the drop's own JSON; delivered only with ok, received_at and equal bytes."""
    ok = payload.get("ok") is True
    received = payload.get("received_at")
    size_match = payload.get("bytes") == expected_bytes
    return {
        "delivered": bool(ok and received and size_match), "ok": ok, "received_at": received,
        "bytes": payload.get("bytes"), "expected_bytes": expected_bytes, "size_match": size_match,
        "queued_record": bool(payload.get("queued")),
    }


def main(argv: list[str] | None = None) -> int:
    """Send one file and print a masked JSON verdict."""
    ap = argparse.ArgumentParser(description="Send one file to the LAN peer and report delivery evidence.")
    ap.add_argument("--file", required=True)
    ap.add_argument("--assignee", default="win")
    ap.add_argument("--topic", default="")
    ap.add_argument("--peer-ip", default="")
    ap.add_argument("--portal-port", type=int, default=0, help="default: lan_peer_assign picks the TLS port when configured")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args(argv)
    src = Path(args.file)
    if not src.is_file():
        print(json.dumps({"delivered": False, "error": "file not found"}))
        return 2
    env = child_env(dict(os.environ))
    cmd = [sys.executable, str(_ASSIGN), "drop", "--peer", "--file", str(src), "--assignee", args.assignee, "--timeout", str(args.timeout)]
    if args.topic:
        cmd += ["--topic", args.topic]
    if args.peer_ip:
        cmd += ["--peer-ip", args.peer_ip]
    if args.portal_port:
        cmd += ["--portal-port", str(args.portal_port)]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False, timeout=args.timeout * 4 + 30)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        payload = {"ok": False, "detail": mask((proc.stdout + proc.stderr)[:300])}
    out = verdict(payload, src.stat().st_size)
    out["filename"] = payload.get("filename") or src.name
    if not out["delivered"]:
        out["detail"] = mask(str(payload.get("detail") or payload.get("last_error") or ""))[:300]
        out["next"] = ("a queued outbox record may exist; reconcile it explicitly with lan_peer_assign.py outbox-resolve "
                       "(do not flush the whole outbox)")
    print(json.dumps(out, indent=2))
    return 0 if out["delivered"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
