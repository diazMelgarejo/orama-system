#!/usr/bin/env python3
"""Start a long-running service detached from the caller, then exit.

Usage:
    spawn_detached.py LOG PIDFILE CWD [--env KEY=VAL ...] -- CMD [ARGS ...]

The child inherits this process's environment plus the --env extras and
PYTHONUNBUFFERED=1 (so secrets are never put on a command line). Its stdout and
stderr are appended to LOG, stdin is the null device, and the child PID is
written to PIDFILE and printed. This launcher exits immediately and the child
keeps running and keeps logging.
"""
from __future__ import annotations

import os
import subprocess
import sys


def _parse(argv: list[str]) -> tuple[str, str, str, dict[str, str], list[str]]:
    if "--" not in argv:
        raise SystemExit("usage: spawn_detached.py LOG PIDFILE CWD [--env K=V ...] -- CMD ...")
    split = argv.index("--")
    head, cmd = argv[:split], argv[split + 1:]
    if len(head) < 3 or not cmd:
        raise SystemExit("usage: spawn_detached.py LOG PIDFILE CWD [--env K=V ...] -- CMD ...")
    log, pidfile, cwd = head[0], head[1], head[2]
    extras: dict[str, str] = {}
    rest = head[3:]
    i = 0
    while i < len(rest):
        if rest[i] == "--env" and i + 1 < len(rest) and "=" in rest[i + 1]:
            key, _, val = rest[i + 1].partition("=")
            extras[key] = val
            i += 2
        else:
            raise SystemExit(f"unexpected argument: {rest[i]}")
    return log, pidfile, cwd, extras, cmd


def spawn(log: str, pidfile: str, cwd: str, extras: dict[str, str], cmd: list[str]) -> int:
    env = {**os.environ, **extras, "PYTHONUNBUFFERED": "1"}
    os.makedirs(os.path.dirname(os.path.abspath(log)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(pidfile)), exist_ok=True)
    logf = open(log, "ab")
    kwargs: dict = dict(
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=logf,
        stderr=subprocess.STDOUT,
        close_fds=True,
    )
    try:
        if os.name == "nt":
            base = (
                subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
                | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            )
            breakaway = 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
            try:
                proc = subprocess.Popen(cmd, creationflags=base | breakaway, **kwargs)
            except PermissionError:
                proc = subprocess.Popen(cmd, creationflags=base, **kwargs)
            except OSError as exc:
                if getattr(exc, "winerror", None) != 5:
                    raise
                proc = subprocess.Popen(cmd, creationflags=base, **kwargs)
        else:
            proc = subprocess.Popen(cmd, start_new_session=True, **kwargs)
    finally:
        logf.close()
    with open(pidfile, "w", encoding="ascii") as fh:
        fh.write(str(proc.pid))
    return proc.pid


def main(argv: list[str]) -> int:
    log, pidfile, cwd, extras, cmd = _parse(argv)
    pid = spawn(log, pidfile, cwd, extras, cmd)
    print(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
