"""The Cline child process: its command line, its environment, its start and its release."""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
from dataclasses import dataclass, field

from . import signal_relay
from .defaults import KEYVAR
from .proxy_server import AccountingProxyServer


def permission_flags(implement: bool, allow_tool_approval: bool) -> list[str]:
    """Return Cline permission flags: plan unless --implement; auto-approve only if requested."""
    flags: list[str] = []
    if not implement:
        flags.append("--plan")
    flags.extend(["--auto-approve", "true" if allow_tool_approval else "false"])
    return flags


def cline_command(config_dir: str, args: argparse.Namespace) -> list[str]:
    """Return the argv of one Cline run against the throwaway config."""
    cline_bin = shutil.which("cline") or "cline"
    cmd = [
        cline_bin, "--config", config_dir, "-P", "openai-compatible", "-m", args.model,
        "--thinking", args.effort, *permission_flags(args.implement, args.allow_tool_approval),
    ]
    cmd.extend(args.rest)  # the bounds stay here: Cline has no such options, the proxy enforces them
    return cmd


@dataclass
class ClineChild:
    """One Cline process and what the launcher must undo after it. Empty until start() runs."""

    proc: subprocess.Popen | None = None
    group: int | None = None
    received: list[int] = field(default_factory=list)  # signals sent to the launcher, in order
    tools: set[int] = field(default_factory=set)  # processes seen below Cline when a signal arrived
    previous_handlers: dict = field(default_factory=dict)

    def start(self, cmd: list[str], proxy: AccountingProxyServer) -> None:
        """Start Cline without the provider key, relay signals to it and let the proxy stop it."""
        child_env = {k: v for k, v in os.environ.items() if k != KEYVAR}
        own_group = hasattr(os, "killpg")  # POSIX; elsewhere only the direct child can be signalled
        self.proc = subprocess.Popen(cmd, env=child_env, stdin=subprocess.DEVNULL, start_new_session=own_group)
        self.group = self.proc.pid if own_group else None
        if self.group is not None:
            self.previous_handlers = signal_relay.forward_signals(self.group, self.received, self.tools)
        proxy.set_child_proc(self.proc, self.group)

    def release(self, proxy: AccountingProxyServer) -> None:
        """Stop a Cline that is still running, then restore the launcher's signal handlers."""
        if self.proc is not None and self.proc.poll() is None:
            proxy.terminate_child()  # an unexpected error must not leave Cline running
        for signum, handler in self.previous_handlers.items():
            signal.signal(signum, handler)
