#!/usr/bin/env python3
"""Tests for the AutoResearcher single-owner backend lock (AR-WIN-1 W2-backend-lock design).

The matrix IDs (W2L-nn) come from the Windows design draft. Every rule below is stated in the design:
an OS-held lock is the authority, age and PID absence are never proof, ambiguity refuses, and an
unknown outcome is held for reconciliation instead of being retried.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402
from _cline_fakes import FakeProc as _FakeProc  # noqa: E402
from _cline_fakes import isolated_cline_workdir  # noqa: E402,F401  (autouse fixture)

_HOLDER = """
import sys, time
sys.path.insert(0, {scripts!r})
import autoresearcher_lock as arl
lock = arl.BackendLock({path!r}).acquire()
if {inflight!r}:
    lock.mark_inflight()
print("READY", flush=True)
time.sleep(120)
"""


_RACER = """
import sys, time
sys.path.insert(0, {scripts!r})
import autoresearcher_lock as arl
try:
    lock = arl.BackendLock({path!r}).acquire()
except arl.LockRefused:
    print("REFUSED", flush=True)
    raise SystemExit(3)
print("READY", flush=True)
time.sleep(60)
"""


def _spawn_holder(path: Path, inflight: bool = False) -> subprocess.Popen:
    """Start a child process that acquires the lock at *path* and then sleeps; return it once READY."""
    code = _HOLDER.format(scripts=str(_SCRIPTS_DIR), path=str(path), inflight=inflight)
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    assert line == "READY", f"holder did not start: {line!r}"
    return proc


def _stop(proc: subprocess.Popen) -> None:
    """Kill a holder child hard (no graceful release) and reap it."""
    proc.kill()
    proc.wait(timeout=10)


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    """A fresh lock path inside a per-test temporary directory."""
    return tmp_path / "autoresearcher_backend.lock"


# ── State model: free, held, held-stale-unproven, ambiguous ──────────────────────────────────────

class TestStateModel:
    """The four states and what each one admits."""

    def test_missing_file_is_free(self, lock_path):
        """A path that was never used is free (guard: matches the old 'missing is not held')."""
        assert arl.inspect(lock_path).state == arl.FREE

    def test_clean_acquire_release_leaves_a_free_file_that_is_not_deleted(self, lock_path):
        """Release writes a released record and keeps the file; the next inspection is free."""
        lock = arl.BackendLock(lock_path).acquire()
        lock.release("completed")
        assert lock_path.exists()
        assert arl.inspect(lock_path).state == arl.FREE

    def test_live_owner_is_held_whatever_the_file_age(self, lock_path):
        """W2L-01: a live owner stays held even when the file is very old (age is not proof)."""
        holder = _spawn_holder(lock_path)
        try:
            old = time.time() - 30 * 24 * 3600
            os.utime(lock_path, (old, old))
            assert arl.inspect(lock_path).state == arl.HELD
        finally:
            _stop(holder)

    def test_env_max_age_zero_does_not_release_a_live_owner(self, lock_path, monkeypatch):
        """W2L-06: the old age override can no longer free a lock held by a live owner."""
        monkeypatch.setenv("AUTORESEARCHER_LOCK_MAX_AGE_SECONDS", "0")
        holder = _spawn_holder(lock_path)
        try:
            assert arl.inspect(lock_path).state == arl.HELD
        finally:
            _stop(holder)

    def test_dead_owner_without_clean_release_is_held_stale_unproven(self, lock_path):
        """W2L-02: the owner died after acquiring and never released; refuse until reconciled."""
        holder = _spawn_holder(lock_path)
        _stop(holder)
        result = arl.inspect(lock_path)
        assert result.state == arl.STALE
        with pytest.raises(arl.LockRefused) as exc:
            arl.BackendLock(lock_path).acquire()
        assert exc.value.state == arl.STALE

    def test_owner_killed_with_an_in_flight_marker_is_ambiguous(self, lock_path):
        """W2L-09: a request may have been sent; the next acquirer must refuse as ambiguous."""
        holder = _spawn_holder(lock_path, inflight=True)
        _stop(holder)
        assert arl.inspect(lock_path).state == arl.AMBIGUOUS
        with pytest.raises(arl.LockRefused) as exc:
            arl.BackendLock(lock_path).acquire()
        assert exc.value.state == arl.AMBIGUOUS

    @pytest.mark.parametrize("junk", ['{"schema": 1, "pid": 12', "not json at all", "\x00\x00\x00", "[]"])
    def test_torn_or_unparseable_record_is_ambiguous(self, lock_path, junk):
        """W2L-07: a torn record is never parsed into a PID and probed; it is ambiguous."""
        lock_path.write_text(junk, encoding="utf-8")
        assert arl.inspect(lock_path).state == arl.AMBIGUOUS

    def test_reused_pid_is_diagnosed_not_trusted(self, lock_path):
        """W2L-03: a record naming a live PID with a different start identity is not owner proof."""
        record = {
            "schema": 1, "state": "acquired", "nonce": "x", "pid": os.getpid(),
            "start_id": "definitely-not-this-process", "resource": "local-backend", "ts": time.time(),
        }
        lock_path.write_text(json.dumps(record), encoding="utf-8")
        result = arl.inspect(lock_path)
        assert result.state == arl.STALE
        assert result.owner is not None and result.owner.get("identity") == "mismatch"

    def test_in_flight_record_without_a_live_lock_is_ambiguous_even_with_live_pid(self, lock_path):
        """An in-flight marker left behind is ambiguous regardless of the recorded PID."""
        record = {
            "schema": 1, "state": "inflight", "nonce": "x", "pid": os.getpid(),
            "start_id": arl.process_start_id(os.getpid()), "resource": "local-backend", "ts": time.time(),
        }
        lock_path.write_text(json.dumps(record), encoding="utf-8")
        assert arl.inspect(lock_path).state == arl.AMBIGUOUS


# ── Acquisition ──────────────────────────────────────────────────────────────────────────────────

class TestAcquisition:
    """Exactly one acquirer wins and the winner can prove it still owns the lock."""

    def test_second_acquirer_in_another_process_is_refused_as_held(self, lock_path):
        """W2L-08: while one owner holds the lock a second acquirer is refused immediately."""
        holder = _spawn_holder(lock_path)
        try:
            with pytest.raises(arl.LockRefused) as exc:
                arl.BackendLock(lock_path).acquire()
            assert exc.value.state == arl.HELD
        finally:
            _stop(holder)

    def test_two_simultaneous_acquirers_yield_exactly_one_winner(self, lock_path):
        """W2L-08: two processes racing for a free lock produce exactly one READY."""
        code = _RACER.format(scripts=str(_SCRIPTS_DIR), path=str(lock_path))
        procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            lines = sorted(p.stdout.readline().strip() for p in procs)
            assert lines == ["READY", "REFUSED"]
        finally:
            for p in procs:
                p.kill()
                p.wait(timeout=10)

    def test_record_carries_identity_and_nonce(self, lock_path):
        """The owner record binds PID, process start identity, resource and a nonce."""
        lock = arl.BackendLock(lock_path, resource="win-lmstudio").acquire()
        try:
            owner = arl.inspect(lock_path).owner
            assert owner is not None
            assert owner["pid"] == os.getpid()
            assert owner["resource"] == "win-lmstudio"
            assert owner["nonce"] and owner["start_id"] == arl.process_start_id(os.getpid())
        finally:
            lock.release("completed")

    def test_recheck_passes_while_owned_and_refuses_when_the_extra_check_fails(self, lock_path):
        """The effect-boundary recheck re-reads caller inputs instead of trusting the earlier check."""
        lock = arl.BackendLock(lock_path).acquire()
        try:
            lock.recheck(lambda: (True, "ok"))
            with pytest.raises(arl.LockRefused) as exc:
                lock.recheck(lambda: (False, "gateway recovered"))
            assert "gateway recovered" in exc.value.reason
        finally:
            lock.release("not-sent")

    def test_recheck_detects_a_replaced_record(self, lock_path):
        """If the record nonce is no longer ours the recheck refuses (stat-then-read style race)."""
        lock = arl.BackendLock(lock_path).acquire()
        try:
            record = json.loads(lock_path.read_text(encoding="utf-8"))
            record["nonce"] = "someone-else"
            lock_path.write_text(json.dumps(record), encoding="utf-8")
            with pytest.raises(arl.LockRefused):
                lock.recheck()
        finally:
            lock.release("not-sent")

    def test_release_unknown_keeps_the_marker_for_reconciliation(self, lock_path):
        """W2L-11/12: an unknown outcome releases the OS lock but leaves an ambiguous in-flight record."""
        lock = arl.BackendLock(lock_path).acquire()
        lock.mark_inflight()
        lock.release("unknown")
        assert arl.inspect(lock_path).state == arl.AMBIGUOUS

    def test_reconcile_requires_an_operator_and_records_the_action(self, lock_path):
        """Clearing an ambiguous record is an explicit operator action that is written into the record."""
        lock = arl.BackendLock(lock_path).acquire()
        lock.mark_inflight()
        lock.release("unknown")
        with pytest.raises(ValueError):
            arl.reconcile(lock_path, operator="", note="no operator")
        arl.reconcile(lock_path, operator="operator-1", note="verified backend idle by hand")
        assert arl.inspect(lock_path).state == arl.FREE
        assert "operator-1" in lock_path.read_text(encoding="utf-8")

    def test_reconcile_refuses_while_the_lock_is_held(self, lock_path):
        """An operator cannot clear a record under a live owner."""
        holder = _spawn_holder(lock_path)
        try:
            with pytest.raises(arl.LockRefused):
                arl.reconcile(lock_path, operator="operator-1", note="should not work")
        finally:
            _stop(holder)


@pytest.mark.skipif(sys.platform != "win32", reason="STILL_ACTIVE (259) is a Windows exit-code artefact")
def test_process_that_exits_with_code_259_is_not_alive():
    """W2L-05: an exited process whose exit code is 259 must not look alive."""
    proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(259)"])
    proc.wait(timeout=30)
    assert arl.process_start_id(proc.pid) is None


def test_process_start_id_is_stable_for_a_live_process():
    """The start identity of this process is non-empty and does not change between calls."""
    first = arl.process_start_id(os.getpid())
    assert first and first == arl.process_start_id(os.getpid())


# ── Dispatch integration: no probe-then-act, no retry after an unknown outcome ───────────────────

@pytest.fixture()
def wired(tmp_path, monkeypatch):
    """Point the dispatcher's backend lock at a temporary path and stub the fallback decision."""
    path = tmp_path / "autoresearcher_backend.lock"
    monkeypatch.setattr(car, "BACKEND_LOCK_WIN", path)
    monkeypatch.setattr(car, "BACKEND_LOCK_MAC", path)
    return path


