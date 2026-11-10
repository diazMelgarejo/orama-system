#!/usr/bin/env python3
"""Regression tests for the Mac review of the AR-WIN-1 backend-lock branch (2026-11-10).

Covers the failed-acquire lock leak, exception paths in the dispatcher, the positional Cline command line,
conservative outcome classification, a configured Cline path, and an honest identity label.
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
from _cline_fakes import FakeProc  # noqa: E402
from _cline_fakes import isolated_cline_workdir  # noqa: E402,F401  (autouse fixture)

_GW_DOWN = {"should_fallback": True, "reason": "gw down"}


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    """A fresh lock path inside a per-test temporary directory."""
    return tmp_path / "autoresearcher_backend.lock"


@pytest.fixture()
def wired(lock_path, monkeypatch):
    """Point the dispatcher's backend locks at the temporary path."""
    monkeypatch.setattr(car, "BACKEND_LOCK_WIN", lock_path)
    monkeypatch.setattr(car, "BACKEND_LOCK_MAC", lock_path)
    return lock_path


class TestLockLeaks:
    """Finding 1: no failure path may leave the OS lock held or free an unknown outcome."""

    def test_failed_acquire_write_does_not_leak_the_lock(self, lock_path):
        """If the first record write raises, the OS lock and descriptor are released again."""
        with patch.object(arl, "_write_record", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                arl.BackendLock(lock_path).acquire()
        assert arl.inspect(lock_path).state != arl.HELD
        arl.BackendLock(lock_path).acquire().release("not-sent")

    @pytest.mark.parametrize("stage", ["lock_error", "contended", "read_error", "classify_error", "write_error"])
    def test_acquire_failure_closes_descriptor_once(self, lock_path: Path, stage: str) -> None:
        """Failed acquisition closes once, unlocking only when an OS lock was acquired."""
        lock = arl.BackendLock(lock_path)
        real_close = os.close
        closed = []

        def close_once(fd: int) -> None:
            """Record and close the descriptor."""
            closed.append(fd)
            real_close(fd)

        with patch.object(arl.os, "close", side_effect=close_once), \
             patch.object(arl, "_unlock", wraps=arl._unlock) as unlock, \
             patch.object(arl, "_try_lock", wraps=arl._try_lock) as try_lock, \
             patch.object(arl, "_read_record", wraps=arl._read_record) as read, \
             patch.object(arl, "_classify", wraps=arl._classify) as classify, \
             patch.object(lock, "_write", wraps=lock._write) as write:
            if stage == "lock_error":
                try_lock.side_effect = arl.LockRefused("refused", "permission denied")
            elif stage == "contended":
                try_lock.return_value = False
            elif stage == "read_error":
                read.side_effect = OSError("read failed")
            elif stage == "classify_error":
                classify.side_effect = ValueError("classification failed")
            else:
                write.side_effect = OSError("write failed")
            with pytest.raises((arl.LockRefused, OSError, ValueError)):
                lock.acquire()
            assert len(closed) == 1
            assert unlock.call_count == (0 if stage in ("lock_error", "contended") else 1)
        assert lock._fd is None

    def test_mark_inflight_failure_is_not_sent_and_frees_the_lock(self, wired):
        """Nothing was sent if the in-flight marker cannot be written; the lock is freed."""
        with patch.object(car, "should_fallback_to_cline", return_value=_GW_DOWN), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(arl.BackendLock, "mark_inflight", side_effect=OSError("disk full")), \
             patch.object(car, "dispatch_cline") as send:
            result = car.dispatch_autoresearcher("windows", "task")
        assert send.call_count == 0 and result["ok"] is False and result["outcome"] == "not-sent"
        assert arl.inspect(wired).state == arl.FREE

    def test_exception_while_sending_is_unknown_and_never_frees_the_lock(self, wired):
        """An exception after the marker was written is unknown, not free."""
        with patch.object(car, "should_fallback_to_cline", return_value=_GW_DOWN), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(car, "dispatch_cline", side_effect=RuntimeError("boom")):
            result = car.dispatch_autoresearcher("windows", "task")
        assert result["ok"] is False and result["outcome"] == "unknown"
        assert arl.inspect(wired).state == arl.AMBIGUOUS

    def test_fast_usage_error_after_effect_keeps_durable_ambiguous(
        self, wired: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A child may have acted before emitting a short usage error and exiting."""
        monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path / "scratch"))
        effects = []

        class EffectProcess(FakeProc):
            """Simulate an external effect before a fast error response."""

            def communicate(self, timeout: float | None = None) -> tuple[str, str]:
                """Record the effect and return the scripted response."""
                effects.append("sent")
                return super().communicate(timeout=timeout)

        process = EffectProcess(1, "", "Unknown command or unquoted prompt\n")
        with patch.object(car, "should_fallback_to_cline", return_value=_GW_DOWN), \
             patch.object(car, "_effect_boundary_ok", return_value=(True, "ok")), \
             patch.object(arl, "process_start_id", return_value="test-start"), \
             patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", return_value=process) as popen:
            result = car.dispatch_autoresearcher("windows", "two word prompt")
        assert effects == ["sent"] and popen.call_count == 1
        assert result["outcome"] == "unknown"
        assert arl.inspect(wired).state == arl.AMBIGUOUS


class TestClineCommandLine:
    """The Cline call is positional, configurable, runs in a scratch directory and classifies usage errors."""

    def test_prompt_is_positional_not_a_task_subcommand(self, monkeypatch):
        """The prompt is a bare positional argument, never ``task``."""
        monkeypatch.delenv("CLINE_PROVIDER", raising=False)
        monkeypatch.delenv("CLINE_MODEL", raising=False)
        argv = car._cline_argv("cline", "summarise the lock design for review")
        assert argv == ["cline", "--plan", "--auto-approve", "false", "summarise the lock design for review"]

    def test_one_word_prompt_is_padded_so_it_is_not_read_as_a_subcommand(self, monkeypatch):
        """A one-word prompt would be rejected as a mistyped subcommand, so it is made multi-word."""
        monkeypatch.delenv("CLINE_PROVIDER", raising=False)
        monkeypatch.delenv("CLINE_MODEL", raising=False)
        assert len(car._cline_argv("cline", "status")[-1].split()) >= 2

    def test_provider_and_model_are_pinned_only_when_configured(self, monkeypatch):
        """CLINE_PROVIDER and CLINE_MODEL pin the route with -P and -m; otherwise Cline's defaults apply."""
        monkeypatch.setenv("CLINE_PROVIDER", "cline-pass")
        monkeypatch.setenv("CLINE_MODEL", "some-model")
        argv = car._cline_argv("cline", "a two word prompt")
        assert argv[:5] == ["cline", "-P", "cline-pass", "-m", "some-model"]
        assert argv[-1] == "a two word prompt"
        assert argv[5:8] == ["--plan", "--auto-approve", "false"]

    def test_dispatch_cline_uses_the_positional_form_and_a_scratch_directory(self, tmp_path, monkeypatch):
        """The subprocess gets no ``task`` argument and does not run in the repository root."""
        monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path / "scratch"))
        with patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", return_value=FakeProc(0, "ok", "")) as popen:
            car.dispatch_cline("two word prompt")
        argv, kwargs = popen.call_args.args[0], popen.call_args.kwargs
        assert argv[1:2] != ["task"]
        assert kwargs["cwd"] == str(tmp_path / "scratch")
        assert Path(kwargs["cwd"]).is_dir() and Path(kwargs["cwd"]) != car.REPO_ROOT

    @pytest.mark.parametrize(
        "text", ["Unknown command or unquoted prompt: task x", "Unknown or disabled provider 'clinepass'"]
    )
    def test_usage_error_text_does_not_prove_not_sent(self, text: str) -> None:
        """Usage-like text does not prove that the launched child sent nothing."""
        bad = FakeProc(1, "", text)
        with patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", return_value=bad):
            assert car.dispatch_cline("two word prompt")["outcome"] == "unknown"

    def test_any_other_nonzero_exit_stays_unknown(self):
        """A failure that is not a recognised pre-request error keeps the conservative unknown outcome."""
        bad = FakeProc(1, "", "the model stopped halfway")
        with patch.object(car, "cline_available", return_value={"available": True, "bin": "cline"}), \
             patch.object(car.subprocess, "Popen", return_value=bad):
            assert car.dispatch_cline("two word prompt")["outcome"] == "unknown"

    def test_cline_bin_environment_variable_is_honoured(self, tmp_path, monkeypatch):
        """A configured CLINE_BIN is used when it points at a real file (Node-manager installs)."""
        fake = tmp_path / "cline-custom"
        fake.write_text("#!/bin/sh\n", encoding="utf-8")
        monkeypatch.setenv("CLINE_BIN", str(fake))
        assert car._find_cline() == str(fake)


class TestIdentityLabel:
    """Finding 3: a failed identity probe must not read as proof of death."""

    def test_identity_is_labelled_unverified_when_the_probe_fails(self, lock_path):
        """When process_start_id cannot answer, the owner identity is ``unverified``."""
        record = {"schema": 1, "state": "acquired", "nonce": "x", "pid": os.getpid(), "start_id": "x",
                  "resource": "local-backend", "ts": time.time()}
        lock_path.write_text(json.dumps(record), encoding="utf-8")
        with patch.object(arl, "process_start_id", return_value=None):
            assert arl.inspect(lock_path).owner["identity"] == "unverified"
