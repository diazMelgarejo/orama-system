"""Test-only helper: keep offline tests from launching a real model, whatever the shell exports.

`install(monkeypatch)` clears the operator approval variables and wraps every subprocess entry point so
that a call whose argv names the real launcher raises instead of running. Other subprocess calls pass
through unchanged, so tests that run the sandbox or a plain interpreter still work.
"""

from __future__ import annotations

import os
import subprocess

APPROVAL_VARIABLES = ("BIAFRA_ORCHESTRATOR_GATE", "BIAFRA_ALLOW_LAUNCH")
LAUNCHER_MARKER = "launch_cline_wandb"
_ENTRY_POINTS = ("run", "Popen", "call", "check_call", "check_output")


def _names_launcher(args) -> bool:
    if isinstance(args, (str, bytes, os.PathLike)):
        return LAUNCHER_MARKER in os.fsdecode(args)
    try:
        return any(LAUNCHER_MARKER in os.fsdecode(a) for a in args)
    except TypeError:
        return False


def install(monkeypatch) -> None:
    for name in APPROVAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    for entry in _ENTRY_POINTS:
        real = getattr(subprocess, entry)

        def guarded(args, *a, __real=real, **kw):
            if _names_launcher(args):
                raise AssertionError("an offline test tried to start the real launcher")
            return __real(args, *a, **kw)

        monkeypatch.setattr(subprocess, entry, guarded)
