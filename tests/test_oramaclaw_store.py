from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from oramaclaw.store import (
    JOURNAL_CAP,
    LOCK_STALE_SECONDS,
    ControlStore,
    LockHeld,
    _acquire_lock,
    _fingerprint,
    _release_lock,
)
from oramaclaw.types import ConfigTarget, Conflict, PendingResolution


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _target(tmp_path: Path) -> ConfigTarget:
    return ConfigTarget(
        workspace_root=tmp_path / "ws",
        config_path=tmp_path / "ws" / "openclaw.json",
        state_dir=tmp_path / "state",
    )


def _conflict(rid: str = "r1") -> Conflict:
    return Conflict(
        resource_key="provider:test",
        manager="oramaclaw",
        managed_path="/effort",
        base_fingerprint="aaa",
        observed_fingerprint="bbb",
        desired_fingerprint="ccc",
        security_topology=False,
        choices=("apply-desired", "keep-current"),
        resolution_id=rid,
    )


def _pending(rid: str = "r1", tx: str = "tx-001") -> PendingResolution:
    return PendingResolution(
        resolution_id=rid,
        conflict=_conflict(rid),
        transaction_id=tx,
        created_at="2026-06-21T00:00:00+00:00",
    )


# ── ControlStore.open / context manager ──────────────────────────────────────

def test_open_creates_state_dir(tmp_path):
    t = _target(tmp_path)
    assert not t.state_dir.exists()
    with ControlStore.open(t):
        assert t.state_dir.exists()


