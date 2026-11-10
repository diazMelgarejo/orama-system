"""Native Windows OS-lock evidence for scripts/autoresearcher_lock.py.

All multi-process scenarios launch real Python children running _lock_helper_native.py.
There are deliberately no lock mocks or thread-based process substitutes. Test artifacts
stay under tests/ rather than using the system temporary directory.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import autoresearcher_lock as arl  # noqa: E402

_HELPER = Path(__file__).resolve().with_name("_lock_helper_native.py")
_TESTS_DIR = Path(__file__).resolve().parent
_SKIP_REASON = "native Windows LockFileEx evidence requires Windows"


@pytest.fixture
def native_dir():
    """Create and remove a per-test directory inside this worktree."""
    with tempfile.TemporaryDirectory(prefix="_native_lock_", dir=_TESTS_DIR) as directory:
        yield Path(directory)


def _spawn(*arguments: object) -> subprocess.Popen:
    """Launch the helper with the same real interpreter that is running pytest."""
    return subprocess.Popen(
        [sys.executable, str(_HELPER), *(str(argument) for argument in arguments)],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )


def _wait_event(path: Path, process: subprocess.Popen, timeout: float = 15) -> dict:
    """Wait for a child's atomic event without an unbounded pipe read."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"child {process.pid} exited {process.returncode} before {path.name}: "
                f"stdout={stdout!r} stderr={stderr!r}"
            )
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {path} from child {process.pid}")


def _finish(process: subprocess.Popen) -> None:
    stdout, stderr = process.communicate(timeout=15)
    assert process.returncode == 0, f"child failed: stdout={stdout!r} stderr={stderr!r}"


def _release_holder(process: subprocess.Popen, release_path: Path) -> None:
    release_path.write_text("release\n", encoding="utf-8")
    try:
        _finish(process)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=10)
        raise


def _cleanup(process: subprocess.Popen | None, release_path: Path | None = None) -> None:
    """Best-effort cleanup that cannot leave a live holder or full output pipe behind."""
    if process is None:
        return
    if release_path is not None and process.poll() is None:
        release_path.write_text("release\n", encoding="utf-8")
    if process.poll() is None:
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
    if process.poll() is None:
        process.wait(timeout=10)
    streams_open = any(
        stream is not None and not stream.closed
        for stream in (process.stdout, process.stderr)
    )
    if streams_open:
        process.communicate()


