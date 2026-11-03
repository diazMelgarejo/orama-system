"""spawn_detached must report, not hide, a refused CREATE_BREAKAWAY_FROM_JOB."""
from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

SPAWN = Path(__file__).resolve().parents[1] / "scripts" / "lib" / "spawn_detached.py"


def _load() -> ModuleType:
    """Import spawn_detached.py as a fresh module."""
    spec = importlib.util.spec_from_file_location("spawn_detached_breakaway", SPAWN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_popen(deny_breakaway: bool) -> tuple[Callable[..., MagicMock], list[int]]:
    """Popen stand-in that raises PermissionError when the breakaway flag is passed."""
    calls: list[int] = []

    def popen(cmd: list[str], creationflags: int = 0, **kwargs: object) -> MagicMock:
        """Record the call; refuse breakaway when asked."""
        calls.append(creationflags)
        if deny_breakaway and creationflags & 0x01000000:
            raise PermissionError("breakaway denied")
        proc = MagicMock()
        proc.pid = 4242
        return proc

    return popen, calls


@pytest.mark.parametrize("denied", [True, False])
def test_breakaway_status_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    denied: bool,
) -> None:
    """Denied breakaway yields breakaway=unavailable plus a stderr warning; PID stays last."""
    mod = _load()
    popen, calls = _fake_popen(denied)
    monkeypatch.setattr(mod.os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(mod.subprocess, "Popen", popen)
    rc = mod.main([str(tmp_path / "l.log"), str(tmp_path / "p.pid"), str(tmp_path), "--", "x"])
    out, err = capsys.readouterr()
    lines = out.split()
    assert rc == 0 and lines[-1] == "4242"
    if denied:
        assert lines[0] == "breakaway=unavailable"
        assert "WARNING" in err and "kills its processes on close" in err
        assert len(calls) == 2
    else:
        assert "breakaway" not in out and err == ""
