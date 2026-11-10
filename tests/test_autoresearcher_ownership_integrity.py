"""Owner-record integrity regressions for the AutoResearcher backend lock."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402


@pytest.mark.parametrize("change", ["nonce", "state", "inflight", "resource", "pid", "malformed"])
def test_recheck_refusal_and_release_preserve_changed_bytes(tmp_path: Path, change: str) -> None:
    """Refusal must not replace foreign, changed or unreadable evidence on release."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    record = json.loads(path.read_bytes())
    if change == "nonce":
        record["nonce"] = "foreign"
    elif change == "state":
        record["state"] = "unknown"
    elif change == "inflight":
        record["state"] = "inflight"
    elif change == "resource":
        record["resource"] = "other-backend"
    elif change == "pid":
        record["pid"] = -1
    replacement = b"broken-json" if change == "malformed" else json.dumps(record).encode()
    path.write_bytes(replacement)
    with pytest.raises(arl.LockRefused):
        lock.recheck()
    lock.release("not-sent")
    assert path.read_bytes() == replacement
    assert lock._fd is None


def test_mark_inflight_refuses_changed_record_and_release_preserves_it(tmp_path: Path) -> None:
    """A changed record remains intact even when marking and subsequent release are attempted."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    record = json.loads(path.read_bytes())
    record["nonce"] = "foreign"
    replacement = json.dumps(record).encode()
    path.write_bytes(replacement)
    with pytest.raises(arl.LockRefused):
        lock.mark_inflight()
    lock.release("not-sent")
    assert path.read_bytes() == replacement
    assert lock._fd is None


def test_owned_recheck_prerequisite_refusal_can_release_cleanly(tmp_path: Path) -> None:
    """An unchanged owner can release after a separate prerequisite denies dispatch."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    with pytest.raises(arl.LockRefused):
        lock.recheck(lambda: (False, "gateway recovered"))
    lock.release("not-sent")
    assert arl.inspect(path).state == arl.FREE


@pytest.mark.skipif(sys.platform == "win32", reason="Windows may deny renaming an open lock file")
def test_replaced_path_is_not_treated_as_owned(tmp_path: Path) -> None:
    """Replacing the lock path must not make a different inode eligible for mutation."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    original = path.read_bytes()
    moved = tmp_path / "old.lock"
    path.rename(moved)
    path.write_bytes(original)
    with pytest.raises(arl.LockRefused):
        lock.mark_inflight()
    lock.release("not-sent")
    assert moved.read_bytes() == original
    assert path.read_bytes() == original


def test_changed_file_identity_refuses_portably(tmp_path: Path) -> None:
    """A path that no longer identifies the locked file is never modified."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    original = path.read_bytes()
    with patch.object(arl.os.path, "samestat", return_value=False):
        with pytest.raises(arl.LockRefused):
            lock.mark_inflight()
        lock.release("not-sent")
    assert path.read_bytes() == original
    assert lock._fd is None


def test_dispatcher_refuses_changed_nonce_before_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A replaced owner nonce prevents dispatch and remains as exact evidence."""
    path = tmp_path / "backend.lock"
    monkeypatch.setattr(car, "BACKEND_LOCK_WIN", path)
    actual_recheck = arl.BackendLock.recheck
    replacement: list[bytes] = []

    def change_then_recheck(
        lock: arl.BackendLock, extra_check: Optional[Callable[[], tuple[bool, str]]] = None
    ) -> None:
        """Change the owner record just before the real effect-boundary recheck."""
        record = json.loads(path.read_bytes())
        record["nonce"] = "foreign"
        replacement.append(json.dumps(record).encode())
        path.write_bytes(replacement[0])
        actual_recheck(lock, extra_check)

    with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True}), \
         patch.object(arl.BackendLock, "recheck", change_then_recheck), \
         patch.object(car, "dispatch_cline") as send:
        result = car.dispatch_autoresearcher("windows", "two word prompt")
    assert result["ok"] is False and result["lock_state"] == "refused"
    send.assert_not_called()
    assert path.read_bytes() == replacement[0]


def test_release_verification_exception_preserves_record_and_closes(tmp_path: Path) -> None:
    """An unexpected verification failure must not overwrite evidence or mask refusal."""
    path = tmp_path / "backend.lock"
    lock = arl.BackendLock(path).acquire()
    original = path.read_bytes()
    with patch.object(arl, "_read_record", side_effect=OSError("verification failed")):
        lock.release("not-sent")
    assert path.read_bytes() == original
    assert lock._fd is None
