#!/usr/bin/env python3
"""lan_peer_assign.py — file-based LAN peer work assignments (markdown / plain text).

Drop topic files to the peer portal inbox instead of streaming large payloads over WS.

Usage:
    # Drop assignment to peer (reads discovery JSON for peer IP)
    python lan_peer_assign.py drop --peer --file ./mac-hypothesis.md --assignee mac --topic autoresearch/hypothesis

    # List peer inbox
    python lan_peer_assign.py list --peer

    # Read one file from peer inbox
    python lan_peer_assign.py read --peer --name 2026-06-28-mac-hypothesis.md

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
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Reuse probe helpers (same directory)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import peer_tls  # noqa: E402
import probe_lan_peer as probe  # noqa: E402

# scripts → hermes-harness → skills → bin/orama-system → bin → repo root
_REPO_ROOT = _SCRIPT_DIR.parents[4]
_SRC_ROOT = _REPO_ROOT / "src"

logger = logging.getLogger("lan_peer_assign")


def _ensure_orama_src() -> None:
    if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))


def _auth_header(token: str) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _is_authenticated_transport(url: str) -> bool:
    """True only for transports that cryptographically protect bearer tokens.

    SECURITY INVARIANT (RFC 6750 §5.3): Bearer tokens MUST only be sent
    over TLS (https://).  http:// with a real token is a credential-leak
    vector — fail-closed.
    """
    return url.startswith("https://")


def _peer_portal_tls_enabled() -> bool:
    """Env gate for peer-portal HTTPS, matching the parsing convention
    already established by orchestrator/dangerous_workers.py
    (PT_ALLOW_DANGEROUS_CLI_WORKERS) and alphaclaw_manager.py
    (ALPHACLAW_TLS_ENABLED). Off by default.

    Without this, _is_authenticated_transport()'s fail-closed check
    means every peer-file call (drop/list/read/flush) silently and
    permanently fails whenever a real control-plane token is configured
    -- there is currently no TLS listener on the peer portal side for
    this to ever succeed against otherwise. This flag exists so an
    operator who HAS deployed TLS in front of their own peer portal
    (out of band, no such mechanism ships in this repo yet -- same
    "minimum required today" scope as ALPHACLAW_TLS_ENABLED) has an
    explicit way to use it, rather than the security invariant being an
    unconditional, unescapable dead end.
    """
    v = (os.environ.get("PEER_PORTAL_TLS_ENABLED") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _peer_base(peer_ip: str, portal_port: int) -> str:
    scheme = "https" if _peer_portal_tls_enabled() else "http"
    return f"{scheme}://{peer_ip}:{portal_port}"


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    return _http_json_ex(method, url, payload, timeout)[0]


def _http_json_ex(
    method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 30
) -> tuple[Any, bool]:
    """Request, retrying across every local control-plane token candidate
    on 401/403 before giving up -- see query_peer_topology.py's _http_get
    for why (2026-07-19 D9 self-correction: resolve_control_plane_token()'s
    single "preferred" token is not always the one the peer accepts, even
    when a working local candidate exists).

    SECURITY: bearer tokens are NEVER attached to unauthenticated http://
    URLs.  _is_authenticated_transport() is checked before any
    Authorization header is constructed — matching the sibling topology
    helper (query_peer_topology._http_get).  For http:// peer URLs the
    request proceeds unauthenticated (no credential to leak); for https://
    the normal candidate-retry loop runs.  RFC 6750 §5.3.
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    candidates = probe.outbound_control_plane_tokens() or [""]
    has_real_token = any(candidates)

    # FAIL-CLOSED: never send bearer tokens over unauthenticated transport
    if has_real_token and not _is_authenticated_transport(url):
        logger.error(
            "SECURITY_STOP: refusing to send %d token candidate(s) to %s "
            "over unauthenticated transport (http://). "
            "Peer portal must use https:// for authenticated endpoints.",
            len(candidates), url,
        )
        # Proceed unauthenticated — the peer may still accept the request
        # without a token (e.g. for health checks or public endpoints).
        # We intentionally do NOT raise here; we simply omit the token.
        candidates = [""]  # unauthenticated path

    # Per-stack trust (PEER_CA_FILE / PEER_PINNED_FINGERPRINTS), resolved
    # BEFORE any Authorization header exists: a peer that fails verification
    # gets no token at all (hard fail, no unverified fallback).
    try:
        tls_kw = peer_tls.urlopen_kwargs(url, timeout)
    except peer_tls.PeerTrustError as exc:
        raise SystemExit(f"peer TLS verification failed {url}: {exc} (token not sent)") from exc

    last_error: tuple[int, str] | None = None
    for token in candidates:
        headers = _auth_header(token) if token else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, **tls_kw) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                # authenticated == a real token travelled over verified https
                return (json.loads(raw) if raw.strip() else {}), bool(token)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = str(exc.reason)
            if exc.code in (401, 403) and token:
                last_error = (exc.code, body[:300])
                continue  # try the next candidate token
            raise SystemExit(f"HTTP {exc.code} {url}: {body[:300]}") from exc
        except Exception as exc:
            raise SystemExit(f"request failed {url}: {exc}") from exc
    code, body = last_error or (401, "no candidates")
    raise SystemExit(
        f"HTTP {code} {url}: {body} (tried {len(candidates)} local token candidate(s))"
    )


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
        try:
            result = _http_json("POST", url, payload, timeout=args.timeout)
        except SystemExit as exc:
            _ensure_orama_src()
            from orama_system.lan_peer_files import write_outbox_file

            record = write_outbox_file(
                filename,
                body,
                assignee=args.assignee,
                topic=args.topic,
                source=probe.local_role(),
                fanout_id=args.fanout_id or "",
                peer_ip=ip,
                portal_port=port,
                error=str(exc),
            )
            _set_state(record["filename"], "queued", last_error=str(exc)[:500])
            record["state"] = "queued"
            print(
                json.dumps(
                    {
                        "ok": False,
                        "queued": True,
                        "scope": "local-outbox",
                        "detail": str(exc),
                        **record,
                    },
                    indent=2,
                )
            )
            return 2
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
        result = _http_json("GET", url, timeout=args.timeout)
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
        result = _http_json("GET", url, timeout=args.timeout)
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


