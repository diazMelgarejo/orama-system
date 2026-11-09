#!/usr/bin/env python3
"""Follow-up tests for the AR-WIN-1 backend lock (queue task CLINE-PICKUP-01).

Covers a distinct refusal for a POSIX permission error, a real child-process descriptor-inheritance check,
and safe launching of the npm-installed Cline CLI on Windows without passing prompts through a cmd shim.
"""
from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    """A fresh lock path inside a per-test temporary directory."""
    return tmp_path / "autoresearcher_backend.lock"


def _fake_fcntl_denying() -> types.ModuleType:
    """A stand-in fcntl whose flock raises PermissionError, usable on any platform."""
    module = types.ModuleType("fcntl")
    module.LOCK_EX, module.LOCK_NB, module.LOCK_UN = 2, 4, 8

    def flock(fd, op):
        """Pretend the filesystem denied the lock request."""
        raise PermissionError(13, "Permission denied")

    module.flock = flock
    return module


class TestPermissionErrorIsDistinct:
    """A permission problem must not read as another live owner."""

    def test_acquire_refuses_with_a_permission_reason(self, lock_path):
        """acquire raises a ``refused`` LockRefused that names the permission problem, not ``held``."""
        with patch.object(arl, "_IS_WINDOWS", False), patch.dict(sys.modules, {"fcntl": _fake_fcntl_denying()}):
            with pytest.raises(arl.LockRefused) as exc:
                arl.BackendLock(lock_path).acquire()
        assert exc.value.state == "refused" and "permission" in exc.value.reason.lower()

    def test_inspect_reports_ambiguous_with_a_permission_reason(self, lock_path):
        """inspect never says ``held`` for a permission error; it is ambiguous and says why."""
        lock_path.write_text("", encoding="utf-8")
        with patch.object(arl, "_IS_WINDOWS", False), patch.dict(sys.modules, {"fcntl": _fake_fcntl_denying()}):
            result = arl.inspect(lock_path)
        assert result.state == arl.AMBIGUOUS and "permission" in result.reason.lower()


_HOLDER_WITH_CHILD = """
import subprocess, sys, time
sys.path.insert(0, {scripts!r})
import autoresearcher_lock as arl
lock = arl.BackendLock({path!r}).acquire()
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
print("READY", child.pid, flush=True)
time.sleep(120)
"""


def test_a_spawned_child_does_not_inherit_the_lock(lock_path):
    """Killing the owner frees the OS lock even while its child is still running (no handle inheritance)."""
    code = _HOLDER_WITH_CHILD.format(scripts=str(_SCRIPTS_DIR), path=str(lock_path))
    holder = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    child_pid = None
    try:
        line = holder.stdout.readline().split()
        assert line and line[0] == "READY"
        child_pid = int(line[1])
        holder.kill()
        holder.wait(timeout=10)
        assert arl.process_start_id(child_pid) is not None  # the child is really still alive
        assert arl.inspect(lock_path).state == arl.STALE  # held-stale-unproven, not held by the child
    finally:
        holder.kill()
        if child_pid:
            subprocess.run(["taskkill", "/F", "/PID", str(child_pid)] if sys.platform == "win32" else ["kill", "-9", str(child_pid)],
                           capture_output=True)


class TestClineShimLaunch:
    """An npm .cmd shim is never given a prompt; the node entry script is launched directly."""

    @staticmethod
    def _layout(tmp_path: Path, with_entry: bool = True) -> Path:
        """Create a fake npm global layout with a cmd shim, node.exe and (optionally) the cline entry script."""
        (tmp_path / "cline.cmd").write_text("@echo off\n", encoding="utf-8")
        (tmp_path / "node.exe").write_text("", encoding="utf-8")
        if with_entry:
            entry = tmp_path / "node_modules" / "cline" / "bin"
            entry.mkdir(parents=True)
            (entry / "cline").write_text("#!/usr/bin/env node\n", encoding="utf-8")
        return tmp_path / "cline.cmd"

    def test_cmd_shim_resolves_to_node_plus_entry(self, tmp_path):
        """The launcher for ``cline.cmd`` is [node, entry script], never the shim itself."""
        shim = self._layout(tmp_path)
        assert car._cline_launcher(str(shim)) == [str(tmp_path / "node.exe"), str(tmp_path / "node_modules" / "cline" / "bin" / "cline")]

    def test_cmd_shim_without_an_entry_is_refused(self, tmp_path):
        """If the node entry cannot be resolved the shim is refused rather than used."""
        shim = self._layout(tmp_path, with_entry=False)
        assert car._cline_launcher(str(shim)) is None
        with patch.object(car, "_find_cline", return_value=str(shim)):
            result = car.cline_available()
        assert result["available"] is False and "shim" in result["reason"]

    def test_plain_binary_is_launched_directly(self):
        """A normal executable is its own launcher."""
        assert car._cline_launcher("cline") == ["cline"]

    def test_argv_for_a_shim_starts_with_node_and_the_entry(self, tmp_path, monkeypatch):
        """_cline_argv builds [node, entry, ..., prompt] for an npm shim, with the prompt last and positional."""
        monkeypatch.delenv("CLINE_PROVIDER", raising=False)
        monkeypatch.delenv("CLINE_MODEL", raising=False)
        shim = self._layout(tmp_path)
        argv = car._cline_argv(str(shim), "a safe prompt & echo hacked")
        assert argv[0] == str(tmp_path / "node.exe") and argv[1].endswith("cline")
        assert argv[-1] == "a safe prompt & echo hacked" and "cline.cmd" not in " ".join(argv[:-1])

    def test_windows_discovery_finds_cline_cmd_when_there_is_no_exe(self, tmp_path, monkeypatch):
        """On Windows, discovery falls back to ``cline.cmd`` from PATH (the npm global install layout)."""
        shim = self._layout(tmp_path)
        monkeypatch.delenv("CLINE_BIN", raising=False)
        with patch.object(car, "_is_windows", return_value=True), \
             patch.object(car.shutil, "which", side_effect=lambda name: str(shim) if name == "cline.cmd" else None):
            assert car._find_cline() == str(shim)
