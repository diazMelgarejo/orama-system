#!/usr/bin/env python3
"""Export/restore a portable Hermes brain archive.

This is an orama-system harness wrapper around Hermes' documented storage model.
It is intentionally conservative:
- no secrets unless --include-secrets is passed
- no sessions unless --include-sessions is passed
- restore is dry-run/non-overwrite by default
- archives include a manifest describing what was copied and why
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
from typing import Iterable

SCHEMA_VERSION = "hermes-portable-brain/v1"
SECRET_ROOTS = {".env", "auth.json", "auth"}
SESSION_ROOTS = {"state.db", "sessions"}
DEFAULT_INCLUDE = [
    "SOUL.md",
    "config.yaml",
    "memories",
    "skills",
    "profiles",
    "cron",
    "kanban",
    "scripts",
    "pets",
    "skins",
    "desktop-plugins",
    "tui-widgets",
]
OPTIONAL_SECRETS = [".env", "auth.json", "auth"]
OPTIONAL_SESSIONS = ["state.db", "sessions"]
ALWAYS_EXCLUDE_NAMES = {
    "hermes-agent",
    "cache",
    "logs",
    "audio_cache",
    "image_cache",
    "bootstrap-cache",
    "node_modules",
    "__pycache__",
    ".git",
}


@dataclass
class ArchiveEntry:
    path: str
    bytes: int
    sha256: str
    category: str


def default_hermes_home() -> Path:
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "hermes"
    return Path.home() / ".hermes"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def iter_files(root: Path, rels: Iterable[str]) -> Iterable[Path]:
    for rel in rels:
        p = root / rel
        if not p.exists():
            continue
        if p.is_file():
            yield p
            continue
        for child in p.rglob("*"):
            if any(part in ALWAYS_EXCLUDE_NAMES for part in child.relative_to(root).parts):
                continue
            if child.is_file():
                yield child


def classify(rel: str) -> str:
    first = rel.split("/", 1)[0]
    if first in SECRET_ROOTS:
        return "secret"
    if first in SESSION_ROOTS:
        return "session"
    if first in {"SOUL.md", "memories", "profiles"}:
        return "identity-memory"
    if first == "skills":
        return "skills"
    if first in {"cron", "kanban", "scripts"}:
        return "automation"
    return "config"


def safe_arcname(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    return PurePosixPath(*rel.parts).as_posix()


def build_manifest(root: Path, entries: list[ArchiveEntry], args: argparse.Namespace) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "created_at_unix": int(time.time()),
        "source_hermes_home": str(root),
        "include_secrets": bool(getattr(args, "include_secrets", False)),
        "include_sessions": bool(getattr(args, "include_sessions", False)),
        "entries": [asdict(e) for e in entries],
        "restore_notes": [
            "Restore into a fresh Hermes install with --dry-run first.",
            "Secrets (.env/auth*) are skipped on restore unless --include-secrets is passed.",
            "Existing files are not overwritten unless --overwrite is passed.",
        ],
    }


def cmd_export(args: argparse.Namespace) -> int:
    root = Path(args.hermes_home).expanduser().resolve()
    if not root.exists():
        print(f"missing HERMES_HOME: {root}", file=sys.stderr)
        return 2
    rels = list(DEFAULT_INCLUDE)
    if args.include_secrets:
        rels += OPTIONAL_SECRETS
    if args.include_sessions:
        rels += OPTIONAL_SESSIONS

    files = sorted(set(iter_files(root, rels)))
    entries: list[ArchiveEntry] = []
    for p in files:
        rel = safe_arcname(p, root)
        entries.append(ArchiveEntry(rel, p.stat().st_size, sha256_file(p), classify(rel)))

    if args.dry_run:
        print(json.dumps(build_manifest(root, entries, args), indent=2))
        return 0

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = build_manifest(root, entries, args)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for p, e in zip(files, entries):
            zf.write(p, e.path)
    tmp.replace(output)
    print(f"wrote {output} ({len(entries)} files, sessions={bool(args.include_sessions)})")
    return 0


def validate_member(name: str) -> PurePosixPath:
    pp = PurePosixPath(name)
    if pp.is_absolute() or ".." in pp.parts or not pp.parts:
        raise ValueError(f"unsafe archive member: {name}")
    return pp


def load_manifest(archive: Path) -> dict:
    with zipfile.ZipFile(archive, "r") as zf:
        if "manifest.json" not in zf.namelist():
            raise ValueError("missing manifest.json")
        return json.loads(zf.read("manifest.json").decode("utf-8"))


def cmd_inspect(args: argparse.Namespace) -> int:
    archive = Path(args.archive).expanduser().resolve()
    manifest = load_manifest(archive)
    entries = manifest.get("entries", [])
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.get("category", "unknown")] = counts.get(e.get("category", "unknown"), 0) + 1
    summary = {
        "archive": str(archive),
        "schema": manifest.get("schema"),
        "source_hermes_home": manifest.get("source_hermes_home"),
        "entry_count": len(entries),
        "counts": counts,
        "include_secrets": manifest.get("include_secrets"),
        "include_sessions": manifest.get("include_sessions"),
    }
    # manifest's entries are ArchiveEntry(path, bytes, sha256, category) --
    # metadata only, never file content -- so printing it (full or summary)
    # does not expose archive contents. include_secrets/include_sessions
    # here are the same inclusion-scope booleans as build_manifest() sets,
    # not secret values.
    print(json.dumps(summary if args.summary else manifest, indent=2))
    return 0


def backup_conflicts(target_root: Path, members: list[str]) -> Path | None:
    existing = [target_root / PurePosixPath(m) for m in members if (target_root / PurePosixPath(m)).exists()]
    if not existing:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = target_root / "backups" / f"pre-portable-brain-restore-{stamp}.zip"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(backup, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in existing:
            if p.is_file():
                zf.write(p, PurePosixPath(*p.relative_to(target_root).parts).as_posix())
    return backup


def cmd_restore(args: argparse.Namespace) -> int:
    archive = Path(args.archive).expanduser().resolve()
    target = Path(args.hermes_home).expanduser().resolve()
    manifest = load_manifest(archive)
    if manifest.get("schema") != SCHEMA_VERSION:
        print(f"unexpected schema: {manifest.get('schema')}", file=sys.stderr)
        return 2
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as zf:
        members = [n for n in zf.namelist() if n != "manifest.json"]
        selected: list[str] = []
        skipped: list[tuple[str, str]] = []
        for name in members:
            pp = validate_member(name)
            category = classify(pp.as_posix())
            if category == "secret" and not args.include_secrets:
                skipped.append((name, "secret requires --include-secrets"))
                continue
            if category == "session" and not args.include_sessions:
                skipped.append((name, "session requires --include-sessions"))
                continue
            out = target / pp
            if out.exists() and not args.overwrite:
                skipped.append((name, "exists; pass --overwrite"))
                continue
            selected.append(name)
        if args.dry_run:
            print(json.dumps({"target": str(target), "would_restore": selected, "skipped": skipped}, indent=2))
            return 0
        backup = backup_conflicts(target, selected) if args.backup else None
        for name in selected:
            pp = validate_member(name)
            out = target / pp
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    print(f"restored={len(selected)} skipped={len(skipped)} target={target}")
    if backup:
        print(f"backup={backup}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export/restore Hermes portable brain archives.")
    p.add_argument("--hermes-home", default=str(default_hermes_home()), help="Hermes home/profile root (default: HERMES_HOME or platform default).")
    sub = p.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("export", help="Create a portable brain archive.")
    ex.add_argument("--output", required=True, help="Output .zip path.")
    ex.add_argument("--include-secrets", action="store_true", help="Include .env/auth* in the archive.")
    ex.add_argument("--include-sessions", action="store_true", help="Include state.db and sessions/.")
    ex.add_argument("--dry-run", action="store_true", help="Print manifest only; do not write archive.")
    ex.set_defaults(func=cmd_export)

    ins = sub.add_parser("inspect", help="Inspect an existing portable brain archive.")
    ins.add_argument("archive")
    ins.add_argument("--summary", action="store_true", help="Print summary only.")
    ins.set_defaults(func=cmd_inspect)

    rs = sub.add_parser("restore", help="Restore from a portable brain archive.")
    rs.add_argument("archive")
    rs.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    rs.add_argument("--include-secrets", action="store_true", help="Restore .env/auth* entries.")
    rs.add_argument("--include-sessions", action="store_true", help="Restore state.db and sessions/.")
    rs.add_argument("--no-backup", dest="backup", action="store_false", help="Do not backup overwritten files.")
    rs.add_argument("--dry-run", action="store_true", help="Show restore plan only.")
    rs.set_defaults(func=cmd_restore, backup=True)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
