"""The launcher's exit code once Cline has exited: 124, 128 plus a signal number, or Cline's own.

124 means spend is breached or not fully accounted, and callers settle it as unknown spend.
"""
from __future__ import annotations

import sys

from . import process_tree
from .cline_process import ClineChild
from .proxy_server import AccountingProxyServer

DRAIN_TIMEOUT_S = 5.0
EXIT_UNACCOUNTED = 124


def exit_code(proxy: AccountingProxyServer, child: ClineChild, child_rc: int) -> int:
    """Drain the proxy, then decide. 124 outranks a relayed signal, which outranks Cline's own code."""
    if not proxy.stop_and_drain(timeout_s=DRAIN_TIMEOUT_S):
        return _fail_closed(
            proxy, f"proxy accounting did not drain within {DRAIN_TIMEOUT_S}s; exiting 124 (spend not fully accounted)")
    if proxy.boundary_error:
        # The handler thread that started the termination dies with this process, so finish it here.
        return _fail_closed(proxy, f"{proxy.boundary_error[0]}; terminating fail-closed")
    if child.received:
        if child.group is not None:
            process_tree.terminate_group(child.proc, child.group, child.tools)
        return 128 + child.received[0]
    return child_rc


def _fail_closed(proxy: AccountingProxyServer, reason: str) -> int:
    sys.stderr.write(f"ERROR: {reason}\n")
    proxy.terminate_child()
    return EXIT_UNACCOUNTED
