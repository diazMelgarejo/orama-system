#!/usr/bin/env python3
"""Gate Hermes/profile installers on a verified orama-system checkout.

Security invariants before writing to $HERMES_HOME or ~/.openclaw workspaces:
  - Operator may set ORAMA_TRUST_HERMES_SYNC=1 after manual review.
  - ORAMA_SKIP_HERMES_SYNC=1 skips all Hermes materialization (install.sh).
  - Default: allow sync only on main aligned with origin/main (when origin exists).
  - ORAMA_VERIFY_COMMIT_SIG=1 requires a GPG-verified HEAD (or origin/main on main).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


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


def verify_commit_signature(root: Path, ref: str) -> tuple[bool, str]:
    """Optional GPG gate — enabled with ORAMA_VERIFY_COMMIT_SIG=1."""
    if not _truthy("ORAMA_VERIFY_COMMIT_SIG"):
        return True, "signature check skipped (set ORAMA_VERIFY_COMMIT_SIG=1 to require)"
    proc = _git(root, "verify-commit", "-q", ref)
    if proc.returncode == 0:
        return True, f"GPG-verified {ref[:12]}"
    return False, f"commit {ref[:12]} is not GPG-verified (git verify-commit failed)"


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

    ok_sig, sig_reason = verify_commit_signature(root, head_sha)
    if not ok_sig:
        return False, sig_reason

    remote = _git(root, "rev-parse", "--verify", "origin/main")
    if remote.returncode == 0:
        origin_sha = remote.stdout.strip()
        on_main = branch.stdout.strip() == "main"
        upstream = _git(root, "merge-base", "--is-ancestor", head_sha, origin_sha)
        if not on_main and upstream.returncode != 0:
            return False, f"branch {branch.stdout.strip()} is not main and not based on origin/main"
        behind = _git(root, "rev-list", "--count", f"{head_sha}..{origin_sha}")
        if behind.returncode == 0 and behind.stdout.strip() not in ("", "0"):
            return (
                False,
                f"checkout is behind origin/main by {behind.stdout.strip()} commit(s); "
                "git fetch origin main && git pull --ff-only",
            )
        if on_main:
            if head_sha != origin_sha:
                ahead = _git(root, "rev-list", "--count", f"{origin_sha}..{head_sha}")
                ahead_n = ahead.stdout.strip() if ahead.returncode == 0 else "?"
                return (
                    False,
                    f"main HEAD ({head_sha[:12]}) != origin/main ({origin_sha[:12]}); "
                    f"ahead by {ahead_n} — pull --ff-only or use ORAMA_TRUST_HERMES_SYNC=1 after review",
                )
            ok_origin_sig, origin_sig_reason = verify_commit_signature(root, origin_sha)
            if not ok_origin_sig:
                return False, origin_sig_reason

    return True, f"trusted checkout @ {head_sha[:12]} ({sig_reason})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trusted install preconditions.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = resolve_repo_root()
    ok, reason = trusted_install_allowed(root)
    if not args.quiet:
        print(reason)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