def _hard_terminate(process: subprocess.Popen, owner_pid: int) -> None:
    """Terminate the real lock-owning interpreter without running Python cleanup."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(0x0001, False, owner_pid)  # PROCESS_TERMINATE
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel32.TerminateProcess(handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)
    process.wait(timeout=10)
    process.communicate()


@pytest.mark.skipif(sys.platform != "win32", reason=_SKIP_REASON)
def test_s1_native_cross_process_contention(native_dir: Path) -> None:
    """Two real racing acquirers produce one winner and one held refusal."""
    lock_path = native_dir / "contended.lock"
    events = [native_dir / f"event-{index}.json" for index in range(2)]
    releases = [native_dir / f"release-{index}" for index in range(2)]
    processes = [
        _spawn("hold", lock_path, event, release)
        for event, release in zip(events, releases)
    ]
    try:
        results = [_wait_event(event, process) for event, process in zip(events, processes)]
        assert sorted(result["outcome"] for result in results) == ["acquired", "refused"]
        refused = next(result for result in results if result["outcome"] == "refused")
        assert refused["state"] == arl.HELD
        assert len({result["pid"] for result in results}) == 2
        assert all(result["pid"] != os.getpid() for result in results)
        winner = next(result for result in results if result["outcome"] == "acquired")
        assert arl.process_start_id(winner["pid"]) == winner["start_id"]
        held = arl.inspect(lock_path)
        assert held.state == arl.HELD
        assert held.owner is not None and held.owner["pid"] == winner["pid"]
        for process, result, release in zip(processes, results, releases):
            if result["outcome"] == "acquired":
                _release_holder(process, release)
            else:
                _finish(process)
    finally:
        for process, release in zip(processes, releases):
            _cleanup(process, release)


@pytest.mark.skipif(sys.platform != "win32", reason=_SKIP_REASON)
def test_s2_native_hard_kill_stale_and_reconcile(native_dir: Path) -> None:
    """A hard-killed owner leaves non-free evidence until an operator reconciles it."""
    lock_path = native_dir / "crashed.lock"
    event_path = native_dir / "acquired.json"
    release_path = native_dir / "release"
    holder = _spawn("hold", lock_path, event_path, release_path)
    try:
        acquired = _wait_event(event_path, holder)
        assert acquired["outcome"] == "acquired"
        assert acquired["pid"] != os.getpid()
        assert arl.process_start_id(acquired["pid"]) == acquired["start_id"]
        assert arl.inspect(lock_path).state == arl.HELD
        _hard_terminate(holder, acquired["pid"])
    finally:
        _cleanup(holder)

    assert arl.process_start_id(acquired["pid"]) is None
    crashed = arl.inspect(lock_path)
    assert crashed.state in {arl.STALE, arl.AMBIGUOUS}
    assert crashed.state != arl.FREE
    with pytest.raises(arl.LockRefused) as refusal:
        arl.BackendLock(lock_path).acquire()
    assert refusal.value.state in {arl.STALE, arl.AMBIGUOUS}

    arl.reconcile(lock_path, operator="native-crash-operator", note="confirmed child was terminated")
    reconciled = arl.inspect(lock_path)
    assert reconciled.state == arl.FREE
    assert reconciled.owner is not None
    assert reconciled.owner["operator"] == "native-crash-operator"
    assert reconciled.owner["note"] == "confirmed child was terminated"


@pytest.mark.skipif(sys.platform != "win32", reason=_SKIP_REASON)
def test_s3_native_stale_identity_is_unverified(native_dir: Path) -> None:
    """A live OS lock with a real exited PID in its record is not declared dead."""
    lock_path = native_dir / "identity.lock"
    holder_event = native_dir / "holder.json"
    holder_release = native_dir / "holder-release"
    identity_event = native_dir / "exited-identity.json"
    holder = _spawn("hold", lock_path, holder_event, holder_release)
    identity_process = None
    original_bytes = None
    try:
        acquired = _wait_event(holder_event, holder)
        assert acquired["outcome"] == "acquired"
        original_bytes = lock_path.read_bytes()
        original_record = json.loads(original_bytes)
        assert original_record["pid"] == acquired["pid"]
        live = arl.inspect(lock_path)
        assert live.state == arl.HELD
        assert live.owner is not None and live.owner["identity"] == "match"

        identity_process = _spawn("identity", identity_event)
        exited = _wait_event(identity_event, identity_process)
        _finish(identity_process)
        assert exited["start_id"]
        assert arl.process_start_id(exited["pid"]) is None

        stale_record = dict(
            original_record,
            pid=exited["pid"],
            start_id=exited["start_id"],
        )
        lock_path.write_text(json.dumps(stale_record, sort_keys=True), encoding="utf-8")
        stale = arl.inspect(lock_path)
        assert stale.state == arl.HELD
        assert stale.owner is not None
        assert stale.owner["pid"] == exited["pid"] != acquired["pid"]
        assert stale.owner["identity"] == "unverified"
        assert stale.owner["identity"] != "dead"
    finally:
        if original_bytes is not None and lock_path.exists():
            lock_path.write_bytes(original_bytes)
        _cleanup(identity_process)
        _cleanup(holder, holder_release)


@pytest.mark.skipif(sys.platform != "win32", reason=_SKIP_REASON)
def test_s4_native_release_outcomes_and_validation(native_dir: Path) -> None:
    """Every valid outcome persists its real record; an invalid outcome is rejected."""
    expected = {
        "completed": ("released", arl.FREE),
        "not-sent": ("released", arl.FREE),
        "unknown": ("unknown", arl.AMBIGUOUS),
    }
    for outcome, (record_state, inspection_state) in expected.items():
        lock_path = native_dir / f"outcome-{outcome}.lock"
        lock = arl.BackendLock(lock_path).acquire()
        lock.release(outcome)
        assert lock_path.exists()
        record = json.loads(lock_path.read_text(encoding="utf-8"))
        assert record["state"] == record_state
        assert arl.inspect(lock_path).state == inspection_state

    invalid_path = native_dir / "invalid-outcome.lock"
    lock = arl.BackendLock(invalid_path).acquire()
    try:
        with pytest.raises(ValueError, match="unknown outcome"):
            lock.release("not-a-valid-outcome")
    finally:
        lock.release("not-sent")
    assert invalid_path.exists()
    assert json.loads(invalid_path.read_text(encoding="utf-8"))["state"] == "released"


@pytest.mark.skipif(sys.platform != "win32", reason=_SKIP_REASON)
def test_s5_native_reconcile_operator_note_gate(native_dir: Path) -> None:
    """Reconcile requires both attribution fields and records them when clearing state."""
    lock_path = native_dir / "reconcile.lock"
    lock = arl.BackendLock(lock_path).acquire()
    lock.release("unknown")
    before = lock_path.read_bytes()
    assert arl.inspect(lock_path).state == arl.AMBIGUOUS

    for operator, note in (("", "a note"), ("operator", ""), ("   ", "a note"), ("operator", " \t ")):
        with pytest.raises(ValueError, match="non-blank operator and note"):
            arl.reconcile(lock_path, operator=operator, note=note)
        assert lock_path.read_bytes() == before

    arl.reconcile(
        lock_path,
        operator="  native-operator  ",
        note="  verified that no request remained in flight  ",
    )
    result = arl.inspect(lock_path)
    assert result.state == arl.FREE
    assert result.owner is not None
    assert result.owner["state"] == "released"
    assert result.owner["operator"] == "native-operator"
    assert result.owner["note"] == "verified that no request remained in flight"
    assert lock_path.exists()
