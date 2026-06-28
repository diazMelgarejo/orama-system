#!/usr/bin/env python3
"""lan_peer_assign.py — file-based LAN peer work assignments (markdown / plain text).

Drop topic files to the peer portal inbox instead of streaming large payloads over WS.

Usage:
    # Drop assignment to peer (reads discovery JSON for peer IP)
    python lan_peer_assign.py --peer drop --file ./mac-hypothesis.md --assignee mac --topic autoresearch/hypothesis

    # List peer inbox
    python lan_peer_assign.py --peer list

    # Read one file from peer inbox
    python lan_peer_assign.py --peer read --name 2026-06-28-mac-hypothesis.md

    # Fan out manifest to peers (local paths → HTTP drop per assignee)
    python lan_peer_assign.py fanout --manifest assignments.json

Manifest JSON::
    {
      "fanout_id": "2026-06-28-autoresearch-001",
      "assignments": [
        {"assignee": "mac", "topic": "hypothesis", "filename": "mac-hypothesis.md", "path": "./tasks/mac.md"},
        {"assignee": "win", "topic": "gpu-run", "filename": "win-gpu.md", "path": "./tasks/win.md"}
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Reuse probe helpers (same directory)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import probe_lan_peer as probe  # noqa: E402

# scripts → hermes-harness → skills → bin/orama-system → bin → repo root
_REPO_ROOT = _SCRIPT_DIR.parents[4]
_SRC_ROOT = _REPO_ROOT / "src"


def _ensure_orama_src() -> None:
    if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))


def _auth_header() -> dict[str, str]:
    token = probe.resolve_control_plane_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _peer_base(peer_ip: str, portal_port: int) -> str:
    return f"http://{peer_ip}:{portal_port}"


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = None
    headers = _auth_header()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {url}: {body[:300]}") from exc
    except Exception as exc:
        raise SystemExit(f"request failed {url}: {exc}") from exc


def _resolve_peer(args: argparse.Namespace) -> tuple[str, int]:
    if args.peer_ip:
        ip = args.peer_ip.strip()
    else:
        discovery = probe.load_discovery()
        ip, _ = probe.peer_from_discovery(discovery, probe.local_role())
    port = int(args.portal_port)
    if not ip:
        raise SystemExit("no peer IP — set --peer-ip or refresh last_discovery.json")
    return ip, port


def cmd_drop(args: argparse.Namespace) -> int:
    body = Path(args.file).read_text(encoding="utf-8")
    filename = args.filename or Path(args.file).name
    payload = {
        "filename": filename,
        "body": body,
        "assignee": args.assignee,
        "topic": args.topic,
        "fanout_id": args.fanout_id or "",
        "source": probe.local_role(),
    }
    if args.peer:
        ip, port = _resolve_peer(args)
        url = f"{_peer_base(ip, port)}/api/peer-file"
        result = _http_json("POST", url, payload)
        print(json.dumps(result, indent=2))
        return 0
    # Local inbox (self-test)
    _ensure_orama_src()
    from orama_system.lan_peer_files import write_inbox_file

    record = write_inbox_file(
        filename,
        body,
        assignee=args.assignee,
        topic=args.topic,
        source=probe.local_role(),
        fanout_id=args.fanout_id or "",
    )
    print(json.dumps({"ok": True, "local": True, **record}, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if args.peer:
        ip, port = _resolve_peer(args)
        url = f"{_peer_base(ip, port)}/api/peer-inbox"
        result = _http_json("GET", url)
        print(json.dumps(result, indent=2))
        return 0
    _ensure_orama_src()
    from orama_system.lan_peer_files import list_inbox

    print(json.dumps({"files": list_inbox()}, indent=2))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    if not args.name:
        raise SystemExit("--name required for read")
    if args.peer:
        ip, port = _resolve_peer(args)
        url = f"{_peer_base(ip, port)}/api/peer-inbox/{args.name}"
        result = _http_json("GET", url)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result.get("body", ""))
        return 0
    _ensure_orama_src()
    from orama_system.lan_peer_files import read_inbox_file

    body, meta = read_inbox_file(args.name)
    if args.json:
        print(json.dumps({"body": body, "meta": meta}, indent=2))
    else:
        print(body)
    return 0


def cmd_fanout(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    fanout_id = str(manifest.get("fanout_id") or "").strip()
    assignments = manifest.get("assignments") or []
    if not assignments:
        raise SystemExit("manifest has no assignments")
    role = probe.local_role()
    results: list[dict[str, Any]] = []
    for item in assignments:
        assignee = str(item.get("assignee") or "").strip()
        topic = str(item.get("topic") or "").strip()
        filename = str(item.get("filename") or Path(item.get("path", "task.md")).name)
        path = Path(str(item.get("path") or ""))
        if not path.is_file():
            raise SystemExit(f"missing assignment file: {path}")
        # Drop to peer when assignee is the other host; keep locally when assignee is us
        to_peer = assignee and assignee != role
        ns = argparse.Namespace(
            file=str(path),
            filename=filename,
            assignee=assignee,
            topic=topic,
            fanout_id=fanout_id,
            peer=to_peer,
            peer_ip=args.peer_ip,
            portal_port=args.portal_port,
        )
        print(f"--- drop {filename} assignee={assignee} peer={to_peer}", file=sys.stderr)
        entry: dict[str, Any] = {"filename": filename, "assignee": assignee, "to_peer": to_peer}
        try:
            cmd_drop(ns)
            entry["status"] = "ok"
        except SystemExit as exc:
            entry["status"] = "error"
            entry["detail"] = str(exc)
            print(f"WARN: {exc}", file=sys.stderr)
        results.append(entry)
    failed = [r for r in results if r.get("status") == "error"]
    out = {"fanout_id": fanout_id, "results": results, "status": "partial" if failed else "ok"}
    print(json.dumps(out, indent=2))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    peer_p = argparse.ArgumentParser(add_help=False)
    peer_p.add_argument(
        "--peer", action="store_true", help="Target peer portal (default: local inbox)"
    )
    peer_p.add_argument("--peer-ip", help="Override peer IP")
    peer_p.add_argument(
        "--portal-port", type=int, default=int(os.environ.get("PORTAL_PORT", "8002"))
    )

    p = argparse.ArgumentParser(description="LAN peer file assignments (markdown handoff)")
    sub = p.add_subparsers(dest="cmd", required=True)

    drop = sub.add_parser("drop", parents=[peer_p], help="Drop a markdown/text file to peer inbox")
    drop.add_argument("--file", required=True, help="Local file to send")
    drop.add_argument("--filename", help="Remote filename (default: basename of --file)")
    drop.add_argument("--assignee", default="", help="mac | win")
    drop.add_argument("--topic", default="", help="e.g. autoresearch/hypothesis")
    drop.add_argument("--fanout-id", default="", help="Fan-out batch id")
    drop.set_defaults(func=cmd_drop)

    lst = sub.add_parser("list", parents=[peer_p], help="List inbox files")
    lst.set_defaults(func=cmd_list)

    read = sub.add_parser("read", parents=[peer_p], help="Read one inbox file")
    read.add_argument("--name", required=True)
    read.add_argument("--json", action="store_true")
    read.set_defaults(func=cmd_read)

    fan = sub.add_parser("fanout", parents=[peer_p], help="Drop many assignments from manifest JSON")
    fan.add_argument("--manifest", required=True)
    fan.set_defaults(func=cmd_fanout)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
