"""Tests for utils.win_exec: absolute resolution, cmd shim argument refusal, tree termination."""
from __future__ import annotations

import os
import errno
import signal
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from utils import win_exec

pytest_plugins = ("posix_containment_fixtures",)

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
        import ctypes

        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        handle = k32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
        k32.CloseHandle(ctypes.c_void_p(handle))
        return code.value == 259
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


@windows_only
def test_refuses_interpreter_hosted_pathext_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interpreter-hosted PATHEXT entries cannot become direct process targets."""
    (tmp_path / "tool.vbs").write_text("WScript.Quit 0", encoding="utf-8")
    (tmp_path / "tool.exe").write_bytes(b"MZ")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("PATHEXT", ".VBS;.JS;.EXE")
    assert win_exec.resolve_executable("tool").lower().endswith("tool.exe")
    with pytest.raises(win_exec.WinExecError):
        win_exec.resolve_executable(str(tmp_path / "tool.vbs"))


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
    proc = win_exec.launch_tree([sys.executable, "-c", CHILD], stdout=subprocess.PIPE, text=True)
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
    """A child not started through launch_tree has no authoritative membership: unknown."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"], **win_exec.popen_tree_kwargs())
    proc.wait()
    assert win_exec.terminate_tree(proc) == "unknown"


def test_escaped_count():
    """escaped_count parses the escaped:<n> status and is 0 otherwise."""
    assert win_exec.escaped_count("escaped:3") == 3
    assert win_exec.escaped_count("contained") == 0


MID = textwrap.dedent(
    """
    import subprocess, sys
    g = subprocess.Popen([sys.executable, "-c", %r])
    print(g.pid, flush=True)
    """
) % GRANDCHILD


def test_reparented_orphan_is_killed_and_contained():
    """root->mid->leaf where mid exits right after spawning leaf: leaf must die, status contained."""
    root_code = textwrap.dedent(
        """
        import subprocess, sys, time
        m = subprocess.Popen([sys.executable, "-c", %r], stdout=subprocess.PIPE, text=True)
        print(m.stdout.readline().strip(), flush=True)
        m.wait()
        time.sleep(120)
        """
    ) % MID
    proc = win_exec.launch_tree([sys.executable, "-c", root_code], stdout=subprocess.PIPE, text=True)
    leaf = int(proc.stdout.readline().strip())
    try:
        time.sleep(0.5)
        assert _pid_alive(leaf)
        assert win_exec.terminate_tree(proc) == "contained"
        deadline = time.time() + 5
        while _pid_alive(leaf) and time.time() < deadline:
            time.sleep(0.1)
        assert not _pid_alive(leaf)
    finally:
        if _pid_alive(leaf):
            os.kill(leaf, 9)
        proc.stdout.close()


def test_orphan_after_root_exit_is_contained_by_the_job():
    """The root itself exits first; its orphaned leaf is still in the job and is killed."""
    root_code = textwrap.dedent(
        """
        import subprocess, sys
        g = subprocess.Popen([sys.executable, "-c", %r])
        print(g.pid, flush=True)
        """
    ) % GRANDCHILD
    proc = win_exec.launch_tree([sys.executable, "-c", root_code], stdout=subprocess.PIPE, text=True)
    leaf = int(proc.stdout.readline().strip())
    if WIN:
        proc.wait()
    else:
        deadline = time.monotonic() + 10
        while not win_exec.exited(proc) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert win_exec.exited(proc)
    try:
        assert _pid_alive(leaf)
        assert win_exec.terminate_tree(proc) == "contained"
        deadline = time.time() + 5
        while _pid_alive(leaf) and time.time() < deadline:
            time.sleep(0.1)
        assert not _pid_alive(leaf)
    finally:
        if _pid_alive(leaf):
            os.kill(leaf, 9)
        proc.stdout.close()


