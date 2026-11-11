"""PR2: detached service launcher and Windows launcher lifecycle (static checks)."""
from __future__ import annotations

import importlib.util
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPAWN = ROOT / "scripts" / "lib" / "spawn_detached.py"
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"
FALLBACK_PS1 = ROOT / "platform" / "windows" / "fallback-chain-verify.ps1"
WATCH_PS1 = ROOT / "scripts" / "lm_link_watch.ps1"

CHILD = (
    "import os,sys,time\n"
    "print('env='+os.environ.get('PR2_EXTRA',''), 'unbuf='+os.environ.get('PYTHONUNBUFFERED',''), flush=True)\n"
    "i=0\n"
    "while True:\n"
    "    print('tick', i, flush=True); i+=1; time.sleep(0.1)\n"
)


def _read(path: Path) -> str:
    """Return a file as text with any UTF-8 BOM removed."""
    return path.read_text(encoding="utf-8-sig")


def _kill(pid: int) -> None:
    """Kill a process tree by PID, ignoring errors."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _load_spawn_module():
    """Import scripts/lib/spawn_detached.py as a fresh module."""
    spec = importlib.util.spec_from_file_location("spawn_detached_under_test", SPAWN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _wait_for(predicate, seconds: float = 10.0) -> bool:
    """Poll a predicate until it is true; return False if the timeout passes first."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def test_spawn_detached_keeps_logging_after_launcher_exits(tmp_path):
    """The launcher prints and records the child PID, passes env extras, and the child keeps logging after the launcher exits."""
    log, pidfile = tmp_path / "svc.log", tmp_path / "svc.pid"
    proc = subprocess.run(
        [sys.executable, str(SPAWN), str(log), str(pidfile), str(tmp_path),
         "--env", "PR2_EXTRA=hello world", "--", sys.executable, "-c", CHILD],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    printed = int(proc.stdout.strip().splitlines()[-1])
    try:
        assert pidfile.read_text(encoding="ascii").strip() == str(printed)
        # The launcher has exited; the log must still grow.
        assert _wait_for(lambda: log.exists() and "tick 1" in log.read_text(errors="replace"))
        size1 = log.stat().st_size
        assert _wait_for(lambda: log.stat().st_size > size1), "log stopped growing after launcher exit"
        text = log.read_text(errors="replace")
        assert "env=hello world" in text
        assert "unbuf=1" in text
    finally:
        _kill(printed)


def test_spawn_env_extras_do_not_leak_into_parent(tmp_path, monkeypatch):
    """Env extras reach the child but never change the parent process environment."""
    monkeypatch.delenv("PR2_EXTRA", raising=False)
    mod = _load_spawn_module()
    log, pidfile = tmp_path / "a.log", tmp_path / "a.pid"
    before = dict(os.environ)
    pid = mod.spawn(str(log), str(pidfile), str(tmp_path), {"PR2_EXTRA": "x1"},
                    [sys.executable, "-c", CHILD])
    try:
        assert dict(os.environ) == before
        assert "PR2_EXTRA" not in os.environ
        assert pidfile.read_text(encoding="ascii").strip() == str(pid)
        assert _wait_for(lambda: log.exists() and "env=x1" in log.read_text(errors="replace"))
    finally:
        _kill(pid)


def test_spawn_parse_requires_separator_and_command():
    """_parse needs the -- separator and a command, and splits env extras from the command."""
    mod = _load_spawn_module()
    with pytest.raises(SystemExit):
        mod._parse(["log", "pid", "cwd"])
    with pytest.raises(SystemExit):
        mod._parse(["log", "pid", "cwd", "--"])
    log, pidf, cwd, extras, cmd = mod._parse(["l", "p", "c", "--env", "A=b=c", "--", "x", "--env", "y"])
    assert extras == {"A": "b=c"} and cmd == ["x", "--env", "y"]


@pytest.mark.skipif(os.name != "nt", reason="Windows creation flags")
def test_spawn_uses_windows_detach_flags_and_breakaway_fallback():
    """The launcher source uses the Windows detach flags and a breakaway fallback (Windows only)."""
    src = _read(SPAWN)
    for token in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP", "0x01000000", "PermissionError"):
        assert token in src


# ── static checks on the PowerShell launcher ─────────────────────────────────


def test_start_ps1_no_builtin_shadow_or_in_process_pump():
    """start.ps1 defines Start-OramaService rather than shadowing Start-Service, and uses neither in-process pumps nor Start-Job."""
    src = _read(START_PS1)
    assert not re.search(r"function\s+Start-Service\b", src)
    assert re.search(r"function\s+Start-OramaService\b", src)
    assert "CopyToAsync" not in src
    assert "Start-Job" not in src, "watcher and services must not use Start-Job"


def test_start_ps1_wait_for_port_has_process_exit_branch_and_loopback_probe():
    """Wait-ForPort detects an exited service and shows its log, and the probe host is the loopback address, not the name localhost."""
    src = _read(START_PS1)
    m = re.search(r"function Wait-ForPort \{.*?\n\}\n", src, re.S)
    assert m, "Wait-ForPort not found"
    body = m.group(0)
    assert "$ServicePid" in body and "Life-GetProc $ServicePid" in body
    assert "Life-ShowLogTail" in body and "return $false" in body
    assert "ConnectAsync('localhost'" not in body
    probe = re.search(r"function Life-ProbeHost \{.*?\n\}\n", src, re.S).group(0)
    assert "[System.Net.IPAddress]::Loopback.IPAddressToString" in probe


def test_start_ps1_honest_fallback_and_exit_code():
    """start.ps1 reports the real fallback verification result and exits 1 when a core service failed."""
    src = _read(START_PS1)
    assert "All model tiers verified" not in src, "unconditional echo must be gone"
    assert "$LASTEXITCODE" in src
    assert "fallback-chain-verify.ps1" in src
    assert "exit 1" in src and "$LifeFailed" in src


def test_start_ps1_stop_kills_pid_files_by_ownership_not_name():
    """--stop kills PID-file processes only after an ownership check, never by process name."""
    src = _read(START_PS1)
    stop = src[src.index("if ($Stop) {"):]
    stop = stop[: stop.index("\nexit 0") if False else stop.index("    exit 0")]
    assert "*.pid" in stop and "taskkill" in stop
    assert "Life-PidMatches" in stop
    assert "Stop-Process -Name" not in src and "taskkill.exe /IM" not in src


def test_start_ps1_watcher_is_detached_with_pid_file():
    """The LM Link watcher is started detached with a PID file, and PID files are gitignored."""
    src = _read(START_PS1)
    assert "lm_link_watch.pid" in src
    assert "Life-Spawn" in src.split("LM Link watcher autostart")[1]
    assert (ROOT / ".gitignore").read_text(encoding="utf-8").count(".logs/*.pid") == 1


def test_fallback_chain_verify_has_no_backtick_e_and_gates_on_tier2():
    """fallback-chain-verify.ps1 avoids the backtick-e escape and gates its status-only exit code on Tier 2."""
    src = _read(FALLBACK_PS1)
    assert "`e" not in src
    assert "[char]27" in src
    assert re.search(r"if \(\$StatusOnly\) \{\s*if \(\$Tier2\) \{ exit 0 \} else \{ exit 1 \}", src)


def test_watcher_probes_loopback_address_not_localhost_name():
    """lm_link_watch.ps1 probes the loopback address, not the name localhost."""
    src = _read(WATCH_PS1)
    assert "http://localhost:1234" not in src
    assert "[System.Net.IPAddress]::Loopback.IPAddressToString" in src
