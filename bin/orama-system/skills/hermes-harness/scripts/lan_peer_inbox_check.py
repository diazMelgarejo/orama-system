#!/usr/bin/env python3
"""Report whether a drop from the Mac peer has arrived in the local LAN peer inbox.

The launcher runs this after every ``--lan-peer`` start. It is read-only apart from a small
"already seen" state file, never touches the network and never prints file bodies.

A drop counts as coming from the Mac when its sidecar ``source`` carries a standalone ``mac`` token
(the file name is used only when there is no source, so a Windows-sent file named mac-* is not counted). Each drop is integrity-checked: the stored bytes must hash to the
``sha256`` recorded in the sidecar. Statuses:

* ``new``            at least one Mac drop not seen by an earlier check;
* ``baseline``       first ever check: existing Mac drops are recorded, none reported as new;
* ``quiet``          Mac drops exist but none are new;
* ``none``           no Mac drop has ever arrived;
* ``integrity-fail`` a Mac drop does not match its recorded hash (exit code 2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
STATE_NAME = "inbox_check.json"


def is_mac_drop(name: str, meta: dict[str, Any]) -> bool:
    """Return True for a Mac drop: the sidecar source decides; the file name is used only when it has no source."""
    source = str(meta.get("source") or "").strip()
    return bool(_MAC_TOKEN.search(source) if source else _MAC_TOKEN.search(name))


def _read_meta(path: Path) -> dict[str, Any]:
    """Load the ``<name>.meta.json`` sidecar next to *path*, or an empty dict when absent or bad."""
    sidecar = path.with_suffix(path.suffix + ".meta.json")
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def collect(inbox: Path, now: float) -> list[dict[str, Any]]:
    """Return Mac drops in *inbox*, newest first, each with age and integrity (ok/mismatch/unknown)."""
    drops: list[dict[str, Any]] = []
    if not inbox.is_dir():
        return drops
    for path in inbox.iterdir():
        if not path.is_file() or path.name.endswith(".meta.json") or path.suffix == ".json":
            continue
        meta = _read_meta(path)
        if not is_mac_drop(path.name, meta):
            continue
        body = path.read_bytes()
        recorded = str(meta.get("sha256") or "")
        if not recorded:
            integrity = "unknown"
        else:
            integrity = "ok" if hashlib.sha256(body).hexdigest() == recorded else "mismatch"
        received = int(meta.get("received_at") or path.stat().st_mtime)
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
    args = parser.parse_args(argv)

    drops = collect(inbox_dir(), time.time())
    state = lan_peer_state_dir() / STATE_NAME
    status, new = evaluate(drops, _load_seen(state))
    result = {
        "status": status,
        "mac_drops": len(drops),
        "new": [d["name"] for d in new],
        "newest": drops[0] if drops else None,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    elif status == "none":
        print("no drop from the Mac has arrived yet")
    elif status == "integrity-fail":
        bad = [d["name"] for d in drops if d["integrity"] == "mismatch"]
        print(f"integrity FAIL for {len(bad)} Mac drop(s): {', '.join(bad)}")
    else:
        newest = drops[0]
        label = {"new": f"{len(new)} new", "baseline": "first check", "quiet": "none new"}[status]
        print(
            f"Mac drops: {len(drops)} total, {label}; newest {newest['name']} "
            f"({newest['bytes']} bytes, {_human_age(newest['age_seconds'])} ago, integrity {newest['integrity']})"
        )
    if not args.no_record and status != "integrity-fail":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"seen": {d["name"]: d["sha256"] for d in drops}}) + "\n", encoding="utf-8")
    return 2 if status == "integrity-fail" else 0


if __name__ == "__main__":
    sys.exit(main())
