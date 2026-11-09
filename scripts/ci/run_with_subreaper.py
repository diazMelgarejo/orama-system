"""Run a command with Linux orphan reaping for containers with an inert PID 1.

Usage: python scripts/ci/run_with_subreaper.py python -m pytest
On other platforms, run the command directly without Linux-specific setup.
"""
from __future__ import annotations

import errno
import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger("run_with_subreaper")
_CLEANUP_SECONDS = 2.0
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def _exitcode_from_status(status: int) -> int:
    """Convert wait status to exit code, preserving 128 + signum convention."""
    code = os.waitstatus_to_exitcode(status)
    return code if code >= 0 else 128 - code


def main(argv: list[str]) -> int:
    """Run argv and return its exit code while reaping adopted Linux children."""
    if not argv:
        logger.error("usage: run_with_subreaper.py COMMAND [ARG ...]")
        return 2
    if sys.platform != "linux":
        return subprocess.call(argv)

    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        error = ctypes.get_errno()
        logger.error("cannot enable child subreaper: %s", os.strerror(error))
        return 1
    proc = subprocess.Popen(argv)
    saved_exit_code: int | None = None
    cleanup_deadline: float | None = None
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline:
                    break
                time.sleep(0.01)
                continue
            if pid == proc.pid:
                saved_exit_code = _exitcode_from_status(status)
                cleanup_deadline = time.monotonic() + _CLEANUP_SECONDS
        except ChildProcessError:
            break
        except OSError as exc:
            if exc.errno == errno.ECHILD:
                break
            raise

    return saved_exit_code if saved_exit_code is not None else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
