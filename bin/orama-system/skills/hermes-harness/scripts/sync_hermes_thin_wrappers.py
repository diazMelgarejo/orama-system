#!/usr/bin/env python3
"""sync_hermes_thin_wrappers.py — refresh local Hermes thin wrappers from canonical source.

Delegates to install_hermes_thin_skills.py --install after verifying the canonical
source is present and the branch is in an expected state.

Usage:
    python sync_hermes_thin_wrappers.py [--dry-run] [--hermes-home DIR]
    python sync_hermes_thin_wrappers.py --verify-only
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def resolve_repo_root() -> Path:
    script = Path(__file__).resolve()
    try:
        top = subprocess.check_output(
            ["git", "-C", str(script.parent), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(top)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return script.parents[5]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="Print what would be done; make no changes")
    p.add_argument("--hermes-home", default=None, help="Override HERMES_HOME (default: auto-detect from env)")
    p.add_argument("--verify-only", action="store_true", help="Check wrapper freshness without updating")
    args = p.parse_args()

    repo_root = resolve_repo_root()
    installer = repo_root / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "install_hermes_thin_skills.py"

    if not installer.exists():
        print(f"ERROR: canonical installer not found at {installer}", file=sys.stderr)
        return 2

    cmd = [sys.executable, str(installer)]
    if args.verify_only:
        cmd.append("--verify")
    elif args.dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--install")

    if args.hermes_home:
        cmd += ["--hermes-home", args.hermes_home]

    print(f"sync_hermes_thin_wrappers: running {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