def test_lock_file_written_on_open(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        assert store._lock_path.exists()
        data = json.loads(store._lock_path.read_bytes())
        assert data["pid"] == os.getpid()


def test_lock_file_removed_on_close(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        lock_path = store._lock_path
    assert not lock_path.exists()


def test_second_open_raises_lock_held(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t):
        with pytest.raises(LockHeld):
            ControlStore.open(t)


def test_stale_lock_by_age_overwritten(tmp_path):
    t = _target(tmp_path)
    lock_path = t.state_dir / "oramaclaw.lock"
    t.state_dir.mkdir(parents=True, exist_ok=True)
    # Write a lock from a dead PID with ancient timestamp.
    stale_data = {"pid": 999999, "acquired_at": time.time() - LOCK_STALE_SECONDS - 10}
    lock_path.write_text(json.dumps(stale_data))
    # Should succeed without raising.
    with ControlStore.open(t) as store:
        data = json.loads(store._lock_path.read_bytes())
    assert data["pid"] == os.getpid()


def test_stale_lock_dead_pid_overwritten(tmp_path):
    t = _target(tmp_path)
    lock_path = t.state_dir / "oramaclaw.lock"
    t.state_dir.mkdir(parents=True, exist_ok=True)
    # Recent timestamp but PID 1 definitely not our process + no create_time match.
    stale_data = {"pid": 999999999, "acquired_at": time.time(), "create_time": 0.0}
    lock_path.write_text(json.dumps(stale_data))
    with ControlStore.open(t):
        pass


# ── Registry ──────────────────────────────────────────────────────────────────

def test_clear_pending_for_transaction(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.add_pending(_pending("r1", "tx-a"))
        store.add_pending(_pending("r2", "tx-b"))
        store.clear_pending_for_transaction("tx-a")
        remaining = {r["resolution_id"] for r in store.load_pending()}
    assert remaining == {"r2"}
    archive_dir = t.state_dir / "registry" / "orphan-conflicts"
    assert archive_dir.is_dir()
    archives = list(archive_dir.glob("orphan-*.json"))
    assert archives, "cleared pending should be archived"
    payload = json.loads(archives[0].read_text(encoding="utf-8"))
    assert payload["records"][0]["resolution_id"] == "r1"


def test_record_ownership(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.record_ownership("mgr", "provider:x", "/effort", "high")
        entry = store.get_ownership("provider:x", "/effort")
    assert entry is not None
    assert entry["manager"] == "mgr"
    assert entry["managed_path"] == "/effort"
    assert entry["fingerprint"] == _fingerprint("high")


def test_sweep_orphan_pending_archives_failed_transaction(tmp_path):
    t = _target(tmp_path)
    t.state_dir.mkdir(parents=True, exist_ok=True)
    pending_path = t.state_dir / "pending-resolutions.json"
    journal_path = t.state_dir / "journal.json"
    pending_path.write_text(
        json.dumps(
            [
                {
                    "resolution_id": "r-orphan",
                    "transaction_id": "tx-failed",
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "resolved_at": None,
                    "chosen": None,
                    "conflict": {"managed_path": "/effort"},
                }
            ]
        ),
        encoding="utf-8",
    )
    journal_path.write_text(
        json.dumps(
            [
                {
                    "transaction_id": "tx-failed",
                    "state": "failed",
                    "resources": [],
                    "auto_woven": [],
                    "conflicts": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    with ControlStore.open(t) as store:
        assert store.load_pending() == []
    archive_dir = t.state_dir / "registry" / "orphan-conflicts"
    assert list(archive_dir.glob("orphan-*.json"))


def test_record_ownership_overwrites(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.record_ownership("mgr-a", "provider:x", "/effort", "low")
        store.record_ownership("mgr-b", "provider:x", "/effort", "high")
        entry = store.get_ownership("provider:x", "/effort")
    assert entry["manager"] == "mgr-b"
    assert entry["fingerprint"] == _fingerprint("high")


def test_field_fingerprint_unknown_returns_none(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        assert store.field_fingerprint("provider:x", "/missing") is None


def test_registry_persists_across_store_instances(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.record_ownership("mgr", "provider:x", "/effort", "medium")
    with ControlStore.open(t) as store2:
        entry = store2.get_ownership("provider:x", "/effort")
    assert entry["fingerprint"] == _fingerprint("medium")


# ── Journal ───────────────────────────────────────────────────────────────────

def test_append_journal_and_last(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.append_journal("tx-001", "committed", ["provider:x"], [], [])
        last = store.last_transaction()
    assert last["transaction_id"] == "tx-001"
    assert last["state"] == "committed"


def test_journal_cap_enforced(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        for i in range(JOURNAL_CAP + 20):
            store.append_journal(f"tx-{i:04d}", "committed", [], [], [])
        journal = store.load_journal()
    assert len(journal) == JOURNAL_CAP
    assert journal[-1]["transaction_id"] == f"tx-{JOURNAL_CAP + 19:04d}"
    assert journal[0]["transaction_id"] == f"tx-0020"


def test_last_transaction_none_when_empty(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        assert store.last_transaction() is None


# ── Pending resolutions ────────────────────────────────────────────────────────

def test_add_pending_and_retrieve(tmp_path):
    t = _target(tmp_path)
    p = _pending("r1")
    with ControlStore.open(t) as store:
        store.add_pending(p)
        records = store.load_pending()
    assert len(records) == 1
    assert records[0]["resolution_id"] == "r1"
    assert records[0]["conflict"]["managed_path"] == "/effort"


def test_add_pending_idempotent_by_id(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.add_pending(_pending("r1", "tx-001"))
        store.add_pending(_pending("r1", "tx-002"))  # same ID, different tx
        records = store.load_pending()
    assert len(records) == 1
    assert records[0]["transaction_id"] == "tx-002"  # replaced


def test_resolve_pending_marks_resolved(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.add_pending(_pending("r1"))
        found = store.resolve_pending("r1", "apply-desired", "2026-06-21T01:00:00+00:00")
        assert found is True
        record = store.pending_by_id("r1")
    assert record["chosen"] == "apply-desired"
    assert record["resolved_at"] == "2026-06-21T01:00:00+00:00"


def test_resolve_pending_unknown_returns_false(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        result = store.resolve_pending("does-not-exist", "apply-desired")
    assert result is False


def test_open_conflicts_excludes_resolved(tmp_path):
    t = _target(tmp_path)
    with ControlStore.open(t) as store:
        store.add_pending(_pending("r1"))
        store.add_pending(_pending("r2"))
        store.resolve_pending("r1", "keep-current")
        open_c = store.open_conflicts()
    assert len(open_c) == 1
    assert open_c[0]["resolution_id"] == "r2"


# ── TOCTOU lock regression tests ──────────────────────────────────────────────

def test_acquire_lock_atomic_first_attempt(tmp_path):
    """Happy path: lock acquired on first O_CREAT|O_EXCL attempt."""
    import os, time
    from oramaclaw.store import _acquire_lock, _release_lock
    lock_path = tmp_path / "test.lock"
    _acquire_lock(lock_path)
    assert lock_path.exists()
    _release_lock(lock_path)
    assert not lock_path.exists()


def test_acquire_lock_stale_overwrite_then_reacquire(tmp_path):
    """Stale lock (dead PID) is overwritten and our PID wins on retry."""
    import json
    from oramaclaw.store import _acquire_lock, _release_lock, LockHeld
    lock_path = tmp_path / "test.lock"
    # Write a stale lock: PID 999999 (almost certainly dead), very old timestamp
    stale = {"pid": 999999, "acquired_at": 0.0, "create_time": None}
    lock_path.write_text(json.dumps(stale))
    # Should overwrite stale lock without raising
    _acquire_lock(lock_path)
    data = json.loads(lock_path.read_text())
    assert data["pid"] != 999999, "stale PID should be replaced by our PID"
    _release_lock(lock_path)


def test_acquire_lock_live_pid_raises_lock_held(tmp_path):
    """Live lock (our own PID) raises LockHeld — not silently overwritten."""
    import json, os
    from oramaclaw.store import _acquire_lock, LockHeld
    import pytest, time
    lock_path = tmp_path / "test.lock"
    # Write a lock with our own PID (definitely alive)
    live = {"pid": os.getpid(), "acquired_at": time.time(), "create_time": None}
    lock_path.write_text(json.dumps(live))
    with pytest.raises(LockHeld):
        _acquire_lock(lock_path)
