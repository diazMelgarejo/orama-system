"""Run a command with Linux orphan reaping for containers with an inert PID 1.

Usage: python scripts/ci/run_with_subreaper.py python -m pytest
On other platforms, run the command directly without Linux-specific setup.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time


def main(argv: list[str]) -> int:
    """Run argv and return its exit code while reaping adopted Linux children."""
    if not argv:
        print("usage: run_with_subreaper.py COMMAND [ARG ...]", file=sys.stderr)
        return 2
    if sys.platform != "linux":
        return subprocess.call(argv)

    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        error = ctypes.get_errno()
        print(f"cannot enable child subreaper: {os.strerror(error)}", file=sys.stderr)
        return 1
    proc = subprocess.Popen(argv)
    while True:
        pid, status = os.waitpid(-1, os.WNOHANG)
        if pid == proc.pid:
            proc.returncode = os.waitstatus_to_exitcode(status)
            return proc.returncode if proc.returncode >= 0 else 128 - proc.returncode
        if pid == 0:
            time.sleep(0.01)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