def test_unlaunched_process_reports_unknown_not_contained():
    """A process started without launch_tree is never reported contained."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                            **win_exec.popen_tree_kwargs())
    assert win_exec.terminate_tree(proc) == "unknown"
    assert proc.poll() is not None


@windows_only
def test_no_pid_kill_after_the_fact(monkeypatch):
    """The job path never shells out to taskkill by bare PID (PID reuse safety)."""
    calls = []
    monkeypatch.setattr(win_exec, "_taskkill", lambda args: calls.append(args))
    proc = win_exec.launch_tree([sys.executable, "-c", "import time; time.sleep(60)"])
    assert win_exec.terminate_tree(proc) == "contained"
    assert calls == []
    done = subprocess.Popen([sys.executable, "-c", "pass"], **win_exec.popen_tree_kwargs())
    done.wait()
    win_exec.terminate_tree(done)
    assert calls == []


def test_no_cim_or_job_leftovers():
    """The dead after-the-fact job helper and the CIM descendant query are gone."""
    assert not hasattr(win_exec, "_job_terminate")
    assert not hasattr(win_exec, "_win_descendants")


BS = chr(92)
UNC = BS + BS + "srv" + BS + "share" + BS + "bin"


@pytest.mark.parametrize("entry", [".", ".." + BS + "x", "bin", UNC])
def test_relative_and_unc_path_entries_are_dropped(entry, monkeypatch, tmp_path):
    """Relative and UNC PATH entries never reach lookup."""
    monkeypatch.setattr(win_exec, "_win", lambda: True)
    good = os.path.abspath(str(tmp_path))
    monkeypatch.setenv("PATH", os.pathsep.join([entry, good]))
    entries = win_exec._search_path_entries()
    assert entry not in entries
    if os.path.splitdrive(good)[0]:
        assert good in entries


def test_unc_entry_allowed_only_with_flag(monkeypatch):
    """A UNC PATH entry is kept only when the caller opts in."""
    monkeypatch.setattr(win_exec, "_win", lambda: True)
    monkeypatch.setattr(win_exec.os.path, "isabs", lambda p: True)
    monkeypatch.setenv("PATH", UNC)
    assert win_exec._search_path_entries() == ()
    assert win_exec._search_path_entries(allow_unc=True) == (UNC,)


@windows_only
def test_dot_path_entry_does_not_resolve_into_cwd(tmp_path, monkeypatch):
    """PATH with '.' must not return a planted cwd binary."""
    (tmp_path / "zzdot.exe").write_bytes(b"MZ")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", ".;.." + BS + "x")
    with pytest.raises(win_exec.WinExecError):
        win_exec.resolve_executable("zzdot")


def test_relative_candidate_path_is_refused(tmp_path, monkeypatch):
    """A relative path candidate (a relative CODEX_BIN) cannot reach the cwd."""
    (tmp_path / "codex").write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    for cand in ("./codex", "." + BS + "codex", "sub/codex"):
        with pytest.raises(win_exec.WinExecError):
            win_exec.resolve_executable(cand)


@pytest.mark.parametrize("name", ["a.cmd.", "a.cmd ", "a.cmd::$DATA", "A.BAT:x"])
def test_cmd_shim_detection_normalises_names(name):
    """Trailing dots/spaces and NTFS stream suffixes still count as a cmd shim."""
    assert win_exec._is_cmd_shim("C:" + BS + "x" + BS + name)


@pytest.mark.parametrize("code", [1, 9, 27, 31])
def test_cmd_shim_refuses_all_control_chars(code):
    """Every C0 control character is refused for shim arguments."""
    with pytest.raises(win_exec.CmdArgumentRefused):
        win_exec.safe_argv("C:" + BS + "x" + BS + "t.cmd", ["a" + chr(code) + "b"])


def test_scope_note_is_documented_and_exported():
    """The job-scoped caveat is a constant and appears in the docstrings."""
    assert "job-scoped containment" in win_exec.CONTAINMENT_SCOPE_NOTE
    assert "out-of-job launchers" in win_exec.CONTAINMENT_SCOPE_NOTE
    assert "WMI" in win_exec.terminate_tree.__doc__
    assert "WMI" in win_exec.__doc__


@windows_only
def test_wmi_launched_leaf_survives_while_status_is_contained(tmp_path):
    """Documented limit: a leaf made through WMI Win32_Process Create is outside the job."""
    ps = os.path.join(os.environ.get("SystemRoot", "C:" + chr(92) + "Windows"), "System32",
                      "WindowsPowerShell", "v1.0", "powershell.exe")
    if not os.path.exists(ps):
        pytest.skip("powershell.exe not available")
    pidfile = tmp_path / "leaf.pid"
    cmd = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
           "@{CommandLine = '" + sys.executable + " -c \"import time; time.sleep(120)\"'}; "
           "Set-Content -Path '" + str(pidfile) + "' -Value $r.ProcessId; Start-Sleep -Seconds 60")
    proc = win_exec.launch_tree([ps, "-NoProfile", "-NonInteractive", "-Command", cmd])
    leaf = 0
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not (pidfile.exists() and pidfile.read_text().strip()):
            time.sleep(0.2)
        if not (pidfile.exists() and pidfile.read_text().strip()):
            pytest.skip("WMI process creation unavailable")
        leaf = int(pidfile.read_text().strip())
        assert win_exec.terminate_tree(proc) == "contained"
        assert _pid_alive(leaf), "WMI-created leaf is outside the job; the caveat must stay documented"
    finally:
        win_exec.terminate_tree(proc)  # stop the PowerShell root even when the test skipped early
        if leaf and _pid_alive(leaf):
            os.kill(leaf, 9)


@windows_only
def test_job_handle_closed_on_collection_and_kills_leaked_leaf():
    """wait()+del+gc closes the job handle; closing kills a leaf the finished root leaked."""
    import ctypes
    import gc

    root_code = textwrap.dedent(
        """
        import subprocess, sys
        g = subprocess.Popen([sys.executable, "-c", %r])
        print(g.pid, flush=True)
        """
    ) % GRANDCHILD
    proc = win_exec.launch_tree([sys.executable, "-c", root_code], stdout=subprocess.PIPE, text=True)
    leaf = int(proc.stdout.readline().strip())
    proc.wait()
    proc.stdout.close()
    job = proc._win_exec_job
    k32 = ctypes.windll.kernel32
    k32.GetHandleInformation.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    flags = ctypes.c_ulong()
    assert k32.GetHandleInformation(ctypes.c_void_p(job), ctypes.byref(flags))
    assert _pid_alive(leaf)
    del proc
    gc.collect()
    try:
        assert not k32.GetHandleInformation(ctypes.c_void_p(job), ctypes.byref(flags))
        deadline = time.time() + 5
        while _pid_alive(leaf) and time.time() < deadline:
            time.sleep(0.1)
        assert not _pid_alive(leaf)
    finally:
        if _pid_alive(leaf):
            os.kill(leaf, 9)


@windows_only
def test_failed_resume_kills_child_and_raises(monkeypatch):
    """A non-zero NTSTATUS from NtResumeProcess kills the suspended child and raises LaunchError."""
    started = []
    real_popen = subprocess.Popen

    def spy(*a, **kw):
        """Popen wrapper that records every started process."""
        p = real_popen(*a, **kw)
        started.append(p)
        return p

    monkeypatch.setattr(win_exec.subprocess, "Popen", spy)
    monkeypatch.setattr(win_exec, "_nt_resume_process", lambda handle: 0xC0000001)
    with pytest.raises(win_exec.LaunchError):
        win_exec.launch_tree([sys.executable, "-c", "import time; time.sleep(60)"])
    assert started and started[0].poll() is not None


@windows_only
def test_exception_after_suspended_start_kills_child_and_raises(monkeypatch):
    """Any exception between the suspended start and resume kills the child, never leaving it suspended."""
    started = []
    real_popen = subprocess.Popen

    def spy(*a, **kw):
        """Popen wrapper that records every started process."""
        p = real_popen(*a, **kw)
        started.append(p)
        return p

    def boom():
        """Raise to simulate a job API failure."""
        raise OSError("job api exploded")

    monkeypatch.setattr(win_exec.subprocess, "Popen", spy)
    monkeypatch.setattr(win_exec, "_create_kill_on_close_job", boom)
    with pytest.raises(win_exec.LaunchError):
        win_exec.launch_tree([sys.executable, "-c", "import time; time.sleep(60)"])
    assert started and started[0].poll() is not None


@windows_only
def test_job_unavailable_still_runs_and_reports_unknown(monkeypatch):
    """When only the job cannot be created, the child is resumed and runs; status is unknown."""
    monkeypatch.setattr(win_exec, "_create_kill_on_close_job", lambda: None)
    proc = win_exec.launch_tree([sys.executable, "-c", "print('ran')"], stdout=subprocess.PIPE, text=True)
    assert proc.stdout.readline().strip() == "ran"
    proc.wait()
    proc.stdout.close()
    assert win_exec.terminate_tree(proc) == "unknown"


class _MockPosixProc:
    """Mock process object for POSIX tree-termination tests."""

    def __init__(self, pid: int = 4242, running: bool = True) -> None:
        """Initialize mock process with a PID and initial running status."""
        self.pid = pid
        self._running = running
        self._killed = False
        self.returncode = None if running else 0
        self._waitpid_lock = threading.Lock()

    def poll(self) -> Optional[int]:
        """Return process exit code or None if still running."""
        return None if self._running else 0

    def kill(self) -> None:
        """Simulate sending kill signal to process."""
        self._killed = True
        self._running = False

    def wait(self, timeout: Optional[float] = None) -> int:
        """Simulate waiting for process exit."""
        self._running = False
        self.returncode = 0
        return 0


def test_posix_plain_popen_group_leader_accident_reports_unknown(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """An untracked PID is killed directly and never treated as a process group."""
    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    monkeypatch.setattr(
        win_exec.os, "getpgid", lambda pid: (_ for _ in ()).throw(AssertionError(pid)), raising=False,
    )
    monkeypatch.setattr(
        win_exec.os, "killpg", lambda pid, sig: (_ for _ in ()).throw(AssertionError(pid)), raising=False,
    )
    proc = _MockPosixProc(1234, running=True)
    assert win_exec.terminate_tree(proc) == "unknown"
    assert not proc._running


def test_posix_launch_tree_reports_contained_when_group_empty(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """A process launched via launch_tree on POSIX reports contained when the group is empty."""
    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    monkeypatch.setattr(win_exec.os, "getpgid", lambda pid: pid, raising=False)
    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: None, raising=False)

    def _killpg(pid: int, sig: int) -> None:
        """Simulate group signal, raising ProcessLookupError when probing dead group."""
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(win_exec.os, "killpg", _killpg, raising=False)
    proc = _MockPosixProc(2345, running=True)
    proc._win_exec_group = 2345
    assert win_exec.terminate_tree(proc) == "contained"
    assert getattr(proc, "_win_exec_result", None) == "contained"


def test_posix_launch_tree_reports_unknown_on_permission_error(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """A launch_tree process on POSIX reports unknown if killpg raises PermissionError."""
    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    monkeypatch.setattr(win_exec.os, "getpgid", lambda pid: pid, raising=False)
    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: None, raising=False)

    def _killpg(pid: int, sig: int) -> None:
        """Raise PermissionError on killpg to simulate unprivileged signal failure."""
        raise PermissionError

    monkeypatch.setattr(win_exec.os, "killpg", _killpg, raising=False)
    proc = _MockPosixProc(3456, running=True)
    proc._win_exec_group = 3456
    assert win_exec.terminate_tree(proc) == "unknown"


def test_posix_launch_tree_reports_unknown_on_unverified_group(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """A group still present after reaping cannot be attributed to the old leader."""
    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    monkeypatch.setattr(win_exec.os, "getpgid", lambda pid: pid, raising=False)
    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: None, raising=False)
    monkeypatch.setattr(win_exec.os, "killpg", lambda pid, sig: None, raising=False)
    proc = _MockPosixProc(4567, running=True)
    proc._win_exec_group = 4567
    assert win_exec.terminate_tree(proc, grace=0.1) == "unknown"


def test_posix_caller_reaped_root_never_signals_group(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """An already reaped leader cannot authorize any signal to its old PGID."""
    proc = MagicMock(pid=4568, returncode=0)
    proc._waitpid_lock = threading.Lock()
    proc._win_exec_group = proc.pid
    calls = []
    monkeypatch.setattr(win_exec.os, "killpg", lambda pid, sig: calls.append(sig))
    assert win_exec.terminate_tree(proc, grace=0) == "unknown"
    assert not calls


def test_posix_missing_waitid_kills_only_direct_child(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """Without WNOWAIT, clean up the direct child and never signal its group."""
    proc = MagicMock(pid=4573, returncode=None)
    proc._win_exec_group = proc.pid
    proc._waitpid_lock = threading.Lock()
    proc.poll.return_value = None
    monkeypatch.delattr(win_exec.os, "waitid")
    assert win_exec.terminate_tree(proc, grace=0) == "unknown"
    proc.kill.assert_called_once_with()
    proc.wait.assert_called_once_with(timeout=2.0)


@pytest.mark.parametrize("error", [errno.ENOSYS, errno.EINVAL])
def test_posix_unsupported_waitid_kills_only_direct_child(
    monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None, error: int
) -> None:
    """An unsupported waitid implementation falls back without group signals."""
    proc = MagicMock(pid=4574, returncode=None)
    proc._win_exec_group = proc.pid
    proc._waitpid_lock = threading.Lock()
    proc.poll.return_value = None

    def waitid(*args: Any) -> None:
        """Simulate an unavailable kernel operation or unsupported flags."""
        raise OSError(error, "unsupported")

    monkeypatch.setattr(win_exec.os, "waitid", waitid)
    assert win_exec.terminate_tree(proc, grace=0) == "unknown"
    proc.kill.assert_called_once_with()
    proc.wait.assert_called_once_with(timeout=2.0)


def test_posix_probe_eperm_still_escalates_after_revalidation(
    monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None
) -> None:
    """An inconclusive probe cannot prevent KILL of the still-owned group."""
    proc = MagicMock(pid=4575, returncode=None)
    proc._win_exec_group = proc.pid
    proc._waitpid_lock = threading.Lock()
    calls: list[int] = []
    ownership: list[int] = []

    def waitid(*args: Any) -> None:
        """Record each non-reaping ownership check."""
        ownership.append(len(calls))

    def killpg(pid: int, sig: int) -> None:
        """Permit group signals but deny all membership probes."""
        calls.append(sig)
        if sig == 0:
            raise PermissionError

    monkeypatch.setattr(win_exec.os, "waitid", waitid)
    monkeypatch.setattr(win_exec.os, "killpg", killpg)
    assert win_exec.terminate_tree(proc, grace=0.1) == "unknown"
    assert calls[:3] == [signal.SIGTERM, 0, getattr(signal, "SIGKILL", 9)]
    assert ownership[:2] == [0, 2]


def test_posix_identity_loss_prevents_further_group_signals(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """If another waiter reaps the leader, do not escalate against its old PGID."""
    proc = MagicMock(pid=4569, returncode=None)
    proc._waitpid_lock = threading.Lock()
    proc._win_exec_group = proc.pid
    calls = []
    states = iter([None, ChildProcessError()])

    def waitid(*args: Any) -> object:
        """Return one owned-child observation, then simulate external reaping."""
        result = next(states)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(win_exec.os, "waitid", waitid)
    monkeypatch.setattr(win_exec.os, "killpg", lambda pid, sig: calls.append(sig))
    assert win_exec.terminate_tree(proc, grace=0) == "unknown"
    assert calls == [signal.SIGTERM]


def test_posix_eperm_and_reaped_probe_eperm_stays_unknown(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """Permission denial cannot establish containment, even after reaping."""
    proc = MagicMock(pid=4570, returncode=None)
    proc._waitpid_lock = threading.Lock()
    proc._win_exec_group = proc.pid
    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: object())
    monkeypatch.setattr(win_exec.os, "killpg", lambda *args: (_ for _ in ()).throw(PermissionError()))
    assert win_exec.terminate_tree(proc, grace=0) == "unknown"
    proc.wait.assert_called()


def test_posix_eperm_requires_post_reap_absence_proof(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """A later ESRCH, not the preceding EPERM, proves the group is absent."""
    proc = MagicMock(pid=4572, returncode=None)
    proc._waitpid_lock = threading.Lock()
    proc._win_exec_group = proc.pid
    calls = []

    def killpg(pid: int, sig: int) -> None:
        """Deny the signal and report absence on the read-only final probe."""
        calls.append(sig)
        if sig:
            raise PermissionError
        proc.wait.assert_called_once()
        raise ProcessLookupError

    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: object())
    monkeypatch.setattr(win_exec.os, "killpg", killpg)
    assert win_exec.terminate_tree(proc, grace=0) == "contained"
    assert calls == [signal.SIGTERM, 0]


def test_posix_never_sends_signal_after_reaping(monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None) -> None:
    """Escalation precedes wait; only a signal-zero probe may follow reaping."""
    proc = MagicMock(pid=4571, returncode=None)
    proc._waitpid_lock = threading.Lock()
    proc._win_exec_group = proc.pid
    reaped = False
    calls = []

    def wait(*args: Any, **kwargs: Any) -> int:
        """Record the point at which the leader is reaped."""
        nonlocal reaped
        reaped = True
        return 0

    def killpg(pid: int, sig: int) -> None:
        """Record signals and simulate an empty group after wait."""
        calls.append((sig, reaped))
        if reaped and sig == 0:
            raise ProcessLookupError
        if sig:
            assert proc._waitpid_lock.locked()
        assert not reaped

    proc.wait.side_effect = wait
    monkeypatch.setattr(win_exec.os, "waitid", lambda *args: None)
    monkeypatch.setattr(win_exec.os, "killpg", killpg)
    assert win_exec.terminate_tree(proc, grace=0) == "contained"
    assert (signal.SIGTERM, False) in calls and (getattr(signal, "SIGKILL", 9), False) in calls


@pytest.mark.skipif(WIN, reason="POSIX process-group semantics")
def test_posix_sigterm_resistant_tree_is_killed_before_reaping() -> None:
    """A TERM-resistant descendant receives group KILL while the leader is owned."""
    def running_state(pid: int) -> Optional[bool]:
        """Distinguish a live process from absence or a non-running zombie."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return None
        try:
            result = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                text=True, timeout=2, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        state = result.stdout.strip()
        if result.returncode != 0 or not state:
            return None
        return not state.startswith("Z")

    code = (
        "import signal,subprocess,sys,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "p=subprocess.Popen([sys.executable,'-c',"
        "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "print(\"ready\",flush=True); time.sleep(60)'],stdout=subprocess.PIPE); "
        "p.stdout.readline(); "
        "print(p.pid,flush=True); time.sleep(60)"
    )
    proc = win_exec.launch_tree([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    child = int(proc.stdout.readline().strip())
    try:
        assert win_exec.terminate_tree(proc, grace=0.3) == "contained"
        assert proc.returncode is not None
        deadline = time.monotonic() + 5
        state = running_state(child)
        while state is not False and time.monotonic() < deadline:
            time.sleep(0.05)
            state = running_state(child)
        assert state is False, f"descendant is still running or status is unknown: {state}"
    finally:
        if _pid_alive(child):
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.stdout.close()


def test_effective_platform_path_module_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """_pathmod returns ntpath for win32 and posixpath for linux/posix platforms."""
    monkeypatch.setattr(win_exec.sys, "platform", "win32")
    assert win_exec._pathmod() is win_exec.ntpath
    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    assert win_exec._pathmod() is win_exec.posixpath


def test_effective_platform_search_path_entries_windows_and_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATH entries follow effective platform: C:\\bin kept on win32, /bin kept on posix."""
    monkeypatch.setattr(win_exec.sys, "platform", "win32")
    monkeypatch.setenv("PATH", r"C:\bin;C:\tools;.;relative\dir;\\srv\share\bin")
    assert win_exec._search_path_entries() == (r"C:\bin", r"C:\tools")
    assert win_exec._search_path_entries(allow_unc=True) == (r"C:\bin", r"C:\tools", r"\\srv\share\bin")

    monkeypatch.setattr(win_exec.sys, "platform", "linux")
    monkeypatch.setenv("PATH", "/usr/bin:/bin:.:relative/dir")
    assert win_exec._search_path_entries() == ("/usr/bin", "/bin")


def test_windows_emulation_drive_less_rooted_entry_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """On Windows, a drive-less rooted path like \\bin is refused as not truly absolute."""
    monkeypatch.setattr(win_exec.sys, "platform", "win32")
    monkeypatch.setenv("PATH", r"\bin;C:\trusted")
    entries = win_exec._search_path_entries()
    assert r"\bin" not in entries
    assert r"C:\trusted" in entries



@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_cmd_shim_refusal_is_host_independent(monkeypatch: pytest.MonkeyPatch, platform: str) -> None:
    """Shim detection and metacharacter refusal behave the same on every host platform."""
    monkeypatch.setattr(sys, "platform", platform)
    for shim in ("C:\\x\\tool.cmd", "/opt/x/TOOL.BAT", "a.cmd.", "a.cmd::$DATA"):
        with pytest.raises(win_exec.CmdArgumentRefused):
            win_exec.safe_argv(shim, ["a&b"])
    assert win_exec.safe_argv("/opt/x/tool.exe", ["a&b"]) == ["/opt/x/tool.exe", "a&b"]


def test_emulated_windows_resolve_keeps_host_path_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resolved real file is returned in host form, never rewritten by ntpath."""
    binary = tmp_path / "tool.CMD"
    binary.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE;.CMD")
    monkeypatch.setattr(win_exec.shutil, "which", lambda candidate, path=None: str(binary))
    assert win_exec.resolve_executable(str(binary)) == os.path.abspath(str(binary))


GRANDCHILD_HOLDS_STDOUT = (
    "import subprocess, sys; "
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
    "print('root-done')"
)


def test_exited_observes_exit_without_reaping(monkeypatch: pytest.MonkeyPatch) -> None:
    """POSIX exit detection uses waitid(WNOWAIT) and never poll(), so the root stays unreaped."""
    calls: list[tuple[int, int, int]] = []

    def fake_waitid(idtype: int, pid: int, options: int) -> object:
        """Record the call and report an exited child."""
        calls.append((idtype, pid, options))
        return object()

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(win_exec.os, "waitid", fake_waitid, raising=False)
    for name, value in (("P_PID", 1), ("WEXITED", 4), ("WNOWAIT", 0x1000000), ("WNOHANG", 1)):
        monkeypatch.setattr(win_exec.os, name, value, raising=False)
    proc = MagicMock(returncode=None, pid=4321)

    assert win_exec.exited(proc) is True
    proc.poll.assert_not_called()
    assert calls and calls[0][1] == 4321 and calls[0][2] & win_exec.os.WNOWAIT


@pytest.mark.parametrize("error", [errno.ENOSYS, errno.EINVAL])
def test_exited_falls_back_when_waitid_is_unsupported(
    monkeypatch: pytest.MonkeyPatch, posix_process_mocks: None, error: int
) -> None:
    """Unsupported WNOWAIT observes the child through Popen's fallback."""
    proc = MagicMock(pid=4322, returncode=None)
    proc.poll.return_value = None

    def waitid(*args: Any) -> None:
        """Simulate a platform without a usable WNOWAIT operation."""
        raise OSError(error, "unsupported")

    monkeypatch.setattr(win_exec.os, "waitid", waitid)
    assert win_exec.exited(proc) is False
    proc.poll.assert_called_once_with()


@pytest.mark.skipif(WIN, reason="POSIX process-group semantics")
def test_exited_leaves_posix_root_unreaped_until_terminate() -> None:
    """The exited root stays a zombie (group id reserved) until terminate_tree reaps it."""
    proc = win_exec.launch_tree([sys.executable, "-c", "pass"])
    deadline = time.monotonic() + 10
    while not win_exec.exited(proc) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert win_exec.exited(proc) and proc.returncode is None
    assert os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None
    assert win_exec.terminate_tree(proc) == "contained"
    assert proc.returncode == 0


def test_run_tree_returns_when_a_descendant_keeps_the_pipe_open() -> None:
    """An exited root whose child still holds stdout cannot hang the caller."""
    start = time.monotonic()
    run = win_exec.run_tree([sys.executable, "-c", GRANDCHILD_HOLDS_STDOUT], timeout=20, grace=3)
    assert time.monotonic() - start < 15
    assert not run.timed_out and run.returncode == 0
    assert "root-done" in run.stdout
    assert run.containment == "contained"


def test_run_tree_timeout_is_bounded_and_contained() -> None:
    """A root that outlives the timeout is tree-killed and reported as timed out."""
    start = time.monotonic()
    run = win_exec.run_tree([sys.executable, "-c", "import time; time.sleep(60)"], timeout=1, grace=3)
    assert run.timed_out and run.returncode is None
    assert run.containment == "contained"
    assert time.monotonic() - start < 15


def test_resolved_unc_target_refused_unless_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A path that resolves through a link to a UNC share is refused unless UNC is allowed."""
    binary = tmp_path / "tool.EXE"
    binary.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE")
    monkeypatch.setattr(win_exec.shutil, "which", lambda candidate, path=None: str(binary))
    unc = BS * 2 + "srv" + BS + "share" + BS + "tool.EXE"
    monkeypatch.setattr(win_exec.os.path, "realpath", lambda path, *args, **kwargs: unc)
    with pytest.raises(win_exec.WinExecError, match="UNC"):
        win_exec.resolve_executable(str(binary))
    assert win_exec.resolve_executable(str(binary), allow_unc=True) == os.path.abspath(str(binary))


def test_path_hit_linking_to_unc_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A PATH hit whose target is on a UNC share is skipped unless UNC is allowed."""
    (tmp_path / "tool.EXE").write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE")
    monkeypatch.setenv("PATH", str(tmp_path))
    unc = BS * 2 + "srv" + BS + "share" + BS + "tool.EXE"
    monkeypatch.setattr(win_exec.os.path, "realpath", lambda path, *args, **kwargs: unc)
    assert win_exec.find_bare_command("tool") is None
    assert win_exec.find_bare_command("tool", allow_unc=True) is not None


def test_system32_tool_never_guesses_a_drive(monkeypatch: pytest.MonkeyPatch) -> None:
    """System32 comes from the API, else SystemRoot; with neither it raises instead of assuming C:."""
    monkeypatch.setattr(win_exec, "_system_directory_from_api", lambda: "")
    monkeypatch.delenv("SystemRoot", raising=False)
    monkeypatch.delenv("SYSTEMROOT", raising=False)
    with pytest.raises(OSError):
        win_exec.system32_tool("taskkill.exe")
    root = "D:" + BS + "Win"
    monkeypatch.setenv("SystemRoot", root)
    assert win_exec.system32_tool("taskkill.exe") == root + BS + "System32" + BS + "taskkill.exe"
    api = "E:" + BS + "OS" + BS + "system32"
    monkeypatch.setattr(win_exec, "_system_directory_from_api", lambda: api)
    assert win_exec.system32_tool("taskkill.exe") == api + BS + "taskkill.exe"


def test_windows_path_lookup_skips_an_earlier_extensionless_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """A later directly launchable executable wins over an earlier extensionless namesake."""
    early, late = tmp_path / "early", tmp_path / "late"
    early.mkdir()
    late.mkdir()
    (early / "tool").touch()
    executable = late / "tool.EXE"
    executable.touch()
    monkeypatch.setattr(win_exec, "_win", lambda: True)
    monkeypatch.setattr(
        win_exec, "_search_path_entries", lambda allow_unc=False: (str(early), str(late)),
    )
    monkeypatch.setenv("PATHEXT", ".EXE")

    assert Path(win_exec.resolve_executable("tool")).samefile(executable)
