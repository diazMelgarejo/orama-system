"""Test-only helper: a fake ``subprocess.Popen`` driven by a plain ``run``-style function.

``as_popen(runner)`` returns a stand-in for ``subprocess.Popen``. Construction always succeeds (the
process "started"); ``communicate`` calls ``runner(argv, timeout=..., **popen_kwargs)`` and hands back its stdout and
stderr, so anything the runner raises (a timeout, an OSError, an interrupt) is raised after the start,
exactly where a real wait can fail. ``kill`` and a second ``communicate`` model the reaping step.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

Runner = Callable[..., subprocess.CompletedProcess[Any]]
Output = bytes | str | None


class FakeProc:
    """A started process whose wait is simulated by ``runner``."""

    def __init__(self, argv: Any, runner: Runner, kwargs: dict[str, Any]) -> None:
        """Remember the launch; nothing runs until ``communicate``."""
        self.argv, self._runner, self.kwargs = argv, runner, kwargs
        self.returncode = None
        self.killed = False
        self.communicate_calls = 0

    def communicate(self, input: Any = None, timeout: float | None = None) -> tuple[Output, Output]:
        """Run the simulated wait once; a call after ``kill`` just reaps and returns no output."""
        self.communicate_calls += 1
        if self.killed:
            self.returncode = -9
            return b"", b""
        completed = self._runner(self.argv, timeout=timeout, **self.kwargs)
        self.returncode = completed.returncode
        return completed.stdout, completed.stderr

    def __enter__(self) -> FakeProc:
        """Context-manager entry, as the real Popen supports."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Context-manager exit: reap like the real Popen."""
        self.wait()

    def poll(self) -> int | None:
        """None while the process has not finished, else its return code."""
        return self.returncode

    def kill(self) -> None:
        """Record that the process was killed."""
        self.killed = True

    def wait(self, timeout: float | None = None) -> int | None:
        """Reap: the return code, -9 after a kill."""
        if self.killed and self.returncode is None:
            self.returncode = -9
        return self.returncode


def as_popen(runner: Runner, procs: list[FakeProc] | None = None) -> Callable[..., FakeProc]:
    """A ``Popen`` replacement whose process behaves as ``runner(argv, timeout=...)`` says.

    Each started process is appended to ``procs`` when given, so a test can inspect kill and reap.
    """

    def popen(argv: Any, **kwargs: Any) -> FakeProc:
        """Start the fake process."""
        proc = FakeProc(argv, runner, kwargs)
        if procs is not None:
            procs.append(proc)
        return proc

    return popen
