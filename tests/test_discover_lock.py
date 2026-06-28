from __future__ import annotations

"""Tests for the cross-platform file-lock helpers added to scripts/discover.py.

The PR replaced direct fcntl calls in _Lock with two new dispatch functions:
  - _try_lock_file(handle): acquires an exclusive non-blocking lock
  - _unlock_file(handle): releases the lock

On POSIX the functions delegate to fcntl.flock; on Windows they use msvcrt.
These tests cover the POSIX path (fcntl available) and the mock-Windows path
(fcntl replaced with None so the msvcrt branch is exercised via a mock).
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
DISCOVER_SCRIPT = ROOT / "scripts" / "discover.py"


def _load_discover():
    spec = importlib.util.spec_from_file_location("discover_test_copy", DISCOVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── _try_lock_file / _unlock_file on POSIX (fcntl branch) ────────────────────

def test_try_lock_file_calls_fcntl_flock(tmp_path):
    """On a POSIX system (fcntl available), _try_lock_file must use fcntl.flock."""
    discover = _load_discover()

    lock_path = tmp_path / "test.lock"
    with open(lock_path, "w") as handle:
        with patch.object(discover, "fcntl") as mock_fcntl:
            # Ensure fcntl is non-None so the fcntl branch is taken.
            discover._try_lock_file(handle)
            # flock must be called exactly once with the file handle as first arg.
            mock_fcntl.flock.assert_called_once()
            call_handle = mock_fcntl.flock.call_args[0][0]
            assert call_handle is handle


def test_unlock_file_calls_fcntl_flock_unlock(tmp_path):
    """On a POSIX system, _unlock_file must call fcntl.flock."""
    discover = _load_discover()

    lock_path = tmp_path / "test.lock"
    with open(lock_path, "w") as handle:
        with patch.object(discover, "fcntl") as mock_fcntl:
            discover._unlock_file(handle)
            mock_fcntl.flock.assert_called_once()
            call_handle = mock_fcntl.flock.call_args[0][0]
            assert call_handle is handle


# ── _try_lock_file / _unlock_file when fcntl is None (msvcrt branch) ─────────

def test_try_lock_file_uses_msvcrt_when_no_fcntl(tmp_path):
    """When discover.fcntl is None, _try_lock_file must fall through to msvcrt."""
    discover = _load_discover()
    mock_msvcrt = MagicMock()
    mock_msvcrt.LK_NBLCK = 2

    lock_path = tmp_path / "test.lock"
    with open(lock_path, "w") as handle:
        discover.fcntl = None
        discover.msvcrt = mock_msvcrt
        discover._try_lock_file(handle)

    mock_msvcrt.locking.assert_called_once()
    args = mock_msvcrt.locking.call_args[0]
    assert args[1] == mock_msvcrt.LK_NBLCK
    assert args[2] == 1  # nbytes=1


def test_unlock_file_uses_msvcrt_when_no_fcntl(tmp_path):
    """When discover.fcntl is None, _unlock_file must fall through to msvcrt."""
    discover = _load_discover()
    mock_msvcrt = MagicMock()
    mock_msvcrt.LK_UNLCK = 0

    lock_path = tmp_path / "test.lock"
    with open(lock_path, "w") as handle:
        discover.fcntl = None
        discover.msvcrt = mock_msvcrt
        discover._unlock_file(handle)

    mock_msvcrt.locking.assert_called_once()
    args = mock_msvcrt.locking.call_args[0]
    assert args[1] == mock_msvcrt.LK_UNLCK
    assert args[2] == 1


def test_try_lock_file_msvcrt_writes_marker_byte(tmp_path):
    """Before calling msvcrt.locking, _try_lock_file must seek+write+flush+seek."""
    discover = _load_discover()
    mock_msvcrt = MagicMock()
    mock_msvcrt.LK_NBLCK = 2

    lock_path = tmp_path / "test.lock"
    with open(lock_path, "w") as handle:
        handle_mock = MagicMock(wraps=handle)
        discover.fcntl = None
        discover.msvcrt = mock_msvcrt
        discover._try_lock_file(handle_mock)

    # Verify the sequence: seek(0) -> write("0") -> flush() -> seek(0) -> locking()
    handle_mock.seek.assert_called()
    handle_mock.write.assert_called_with("0")
    handle_mock.flush.assert_called()


# ── _Lock context manager ─────────────────────────────────────────────────────

def test_lock_acquires_and_releases(tmp_path, monkeypatch):
    """_Lock.__enter__ and __exit__ round-trip without error on POSIX."""
    discover = _load_discover()
    monkeypatch.setattr(discover, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(discover, "_lock_path", lambda: tmp_path / "state" / "discovery.lock")

    with discover._Lock(timeout=2.0):
        pass  # Acquiring and releasing must not raise.


def test_lock_timeout_raises(tmp_path, monkeypatch):
    """When the lock cannot be acquired within the timeout, TimeoutError is raised."""
    discover = _load_discover()
    monkeypatch.setattr(discover, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(discover, "_lock_path", lambda: tmp_path / "state" / "discovery.lock")

    # Make _try_lock_file always raise BlockingIOError to simulate a held lock.
    monkeypatch.setattr(discover, "_try_lock_file", lambda _: (_ for _ in ()).throw(BlockingIOError()))

    with pytest.raises(TimeoutError, match="discovery lock timeout"):
        with discover._Lock(timeout=0.1):
            pass
            pass


def test_lock_propagates_non_contention_os_error(tmp_path, monkeypatch):
    """Permission and path failures must not be mislabeled as lock contention."""
    discover = _load_discover()
    monkeypatch.setattr(discover, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(discover, "_lock_path", lambda: tmp_path / "state" / "discovery.lock")
    monkeypatch.setattr(discover, "_try_lock_file", lambda _: (_ for _ in ()).throw(PermissionError("denied")))

    with pytest.raises(PermissionError, match="denied"):
        with discover._Lock(timeout=0.1):
            pass
