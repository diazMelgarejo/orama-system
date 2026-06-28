"""LAN peer file inbox — markdown/plain-text handoff (no streaming required)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def lan_peer_state_dir() -> Path:
    return Path.home() / ".openclaw" / "state" / "lan_peer"


def inbox_dir() -> Path:
    return lan_peer_state_dir() / "inbox"


def outbox_dir() -> Path:
    return lan_peer_state_dir() / "outbox"


def sanitize_filename(name: str) -> str:
    raw = name.strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    candidate = raw
    if not _SAFE_NAME.match(candidate):
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    if candidate.endswith(".json"):
        raise ValueError("use .md or .txt for assignment bodies; .json is metadata only")
    return candidate


def _meta_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".meta.json")


def write_inbox_file(
    filename: str,
    body: str,
    *,
    assignee: str = "",
    topic: str = "",
    source: str = "",
    fanout_id: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a peer assignment file + sidecar metadata."""
    safe = sanitize_filename(filename)
    dest = inbox_dir() / safe
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    record = {
        "filename": safe,
        "assignee": assignee.strip(),
        "topic": topic.strip(),
        "source": source.strip(),
        "fanout_id": fanout_id.strip(),
        "received_at": int(time.time()),
        "bytes": len(body.encode("utf-8")),
    }
    if extra:
        record.update(extra)
    _meta_path(dest).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def list_inbox() -> list[dict[str, Any]]:
    root = inbox_dir()
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*")):
        if path.suffix == ".json" or path.name.endswith(".meta.json"):
            continue
        meta_path = _meta_path(path)
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        items.append(
            {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "assignee": meta.get("assignee", ""),
                "topic": meta.get("topic", ""),
                "source": meta.get("source", ""),
                "fanout_id": meta.get("fanout_id", ""),
                "received_at": meta.get("received_at", int(path.stat().st_mtime)),
            }
        )
    return items


def read_inbox_file(filename: str) -> tuple[str, dict[str, Any]]:
    safe = sanitize_filename(filename)
    path = inbox_dir() / safe
    if not path.is_file():
        raise FileNotFoundError(safe)
    body = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    meta_path = _meta_path(path)
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    return body, meta
