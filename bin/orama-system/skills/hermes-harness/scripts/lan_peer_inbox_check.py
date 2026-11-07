#!/usr/bin/env python3
"""Report whether a drop from the LAN peer has arrived in the local LAN peer inbox.

The launcher runs this after every ``--lan-peer`` start: the Windows launcher asks about Mac drops (the
default, ``--peer mac``) and the Mac launcher asks about Windows drops (``--peer win``). It is read-only
apart from a small per-peer "already seen" state file, never touches the network and never prints file
bodies.

A drop counts as coming from the peer when its sidecar ``source`` carries a standalone token for that peer
(``mac`` or ``win``); the file name is used only when there is no source. Each drop is integrity-checked:
the stored bytes must hash to the ``sha256`` recorded in the sidecar. Statuses:

* ``new``            at least one peer drop not seen by an earlier check;
* ``baseline``       first ever check: existing peer drops are recorded, none reported as new;
* ``quiet``          peer drops exist but none are new;
* ``none``           no drop from the peer has ever arrived;
* ``integrity-fail`` a peer drop does not match its recorded hash (exit code 2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

_SRC_ROOT = Path(__file__).resolve().parents[5] / "src"
if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from orama_system.lan_peer_files import inbox_dir, lan_peer_state_dir  # noqa: E402

_MAC_TOKEN = re.compile(r"(?<![a-z0-9])mac(?![a-z0-9])", re.IGNORECASE)
_PEER_TOKENS = {"mac": _MAC_TOKEN, "win": re.compile(r"(?<![a-z0-9])win(?![a-z0-9])", re.IGNORECASE)}
PEER_LABELS = {"mac": "Mac", "win": "Windows"}
STATE_NAME = "inbox_check.json"


def state_name(peer: str = "mac") -> str:
    """Return the already-seen state file name for *peer*; the Mac name is the original one, for compatibility."""
    return STATE_NAME if peer == "mac" else f"inbox_check_{peer}.json"


def is_peer_drop(name: str, meta: dict[str, Any], peer: str = "mac") -> bool:
    """Return True for a drop from *peer*: the sidecar source decides; the file name is used only when it has no source."""
    token = _PEER_TOKENS[peer]
    source = str(meta.get("source") or "").strip()
    return bool(token.search(source) if source else token.search(name))


def is_mac_drop(name: str, meta: dict[str, Any]) -> bool:
    """Return True for a Mac drop (the original entry point, kept for existing callers)."""
    return is_peer_drop(name, meta, "mac")


def _read_meta(path: Path) -> dict[str, Any]:
    """Load the ``<name>.meta.json`` sidecar next to *path*, or an empty dict when absent or bad."""
    sidecar = path.with_suffix(path.suffix + ".meta.json")
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def collect(inbox: Path, now: float, peer: str = "mac") -> list[dict[str, Any]]:
    """Return *peer* drops in *inbox*, newest first, each with age and integrity (ok/mismatch/unknown)."""
    drops: list[dict[str, Any]] = []
    if not inbox.is_dir():
        return drops
    for path in inbox.iterdir():
        if not path.is_file() or path.name.endswith(".meta.json") or path.suffix == ".json":
            continue
        meta = _read_meta(path)
        if not is_peer_drop(path.name, meta, peer):
            continue
        try:
            body = path.read_bytes()
            recorded = str(meta.get("sha256") or "")
            if not recorded:
                integrity = "unknown"
            else:
                integrity = "ok" if hashlib.sha256(body).hexdigest() == recorded else "mismatch"
            received = int(meta.get("received_at") or path.stat().st_mtime)
        except OSError:
            continue
        drops.append(
            {
                "name": path.name,
                "bytes": len(body),
                "received_at": received,
                "age_seconds": max(0, int(now - received)),
                "integrity": integrity,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return sorted(drops, key=lambda d: d["received_at"], reverse=True)


def _load_seen(state: Path) -> dict[str, str] | None:
    """Return the name->sha256 map of drops already reported, or None when no state exists yet."""
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    seen = data.get("seen") if isinstance(data, dict) else None
    return seen if isinstance(seen, dict) else None


def evaluate(drops: list[dict[str, Any]], seen: dict[str, str] | None) -> tuple[str, list[dict[str, Any]]]:
    """Return ``(status, new_drops)`` for the collected drops against the already-seen map."""
    if any(d["integrity"] == "mismatch" for d in drops):
        return "integrity-fail", []
    if not drops:
        return "none", []
    if seen is None:
        return "baseline", []
    new = [d for d in drops if seen.get(d["name"]) != d["sha256"]]
    return ("new" if new else "quiet"), new


def _human_age(seconds: int) -> str:
    """Format an age in seconds as minutes, hours or days."""
    if seconds < 3600:
        return f"{seconds // 60} min"
    if seconds < 172800:
        return f"{seconds // 3600} h"
    return f"{seconds // 86400} d"


def main(argv: list[str] | None = None) -> int:
    """Run the check, record what was seen unless --no-record, print the result and return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--no-record", action="store_true", help="do not update the already-seen state")
    parser.add_argument(
        "--peer", choices=sorted(_PEER_TOKENS), default="mac",
        help="which peer's drops to report (default mac: the Windows launcher; win: the Mac launcher)",
    )
    args = parser.parse_args(argv)
    peer, who = args.peer, PEER_LABELS[args.peer]

    drops = collect(inbox_dir(), time.time(), peer)
    state = lan_peer_state_dir() / state_name(peer)
    status, new = evaluate(drops, _load_seen(state))
    result = {
        "status": status,
        f"{peer}_drops": len(drops),
        "new": [d["name"] for d in new],
        "newest": drops[0] if drops else None,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    elif status == "none":
        print(f"no drop from the {who} peer has arrived yet")
    elif status == "integrity-fail":
        bad = [d["name"] for d in drops if d["integrity"] == "mismatch"]
        print(f"integrity FAIL for {len(bad)} {who} drop(s): {', '.join(bad)}")
    else:
        newest = drops[0]
        label = {"new": f"{len(new)} new", "baseline": "first check", "quiet": "none new"}[status]
        print(
            f"{who} drops: {len(drops)} total, {label}; newest {newest['name']} "
            f"({newest['bytes']} bytes, {_human_age(newest['age_seconds'])} ago, integrity {newest['integrity']})"
        )
    if not args.no_record and status != "integrity-fail":
        state.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps({"seen": {d["name"]: d["sha256"] for d in drops}}) + "\n"
        tmp_state = state.with_name(f".{state.name}.tmp.{os.getpid()}")
        try:
            tmp_state.write_text(content, encoding="utf-8")
            os.replace(tmp_state, state)
        except OSError:
            if tmp_state.exists():
                try:
                    tmp_state.unlink()
                except OSError:
                    pass
            raise
    return 2 if status == "integrity-fail" else 0


if __name__ == "__main__":
    sys.exit(main())
