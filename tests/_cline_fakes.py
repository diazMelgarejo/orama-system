"""Small fakes for the Cline dispatch tests: a Popen stand-in with scripted output and failures."""
from __future__ import annotations

from typing import Optional


class FakeProc:
    """A subprocess.Popen stand-in: scripted return code, output, and an optional error on the first communicate()."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "", comm_exc: Optional[BaseException] = None) -> None:
        """Store the scripted result; *comm_exc* is raised by the first communicate() call only."""
        self.returncode = returncode
        self._out, self._err = stdout, stderr
        self._exc = comm_exc
        self.killed = False

    def communicate(self, timeout: Optional[float] = None):
        """Return (stdout, stderr), raising the scripted error once (like a timeout or a broken pipe)."""
        if self._exc is not None:
            exc, self._exc = self._exc, None
            raise exc
        return self._out, self._err

    def kill(self) -> None:
        """Record that the process was killed."""
        self.killed = True
