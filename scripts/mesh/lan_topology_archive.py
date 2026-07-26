#!/usr/bin/env python3
"""Archive committed LAN topology to gitignored local caches before IP expunge.

Reads private IPs from a git ref (default origin/main), writes:
  - .local/lan-topology-archive.json  (structured backup)
  - .env.local in orama (+ Perpetua when PERPETUA_TOOLS_PATH is set)

Idempotent: never overwrites an existing archive unless --force.
Integrative: dotenv merges fill missing/empty keys only — never replace operator values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_MESH_DIR = Path(__file__).resolve().parent
if str(_MESH_DIR) not in sys.path:
    sys.path.insert(0, str(_MESH_DIR))
from dotenv_merge import harmonize_dotenv_keys
from mesh_logging import get_mesh_logger

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_PATH = ROOT / ".local" / "lan-topology-archive.json"
TRACKED_SOURCES = (
    "bin/orama-system/config/agent_registry.json",
    "config/mac-orchestrator.json",
)
PRIVATE_IP_RE = re.compile(
    r"https?://(?:169\.254|192\.168|10\.\d+|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+(?::\d+)?(?:/v1)?"
)
ENV_KEYS = (
    "LM_STUDIO_WIN_ENDPOINTS",
    "LM_STUDIO_WIN_5080_ENDPOINTS",
    "LM_STUDIO_MAC_ENDPOINT",
    "WINDOWS_IP",
    "LAN_GPU_IP_OVERRIDE",
)
ENV_HEADER = (
    "# LAN topology — harmonized from committed config before IP expunge "
    "(scripts/mesh/lan_topology_archive.py)"
)
log = get_mesh_logger("orama.mesh.lan_topology", repo_root=ROOT)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_show(ref: str, path: str) -> str | None:
    proc = _git("show", f"{ref}:{path}")
    if proc.returncode != 0:
        return None
    return proc.stdout


def normalize_url(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith("/v1"):
        return url
    if re.match(r"https?://[^/]+:\d+$", url):
        return f"{url}/v1"
    return url


def _is_5080_context(text: str, start: int, end: int) -> bool:
    """Classify endpoint from the role/key immediately preceding the matched URL."""
    if ":5080" in text[start:end]:
        return True
    prefix = text[max(0, start - 96) : start]
    nested = re.search(r'"([^"]+)"\s*:\s*\{\s*"url"\s*:\s*"$', prefix)
    if nested:
        return "5080" in nested.group(1).lower()
    immediate = re.search(r'"([^"]+)"\s*:\s*"$', prefix)
    if immediate:
        return "5080" in immediate.group(1).lower()
    return False


def extract_env_map(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for match in PRIVATE_IP_RE.finditer(text):
        url = normalize_url(match.group(0))
        base = url.replace("/v1", "")
        if _is_5080_context(text, match.start(), match.end()):
            env.setdefault("LM_STUDIO_WIN_5080_ENDPOINTS", base)
        else:
            env.setdefault("LM_STUDIO_WIN_ENDPOINTS", base)
    return env


def collect_from_ref(ref: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    for rel in TRACKED_SOURCES:
        text = git_show(ref, rel)
        if not text:
            continue
        merged.update(extract_env_map(text))
    return merged


def load_archive() -> dict | None:
    if not ARCHIVE_PATH.is_file():
        return None
    return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))


def write_archive(env: dict[str, str], *, source_ref: str, source_sha: str) -> None:
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "source_ref": source_ref,
        "source_sha": source_sha,
        "endpoints": env,
    }
    ARCHIVE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def merge_env_file(path: Path, env: dict[str, str]) -> None:
    harmonize_dotenv_keys(
        path,
        env,
        managed_keys=frozenset(ENV_KEYS),
        header_comment=ENV_HEADER,
    )


def target_env_paths() -> list[Path]:
    paths = [ROOT / ".env.local"]
    pt = os.environ.get("PERPETUA_TOOLS_PATH", "").strip()
    if pt:
        paths.append(Path(pt) / ".env.local")
    home_openclaw = Path.home() / ".openclaw" / ".env.lmstudio"
    paths.append(home_openclaw)
    return paths


def backup(ref: str, force: bool) -> int:
    if ARCHIVE_PATH.is_file() and not force:
        log.info(
            "OK: archive exists at %s (use --force to refresh)",
            ARCHIVE_PATH.relative_to(ROOT),
        )
        return 0
    env = collect_from_ref(ref)
    if not env:
        log.info("OK: no private LAN URLs in %s tracked configs — nothing to archive", ref)
        return 0
    sha = _git("rev-parse", ref).stdout.strip() or "unknown"
    write_archive(env, source_ref=ref, source_sha=sha)
    log.info(
        "OK: archived %d endpoint(s) to %s",
        len(env),
        ARCHIVE_PATH.relative_to(ROOT),
    )
    return 0


def apply() -> int:
    data = load_archive()
    if not data:
        log.info("skip: no .local/lan-topology-archive.json")
        return 0
    env = data.get("endpoints") or {}
    if not env:
        return 0
    for path in target_env_paths():
        if path == Path.home() / ".openclaw" / ".env.lmstudio":
            path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent and not path.parent.exists() and path != ROOT / ".env.local":
            continue
        merge_env_file(path, env)
        log.info("OK: merged LAN endpoints into %s", path)
    return 0


def ensure_local_cache() -> int:
    ref = "origin/main"
    if _git("rev-parse", "--verify", ref).returncode != 0:
        ref = "main"
    if not ARCHIVE_PATH.is_file():
        env = collect_from_ref(ref)
        if env:
            sha = _git("rev-parse", ref).stdout.strip() or "unknown"
            write_archive(env, source_ref=ref, source_sha=sha)
            log.info("OK: auto-archived LAN topology from %s", ref)
    return apply()


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive/restore LAN topology locally.")
    parser.add_argument("--backup", action="store_true", help="Archive from git ref")
    parser.add_argument("--apply", action="store_true", help="Merge archive into .env.local targets")
    parser.add_argument("--ensure-local-cache", action="store_true", help="Backup-if-needed then apply")
    parser.add_argument("--ref", default="origin/main", help="Git ref to read committed IPs from")
    parser.add_argument("--force", action="store_true", help="Overwrite existing archive")
    args = parser.parse_args()

    if args.ensure_local_cache:
        return ensure_local_cache()
    if args.backup:
        return backup(args.ref, args.force)
    if args.apply:
        return apply()
    parser.error("choose --backup, --apply, or --ensure-local-cache")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