_STATES = ("queued", "sent", "delivered")


def _meta_file(filename: str) -> Path:
    _ensure_orama_src()
    from orama_system.lan_peer_files import _meta_path, _resolve_within, outbox_dir

    return _meta_path(_resolve_within(outbox_dir(), filename))


def _item_state(meta: dict[str, Any]) -> str:
    """Old .meta.json files carry no state: they are queued."""
    st = str(meta.get("state") or "queued").strip().lower()
    return st if st in _STATES else "queued"


def _set_state(filename: str, state: str, **fields: Any) -> None:
    path = _meta_file(filename)
    meta: dict[str, Any] = {}
    if path.is_file():
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["state"] = state
    meta["state_at"] = int(time.time())
    meta.update(fields)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _select_items(items: list[dict[str, Any]], only: list[str]) -> list[dict[str, Any]]:
    wanted = {Path(o).name for o in only}
    out = []
    for item in items:
        name = str(item.get("filename") or "")
        if not name:
            continue
        if wanted and name not in wanted and Path(name).stem not in wanted:
            continue
        out.append(item)
    return out


def cmd_outbox_status(args: argparse.Namespace) -> int:
    """Read-only listing of outbox entries and their delivery state."""
    _ensure_orama_src()
    from orama_system.lan_peer_files import list_outbox, read_outbox_file

    rows = []
    for item in list_outbox():
        name = str(item.get("filename") or "")
        if not name:
            continue
        _, meta = read_outbox_file(name)
        rows.append(
            {
                "filename": name,
                "state": _item_state(meta),
                "peer_ip": str(meta.get("peer_ip") or ""),
                "portal_port": str(meta.get("portal_port") or ""),
                "queued_at": meta.get("queued_at", ""),
                "state_at": meta.get("state_at", ""),
                "last_error": str(meta.get("last_error") or "")[:300],
            }
        )
    counts = {s: sum(1 for r in rows if r["state"] == s) for s in _STATES}
    print(json.dumps({"items": rows, "counts": counts}, indent=2))
    return 0