class TestDispatchIntegration:
    """dispatch_autoresearcher takes the lock, rechecks at the effect boundary and never retries."""

    def test_success_releases_the_lock(self, wired):
        """A completed dispatch leaves the lock free."""
        with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(car, "dispatch_cline", return_value={"ok": True, "output": "done", "elapsed": 1.0}) as send:
            result = car.dispatch_autoresearcher("windows", "task")
        assert result["ok"] is True and send.call_count == 1
        assert arl.inspect(wired).state == arl.FREE

    def test_probe_then_act_race_refuses_at_the_recheck(self, wired):
        """W2L-10: the gateway recovers between the decision and the send; nothing is sent."""
        with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
             patch.object(car, "_effect_boundary_ok", return_value=(False, "gateway recovered")), \
             patch.object(car, "dispatch_cline") as send:
            result = car.dispatch_autoresearcher("windows", "task")
        assert result["ok"] is False and send.call_count == 0
        assert "gateway recovered" in result["output"]
        assert arl.inspect(wired).state == arl.FREE

    def test_timeout_is_unknown_and_is_not_retried(self, wired):
        """W2L-11: a timeout after the request was written is unknown: one send, ambiguous record."""
        unknown = {"ok": False, "output": "cline task timed out", "elapsed": 300.0, "outcome": "unknown"}
        with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(car, "dispatch_cline", return_value=unknown) as send:
            result = car.dispatch_autoresearcher("windows", "task")
        assert send.call_count == 1
        assert result["ok"] is False and result["outcome"] == "unknown"
        assert arl.inspect(wired).state == arl.AMBIGUOUS

    def test_nonzero_exit_after_send_is_not_retried(self, wired):
        """W2L-12: a nonzero exit after the request was sent is unknown and never auto-retried."""
        failed = {"ok": False, "output": "exit 1", "elapsed": 2.0, "outcome": "unknown"}
        with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(car, "dispatch_cline", return_value=failed) as send:
            car.dispatch_autoresearcher("macos", "task")
        assert send.call_count == 1

    def test_proven_not_sent_failure_frees_the_lock(self, wired):
        """A failure with evidence that nothing left the process (cline missing) is recorded as not sent."""
        not_sent = {"ok": False, "output": "cline unavailable", "elapsed": 0, "outcome": "not-sent"}
        with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(car, "dispatch_cline", return_value=not_sent) as send:
            result = car.dispatch_autoresearcher("windows", "task")
        assert send.call_count == 1 and result["ok"] is False
        assert arl.inspect(wired).state == arl.FREE

    def test_a_held_lock_refuses_dispatch_without_sending(self, wired):
        """When another owner holds the backend lock the dispatch is refused with the state named."""
        holder = _spawn_holder(wired)
        try:
            with patch.object(car, "should_fallback_to_cline", return_value={"should_fallback": True, "reason": "gw down"}), \
                 patch.object(car, "dispatch_cline") as send:
                result = car.dispatch_autoresearcher("windows", "task")
            assert send.call_count == 0 and result["ok"] is False
            assert result["lock_state"] == arl.HELD
        finally:
            _stop(holder)

    def test_idle_gate_reports_busy_for_every_non_free_lock_state(self, wired):
        """local_backend_idle must not call the backend idle while the backend lock is not free."""
        holder = _spawn_holder(wired, inflight=True)
        _stop(holder)
        with patch.object(car, "_probe_http_ok", return_value=True), \
             patch.object(car, "WIN_PULSE_LOCK", wired.parent / "absent.lock"):
            assert car.local_backend_idle("windows")["idle"] is False

    def test_dispatch_cline_marks_a_missing_cli_as_not_sent_and_a_timeout_as_unknown(self):
        """dispatch_cline classifies outcomes: missing CLI is not-sent, a timeout is unknown."""
        with patch.object(car, "cline_available", return_value={"available": False, "reason": "missing"}):
            assert car.dispatch_cline("t")["outcome"] == "not-sent"
        with patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", return_value=_FakeProc(0, "", "", comm_exc=subprocess.TimeoutExpired("cline", 300))):
            assert car.dispatch_cline("t")["outcome"] == "unknown"
        with patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", side_effect=FileNotFoundError("cline")):
            assert car.dispatch_cline("t")["outcome"] == "not-sent"
