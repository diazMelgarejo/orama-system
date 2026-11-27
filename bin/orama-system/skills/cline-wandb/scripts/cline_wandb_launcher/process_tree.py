"""Process lookup and signalling: Cline's process group and the processes below it.

Other modules call these as `process_tree.<name>`, so each has one place where a test can replace it.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time

TERMINATE_GRACE_S = 2.0


def signal_group(group: int, signum: int) -> bool:
    """Send `signum` to a process group; False once no member is left to receive it."""
    try:
        os.killpg(group, signum)
    except OSError:
        return False
    return True


def descendants(root: int) -> set[int]:
    """Processes below `root` right now, except Cline's shared hub daemon and what it started.

    Cline runs each tool command in a new session, outside the child's group, and once the parent dies the
    command can no longer be traced to it. So take this list before signalling. Empty if `ps` fails.
    """
    try:
        listing = subprocess.run(["ps", "-Ao", "pid=,ppid=,command="], capture_output=True, text=True,
                                 errors="replace", timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    children: dict[int, list[int]] = {}
    for line in listing.splitlines():
        fields = line.split(None, 2)
        if len(fields) >= 2 and "--cline-hub-daemon" not in (fields[2] if len(fields) > 2 else ""):
            children.setdefault(int(fields[1]), []).append(int(fields[0]))
    found: set[int] = set()
    queue = [root]
    while queue:
        for pid in children.get(queue.pop(), []):
            if pid not in found:
                found.add(pid)
                queue.append(pid)
    return found


def signal_pid(pid: int, signum: int) -> bool:
    """Send `signum` to one process; False once it is gone."""
    try:
        os.kill(pid, signum)
    except OSError:
        return False
    return True


def terminate_group(proc: subprocess.Popen, group: int, tools: set[int] | None = None) -> None:
    """Terminate the child's group and the tool processes below it, escalating to SIGKILL.

    `cline` is a wrapper that starts the real program as its own child, so signalling only `proc`
    would leave the program that does the work running. `tools` adds processes already seen below it.
    """
    below = descendants(group) | (tools or set())
    signalled = signal_group(group, signal.SIGTERM)
    if not signalled and not below:
        return
    deadline = time.monotonic() + TERMINATE_GRACE_S
    while time.monotonic() < deadline:
        proc.poll()  # reap the leader, otherwise its zombie keeps the group alive
        if not signal_group(group, 0) and not any(signal_pid(pid, 0) for pid in below):
            return
        time.sleep(0.05)
    signal_group(group, signal.SIGKILL)
    for pid in below:
        signal_pid(pid, signal.SIGKILL)
    proc.poll()


def terminate_proc(proc: subprocess.Popen, group: int | None = None) -> None:
    """Terminate child process fail-closed, escalating to kill after a short grace period.

    With `group` (the child leads its own process group) the whole group is terminated.
    """
    if group is not None:
        terminate_group(proc, group)
        return
    try:
        proc.terminate()
    except (OSError, ProcessLookupError):
        return
    try:
        proc.wait(timeout=TERMINATE_GRACE_S)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except (OSError, ProcessLookupError):
            pass
    except (OSError, ValueError):
        pass
