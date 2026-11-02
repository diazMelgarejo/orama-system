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
    proc.wait()
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
        p = real_popen(*a, **kw)
        started.append(p)
        return p

    def boom():
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
