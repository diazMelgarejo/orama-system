#!/usr/bin/env python3
"""Gate Hermes/profile installers — detailed reasons logged locally only."""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_NAME = "verify-trusted-install.log"
logger = logging.getLogger(__name__)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def resolve_repo_root() -> Path:
    script = Path(__file__).resolve()
    top = _git(script.parent.parent.parent, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and top.stdout.strip():
        return Path(top.stdout.strip())
    return script.parent.parent.parent


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def log_local(root: Path, ok: bool, reason: str) -> None:
    path = root / ".local" / LOG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    line = f"{stamp}\t{'OK' if ok else 'FAIL'}\t{reason}\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _branch_synced_with_main(root: Path, branch_name: str, head_sha: str) -> tuple[bool, str]:
    remote = _git(root, "rev-parse", "--verify", "origin/main")
    if remote.returncode != 0:
        return False, "origin/main not available"
    origin_sha = remote.stdout.strip()
    if branch_name == "main":
        if head_sha != origin_sha:
            return False, f"main HEAD {head_sha[:12]} != origin/main {origin_sha[:12]}"
        return True, "main matches origin/main"

    scan_script = root / "scripts" / "git" / "reanchor_scan.sh"
    if not scan_script.is_file():
        return False, "reanchor_scan.sh missing"
    result = subprocess.run(
        ["bash", str(scan_script), str(root), "origin/main", "heads"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in (0, 2):
        return False, "reanchor_scan failed"
    scan_ref_re = re.compile(r"^\s+(\S+)\s+(.+)$")
    for line in result.stdout.splitlines():
        match = scan_ref_re.match(line)
        if not match or match.group(1) != branch_name:
            continue
        status = match.group(2)
        if "MERGED/in-main" in status:
            return True, f"branch {branch_name} tree-twin in main"
        if "NEEDS-REANCHOR" in status:
            return False, f"branch {branch_name} needs reanchor onto main"
        if "NO-TWIN" in status or "ORPHAN" in status:
            return False, f"branch {branch_name} not synchronized with main"
    return False, f"branch {branch_name} sync status unknown"


def trusted_install_allowed(root: Path) -> tuple[bool, str]:
    if _truthy("ORAMA_SKIP_HERMES_SYNC"):
        return False, "ORAMA_SKIP_HERMES_SYNC is set"
    if _truthy("ORAMA_TRUST_HERMES_SYNC"):
        return True, "operator override ORAMA_TRUST_HERMES_SYNC=1"
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch.returncode != 0:
        return False, "not a git repository"
    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return False, "cannot resolve HEAD"
    head_sha = head.stdout.strip()
    dirty = _git(root, "status", "--porcelain", "--", "bin/agents", "bin/orama-system/skills/hermes-harness")
    if dirty.returncode != 0:
        return False, "git status failed for harness paths"
    if dirty.stdout.strip():
        return False, "uncommitted changes under bin/agents or hermes-harness"
    synced, sync_reason = _branch_synced_with_main(root, branch.stdout.strip(), head_sha)
    if not synced:
        return False, sync_reason
    return True, f"trusted checkout @ {head_sha[:12]} ({sync_reason})"


def _configure_logging(quiet: bool) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.WARNING if quiet else logging.INFO)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trusted install preconditions.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    _configure_logging(args.quiet)
    root = resolve_repo_root()
    ok, reason = trusted_install_allowed(root)
    log_local(root, ok, reason)
    if not args.quiet:
        if ok:
            logger.info("trusted install check passed")
        else:
            logger.error("trusted install check failed")
            logger.error("see .local/verify-trusted-install.log — never prints topology to stdout")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
