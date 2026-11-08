"""Exercise the test-suite launcher with real orphaned processes."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "scripts/ci/run_with_subreaper.py"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux subreapers are unavailable")
def test_launcher_reaps_adopted_orphan_while_command_runs() -> None:
    """An orphan exiting during the command is reaped instead of reaching PID 1."""
    command = textwrap.dedent('''\
        import os, subprocess, sys, time
        parent = "import subprocess,sys; p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.3)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(p.pid, flush=True)"
        pid = int(subprocess.check_output([sys.executable, "-c", parent], text=True))
        deadline = time.monotonic() + 5
        while os.path.exists(f"/proc/{pid}") and time.monotonic() < deadline:
            time.sleep(0.02)
        sys.exit(0 if not os.path.exists(f"/proc/{pid}") else 1)
    ''')
    result = subprocess.run([sys.executable, str(LAUNCHER), sys.executable, "-c", command], timeout=15)
    assert result.returncode == 0


@pytest.mark.parametrize("exit_code", [0, 7])
def test_launcher_preserves_command_exit_code(exit_code: int) -> None:
    """The wrapper returns success or the command's original failure code."""
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), sys.executable, "-c", f"raise SystemExit({exit_code})"], timeout=15
    )
    assert result.returncode == exit_code


@pytest.mark.skipif(sys.platform != "linux", reason="Linux subreapers are unavailable")
def test_launcher_preserves_signal_exit_code() -> None:
    """A command terminated by a signal exits with 128 + signum."""
    import signal

    result = subprocess.run(
        [sys.executable, str(LAUNCHER), sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"],
        timeout=15,
    )
    assert result.returncode == 128 + signal.SIGTERM


@pytest.mark.skipif(sys.platform != "linux", reason="Linux subreapers are unavailable")
def test_launcher_bounds_wait_for_lingering_descendant(monkeypatch: pytest.MonkeyPatch) -> None:
    """An indefinitely running adopted child cannot hold the command's exit status hostage."""
    import ctypes

    spec = importlib.util.spec_from_file_location("subreaper_launcher", LAUNCHER)
    assert spec and spec.loader
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    monkeypatch.setattr(ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(prctl=lambda *args: 0))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda argv: SimpleNamespace(pid=123))
    clock = [0.0]
    monkeypatch.setattr(launcher.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(launcher.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration))
    calls = [0]

    def waitpid(pid: int, options: int) -> tuple[int, int]:
        """Simulate a completed command followed by a lingering descendant."""
        calls[0] += 1
        if calls[0] == 1:
            return 123, 7 << 8
        assert options == launcher.os.WNOHANG, "waiting for descendants must not block"
        return 0, 0

    monkeypatch.setattr(launcher.os, "waitpid", waitpid)
    assert launcher.main(["command"]) == 7
    assert clock[0] <= 10
