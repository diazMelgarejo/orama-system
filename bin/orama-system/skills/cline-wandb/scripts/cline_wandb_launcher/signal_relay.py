"""Relay the launcher's own INT, TERM and HUP to the Cline child."""
from __future__ import annotations

import signal
import threading

from . import process_tree


def forward_signals(group: int, received: list[int], tools: set[int]) -> dict:
    """Relay the launcher's INT, TERM and HUP to the child's group; return the replaced handlers.

    The child runs in its own session, so a terminal Ctrl-C or a supervisor's TERM reaches only the
    launcher. A second signal means the child did not stop, so the group is killed.
    """

    def relay(signum: int, frame: object) -> None:
        tools.update(process_tree.descendants(group))  # while their parent is still alive
        if received:
            process_tree.signal_group(group, signal.SIGKILL)
            for pid in tools:
                process_tree.signal_pid(pid, signal.SIGKILL)
        else:
            process_tree.signal_group(group, signum)
        received.append(signum)

    previous: dict = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, relay)
    return previous