def cmd_flush_outbox(args: argparse.Namespace) -> int:
    _ensure_orama_src()
    from orama_system.lan_peer_files import list_outbox, read_outbox_file, remove_outbox_file

    # Each outbox item was queued with its own intended peer_ip/portal_port
    # (see write_outbox_file) -- that stored target ALWAYS wins per item.
    # --peer-ip/--portal-port on this command are only a fallback default
    # for legacy items queued before peer_ip was recorded, never an
    # override -- a batch commonly spans multiple peers.
    #
    # Delivery states (recorded in each entry's .meta.json):
    #   queued    -> not yet accepted by the peer (default; absent == queued)
    #   sent      -> peer answered 2xx but did NOT confirm ok:true over an
    #                authenticated channel (kept; retried by default)
    #   delivered -> authenticated HTTPS success AND body ok:true
    # Failures, timeouts and SECURITY_STOP leave the entry queued with
    # last_error. Selection: --only (repeatable) and/or --state. Default
    # (neither) retries every non-delivered entry, as before.
    only = list(getattr(args, "only", None) or [])
    state_filter = list(getattr(args, "state", None) or [])
    strict = bool(getattr(args, "strict", False))
    keep = bool(getattr(args, "keep_delivered", False))
    default_peer: tuple[str, int] | None = None
    results: list[dict[str, Any]] = []
    for item in _select_items(list_outbox(), only):
        filename = str(item.get("filename") or "")
        body, meta = read_outbox_file(filename)
        prior = _item_state(meta)
        if state_filter:
            if prior not in state_filter:
                continue
        elif prior == "delivered":
            continue
        stored_ip = str(meta.get("peer_ip") or "").strip()
        if stored_ip:
            item_port_raw = str(meta.get("portal_port") or "").strip()
            item_ip, item_port = stored_ip, (int(item_port_raw) if item_port_raw else int(args.portal_port))
        else:
            if default_peer is None:
                default_peer = _resolve_peer(args)
            item_ip, item_port = default_peer
        url = f"{_peer_base(item_ip, item_port)}/api/peer-file"
        payload = {
            "filename": filename,
            "body": body,
            "assignee": str(meta.get("assignee") or item.get("assignee") or ""),
            "topic": str(meta.get("topic") or item.get("topic") or ""),
            "fanout_id": str(meta.get("fanout_id") or item.get("fanout_id") or ""),
            "source": str(meta.get("source") or probe.local_role()),
        }
        entry: dict[str, Any] = {
            "filename": filename,
            "status": "pending",
            "peer_ip": item_ip,
            "portal_port": item_port,
        }
        try:
            result, authed = _http_json_ex("POST", url, payload, timeout=args.timeout)
        except SystemExit as exc:
            entry["status"] = "error"
            entry["state"] = "queued"
            entry["detail"] = str(exc)
            _set_state(filename, "queued", last_error=str(exc)[:500])
        else:
            confirmed = isinstance(result, dict) and result.get("ok") is True
            if confirmed and authed:
                entry["status"] = "delivered"
                entry["state"] = "delivered"
                if keep:
                    _set_state(filename, "delivered", last_error="", delivered_at=int(time.time()))
                else:
                    remove_outbox_file(filename)
            else:
                why = (
                    "peer response lacked ok:true"
                    if not confirmed
                    else "success was not on an authenticated (token over https) channel"
                )
                entry["status"] = "sent"
                entry["state"] = "sent"
                entry["detail"] = why
                _set_state(filename, "sent", last_error=why)
        results.append(entry)
        detail = f" ({entry['detail'][:120]})" if entry.get("detail") else ""
        print(f"{entry['status']:9s} {filename} -> {item_ip}:{item_port}{detail}", file=sys.stderr)
    delivered = [r for r in results if r["status"] == "delivered"]
    remaining = [r for r in results if r["status"] != "delivered"]
    summary = f"delivered {len(delivered)}, still queued {len(remaining)}"
    print(summary, file=sys.stderr)
    print(
        json.dumps(
            {
                "ok": not remaining,
                "summary": summary,
                "delivered": len(delivered),
                "still_queued": len(remaining),
                "results": results,
            },
            indent=2,
        )
    )
    if strict:
        return 1 if remaining else 0
    return 1 if any(r["status"] == "error" for r in results) else 0


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
            timeout=args.timeout,
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
    peer_p.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("LAN_PEER_HTTP_TIMEOUT", "30")),
        help="HTTP timeout in seconds for peer portal calls",
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

    flush = sub.add_parser(
        "flush-outbox",
        parents=[peer_p],
        help="Retry locally queued peer drops",
    )
    flush.add_argument("--only", action="append", default=[], metavar="FILE_OR_ID",
                       help="Only flush this outbox filename (or stem); repeatable")
    flush.add_argument("--state", action="append", default=[], choices=list(_STATES),
                       help="Only flush entries in this state; repeatable")
    flush.add_argument("--strict", action="store_true",
                       help="Exit non-zero when anything remains queued/sent")
    flush.add_argument("--keep-delivered", action="store_true",
                       help="Keep delivered entries (state=delivered) instead of removing them")
    flush.set_defaults(func=cmd_flush_outbox)

    stat = sub.add_parser("outbox-status", help="List outbox entries and delivery states (read-only)")
    stat.set_defaults(func=cmd_outbox_status)

    fan = sub.add_parser("fanout", parents=[peer_p], help="Drop many assignments from manifest JSON")
    fan.add_argument("--manifest", required=True)
    fan.set_defaults(func=cmd_fanout)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
