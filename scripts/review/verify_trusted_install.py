#!/usr/bin/env python3
"""Gate Hermes/profile installers — detailed reasons logged locally only."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_NAME = "verify-trusted-install.log"


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
    if dirty.stdout.strip():
        return False, "uncommitted changes under bin/agents or hermes-harness"
    remote = _git(root, "rev-parse", "--verify", "origin/main")
    if remote.returncode == 0:
        origin_sha = remote.stdout.strip()
        on_main = branch.stdout.strip() == "main"
        upstream = _git(root, "merge-base", "--is-ancestor", head_sha, origin_sha)
        if not on_main and upstream.returncode != 0:
            return False, f"branch {branch.stdout.strip()} not based on origin/main"
        behind = _git(root, "rev-list", "--count", f"{head_sha}..{origin_sha}")
        if behind.returncode == 0 and behind.stdout.strip() not in ("", "0"):
            return False, f"behind origin/main by {behind.stdout.strip()}"
        if on_main and head_sha != origin_sha:
            return False, f"main HEAD {head_sha[:12]} != origin/main {origin_sha[:12]}"
    return True, f"trusted checkout @ {head_sha[:12]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trusted install preconditions.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    root = resolve_repo_root()
    ok, reason = trusted_install_allowed(root)
    log_local(root, ok, reason)
    if not args.quiet:
        print("trusted install check passed" if ok else "trusted install check failed")
        if not ok:
            print("see .local/verify-trusted-install.log — never prints topology to stdout", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
