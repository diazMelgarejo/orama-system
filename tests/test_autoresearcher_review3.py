#!/usr/bin/env python3
"""Tests for the CodeRabbit findings on orama PR 487 (2026-11-10).

The lock must fail closed on every path: an inspect error means busy, and a recheck or acquire error never leaves the OS
lock held or lets a request go out.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_HERE = Path(__file__).resolve().parent
for _p in (str(_HERE.parent / "scripts"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402
from _cline_fakes import isolated_cline_workdir  # noqa: E402,F401  (autouse fixture)

_GW_DOWN = {"should_fallback": True, "reason": "gw down"}


@pytest.fixture()
def wired(tmp_path, monkeypatch):
    """Point both backend locks at a temporary path."""
    path = tmp_path / "autoresearcher_backend.lock"
    monkeypatch.setattr(car, "BACKEND_LOCK_WIN", path)
    monkeypatch.setattr(car, "BACKEND_LOCK_MAC", path)
    monkeypatch.setattr(car, "WIN_PULSE_LOCK", tmp_path / "absent-win.lock")
    monkeypatch.setattr(car, "MAC_PULSE_LOCK", tmp_path / "absent-mac.lock")
    return path


@pytest.mark.parametrize("plat", ["windows", "macos"])
def test_an_inspect_error_means_busy_not_an_exception(wired, plat):
    """A broken lock check (another account owns the file, a sharing violation) must read as busy, never raise or idle."""
    with patch.object(car, "_probe_http_ok", return_value=True), \
         patch.object(arl, "inspect", side_effect=PermissionError("owned by another account")):
        result = car.local_backend_idle(plat)
    assert result["idle"] is False and "backend lock check failed" in result["reason"]


def test_a_recheck_error_releases_the_lock_as_not_sent(wired):
    """If the effect-boundary recheck raises something other than LockRefused nothing was sent and the lock is freed."""
    with patch.object(car, "should_fallback_to_cline", return_value=_GW_DOWN), \
         patch.object(car, "_effect_boundary_ok", side_effect=RuntimeError("gateway probe blew up")), \
         patch.object(car, "dispatch_cline") as send:
        result = car.dispatch_autoresearcher("windows", "task")
    assert send.call_count == 0 and result["ok"] is False and result["outcome"] == "not-sent"
    assert arl.inspect(wired).state == arl.FREE


def test_an_unexpected_acquire_error_refuses_without_sending(wired):
    """An OSError from the lock layer is a refusal, not a crash and not a send."""
    with patch.object(car, "should_fallback_to_cline", return_value=_GW_DOWN), \
         patch.object(arl.BackendLock, "acquire", side_effect=OSError("sharing violation")), \
         patch.object(car, "dispatch_cline") as send:
        result = car.dispatch_autoresearcher("windows", "task")
    assert send.call_count == 0 and result["ok"] is False and result["lock_state"] == "refused"


def test_the_scratch_workdir_is_isolated_per_test(tmp_path):
    """The autouse fixture points CLINE_WORKDIR at a temporary directory so tests never touch the real home."""
    import os

    assert os.environ["CLINE_WORKDIR"].startswith(str(tmp_path))
