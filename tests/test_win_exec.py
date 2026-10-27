"""Tests for utils.win_exec: absolute resolution, cmd shim argument refusal, tree termination."""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

import pytest

from utils import win_exec

WIN = sys.platform == "win32"
windows_only = pytest.mark.skipif(not WIN, reason="Windows-specific behaviour")

GRANDCHILD = "import time; time.sleep(120)"
CHILD = textwrap.dedent(
    """
    import subprocess, sys, time
    g = subprocess.Popen([sys.executable, "-c", %r])
    print(g.pid, flush=True)
    time.sleep(120)
    """
) % GRANDCHILD


def _pid_alive(pid: int) -> bool:
    """Whether ``pid`` is still a running process."""
    if WIN:
        return win_exec._win_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@windows_only
def test_resolver_ignores_planted_exe_in_cwd(tmp_path, monkeypatch):
    """A planted exe in the working directory is never returned for a bare name."""
    planted = tmp_path / "zzcli.exe"
    planted.write_bytes(b"MZ")
    other = tmp_path / "bin"
    other.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(other))
    monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)
    with pytest.raises(win_exec.WinExecError):
        win_exec.resolve_executable("zzcli")
    real = other / "zzcli.exe"
    real.write_bytes(b"MZ")
    assert win_exec.resolve_executable("zzcli").lower() == os.path.abspath(real).lower()


@windows_only
def test_resolves_cmd_shim_to_absolute(tmp_path, monkeypatch):
    """A .cmd shim on PATH resolves to its absolute path."""
    shim = tmp_path / "shimcli.cmd"
    shim.write_text("@exit /b 0\r\n")
    monkeypatch.setenv("PATH", str(tmp_path))
    got = win_exec.resolve_executable("shimcli")
    assert os.path.isabs(got) and got.lower().endswith("shimcli.cmd")


@windows_only
def test_refuses_ps1_and_extensionless(tmp_path, monkeypatch):
    """.ps1 and extensionless files are not executables on Windows."""
    (tmp_path / "onlyps.ps1").write_text("x")
    (tmp_path / "noext").write_text("x")
    monkeypatch.setenv("PATH", str(tmp_path))
    for name in ("onlyps", "noext", str(tmp_path / "onlyps.ps1"), str(tmp_path / "noext")):
        with pytest.raises(win_exec.WinExecError):
            win_exec.resolve_executable(name)


def test_resolver_never_falls_back_to_bare_name(tmp_path, monkeypatch):
    """A missing command raises instead of returning the bare name."""
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(win_exec.WinExecError):
        win_exec.resolve_executable("definitely-not-installed-xyz")


METACHARS = ["%", "!", "^", "&", "|", "<", ">", '"', "\n", "\r"]


@pytest.mark.parametrize("ch", METACHARS)
def test_cmd_shim_metacharacters_refused(ch):
    """Each cmd metacharacter in an argument is refused for .cmd and .bat targets."""
    for shim in ("C:\\x\\tool.cmd", "C:\\x\\tool.BAT"):
        with pytest.raises(win_exec.CmdArgumentRefused):
            win_exec.safe_argv(shim, ["ok", "a" + ch + "b"])


def test_cmd_shim_clean_args_pass_and_exe_roundtrips():
    """Clean args pass for shims; .exe targets keep every character."""
    assert win_exec.safe_argv("C:\\x\\tool.cmd", ["hello world", "--flag=1"]) == [
        "C:\\x\\tool.cmd", "hello world", "--flag=1"]
    nasty = ["a&b", "%PATH%", "x|y", '"q"', "l1\nl2"]
    assert win_exec.safe_argv("C:\\x\\tool.exe", nasty)[1:] == nasty


@windows_only
def test_injection_through_cmd_shim_is_inert(tmp_path):
    """The receipt's quote-plus-ampersand injection is refused and never executes."""
    marker = tmp_path / "INJECTED"
    shim = tmp_path / "echo.cmd"
    shim.write_text("@echo off\r\necho %*\r\n")
    payload = 'x" & echo hi > "' + str(marker) + '" & "'
    with pytest.raises(win_exec.CmdArgumentRefused):
        win_exec.safe_argv(str(shim), [payload])
    assert not marker.exists()


def _spawn_tree():
    """Start a python child that spawns a sleeping grandchild; return (proc, grandchild_pid)."""
    proc = subprocess.Popen([sys.executable, "-c", CHILD], stdout=subprocess.PIPE, text=True,
                            **win_exec.popen_tree_kwargs())
    return proc, int(proc.stdout.readline().strip())


def test_terminate_tree_kills_grandchild():
    """terminate_tree kills the grandchild too and reports containment."""
    proc, gpid = _spawn_tree()
    try:
        assert _pid_alive(gpid)
        status = win_exec.terminate_tree(proc)
        assert status == "contained", status
        deadline = time.time() + 5
        while _pid_alive(gpid) and time.time() < deadline:
            time.sleep(0.1)
        assert not _pid_alive(gpid)
        assert proc.poll() is not None
    finally:
        if _pid_alive(gpid):
            os.kill(gpid, 9)
        proc.stdout.close()


def test_terminate_tree_on_exited_child_is_not_overclaimed():
    """On Windows an already-exited child cannot be verified, so the status is unknown."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"], **win_exec.popen_tree_kwargs())
    proc.wait()
    status = win_exec.terminate_tree(proc)
    if WIN:
        assert status == "unknown"
    else:
        assert status in ("unknown", "contained")


def test_escaped_count():
    """escaped_count parses the escaped:<n> status and is 0 otherwise."""
    assert win_exec.escaped_count("escaped:3") == 3
    assert win_exec.escaped_count("contained") == 0
