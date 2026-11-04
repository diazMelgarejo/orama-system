"""LAN peer file inbox — markdown/plain-text handoff (no streaming required)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _home_dir() -> Path:
    """Home directory for LAN peer state: ``HOME`` when set, else ``Path.home()``."""
    # Path.home() resolves via USERPROFILE on Windows and ignores HOME
    # entirely, which silently defeats test isolation: tests set
    # env["HOME"] = tmp_path expecting outbox/inbox state to land there,
    # but on Windows it landed in the real user profile instead — a test
    # run could leak fixture files into (or even attempt real delivery
    # from) actual production LAN peer coordination state. Honor HOME
    # explicitly first; Path.home() remains the fallback for normal use
    # where HOME is typically unset on Windows.
    override = os.environ.get("HOME")
    if override:
        return Path(override)
    return Path.home()


def lan_peer_state_dir() -> Path:
    """Root of the LAN peer state tree (inbox, outbox and metadata)."""
    return _home_dir() / ".openclaw" / "state" / "lan_peer"


def inbox_dir() -> Path:
    """Directory holding files received from peers."""
    return lan_peer_state_dir() / "inbox"


def outbox_dir() -> Path:
    """Directory holding files queued for a peer that were not yet delivered."""
    return lan_peer_state_dir() / "outbox"


def sanitize_filename(name: str) -> str:
    """Return ``name`` stripped when it is a safe assignment filename, else raise ValueError."""
    raw = name.strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    candidate = raw
    if not _SAFE_NAME.match(candidate):
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    if candidate.endswith(".json"):
        raise ValueError("use .md or .txt for assignment bodies; .json is metadata only")
    return candidate


def _resolve_within(root: Path, name: str) -> Path:
    """Resolve `name` under `root`, verifying containment by normalized-path prefix.

    Two prior fixes here used pathlib's Path.resolve() + is_relative_to() --
    both got re-flagged by CodeQL alerts #59 and #63 (py/path-injection),
    proving that shape isn't reliably recognized as a sanitizer. CodeQL's own
    rule documentation (code-scanning alert #63 "GOOD" example) shows the
    specific idiom its query is built to recognize: os.path.normpath(
    os.path.join(base, name)) followed by str.startswith(base). This function
    now matches that idiom exactly, on top of the character-allowlist check
    (which already made traversal impossible on its own -- this is the
    static-analysis-recognized shape, not a functional change to what's
    rejected).
    """
    raw = name.strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    if not _SAFE_NAME.match(raw):
        raise ValueError(f"unsafe or invalid filename: {name!r}")
    if raw.endswith(".json"):
        raise ValueError("use .md or .txt for assignment bodies; .json is metadata only")
    base = os.path.normpath(str(root))
    full_path = os.path.normpath(os.path.join(base, raw))
    # A single startswith guard, exactly CodeQL's recognized idiom: an
    # ``or full_path == base`` alternative hid the guard from py/path-injection,
    # and a name that resolves to the root itself is not a file anyway.
    if not full_path.startswith(base + os.sep):
        raise ValueError(f"unsafe path escapes root: {name!r}")
    return Path(full_path)


def _meta_path(path: Path) -> Path:
    """Sidecar metadata path (``<name>.meta.json``) for an assignment file."""
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
    """Persist the exact UTF-8 body bytes and their sidecar metadata."""
    dest = _resolve_within(inbox_dir(), filename)
    safe = dest.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = body.encode("utf-8")
    dest.write_bytes(payload)
    record = {
        "filename": safe,
        "assignee": assignee.strip(),
        "topic": topic.strip(),
        "source": source.strip(),
        "fanout_id": fanout_id.strip(),
        "received_at": int(time.time()),
    }
    if extra:
        record.update(extra)
    record["bytes"] = len(payload)
    record["sha256"] = hashlib.sha256(payload).hexdigest()
    _meta_path(dest).write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return record


def write_outbox_file(
    filename: str,
    body: str,
    *,
    assignee: str = "",
    topic: str = "",
    source: str = "",
    fanout_id: str = "",
    peer_ip: str = "",
    portal_port: int | str = "",
    error: str = "",
) -> dict[str, Any]:
    """Queue exact UTF-8 body bytes without platform newline translation."""
    dest = _resolve_within(outbox_dir(), filename)
    safe = dest.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = body.encode("utf-8")
    dest.write_bytes(payload)
    record = {
        "filename": safe,
        "assignee": assignee.strip(),
        "topic": topic.strip(),
        "source": source.strip(),
        "fanout_id": fanout_id.strip(),
        "peer_ip": str(peer_ip).strip(),
        "portal_port": str(portal_port).strip(),
        "last_error": error.strip(),
        "queued_at": int(time.time()),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    _meta_path(dest).write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return record


def _list_files(root: Path) -> list[dict[str, Any]]:
    """List assignment files under ``root`` with their metadata, skipping JSON sidecars and non-files."""
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*")):
        if not path.is_file() or path.suffix == ".json" or path.name.endswith(".meta.json"):
            continue
        meta_path = _meta_path(path)
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        entry = {
            "filename": path.name,
            "bytes": path.stat().st_size,
            "assignee": meta.get("assignee", ""),
            "topic": meta.get("topic", ""),
            "source": meta.get("source", ""),
            "fanout_id": meta.get("fanout_id", ""),
            "received_at": meta.get("received_at", int(path.stat().st_mtime)),
        }
        if "peer_ip" in meta:
            entry["peer_ip"] = meta.get("peer_ip", "")
            entry["portal_port"] = meta.get("portal_port", "")
        items.append(entry)
    return items


def list_inbox() -> list[dict[str, Any]]:
    """List received assignment files with their metadata."""
    return _list_files(inbox_dir())


def list_outbox() -> list[dict[str, Any]]:
    """List queued (undelivered) assignment files with their metadata."""
    return _list_files(outbox_dir())


def _read_file(root: Path, filename: str) -> tuple[str, dict[str, Any]]:
    """Read UTF-8 without newline translation; raise FileNotFoundError when absent."""
    path = _resolve_within(root, filename)
    safe = path.name
    if not path.is_file():
        raise FileNotFoundError(safe)
    body = path.read_bytes().decode("utf-8")
    meta: dict[str, Any] = {}
    meta_path = _meta_path(path)
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    return body, meta


def read_inbox_file(filename: str) -> tuple[str, dict[str, Any]]:
    """Return the body and metadata of a received assignment file."""
    return _read_file(inbox_dir(), filename)


def read_outbox_file(filename: str) -> tuple[str, dict[str, Any]]:
    """Return the body and metadata of a queued assignment file."""
    return _read_file(outbox_dir(), filename)


def remove_outbox_file(filename: str) -> None:
    """Delete a queued assignment file and its metadata sidecar, if present."""
    path = _resolve_within(outbox_dir(), filename)
    meta_path = _meta_path(path)
    if path.is_file():
        path.unlink()
    if meta_path.is_file():
        meta_path.unlink()
