#!/usr/bin/env python3
"""Tests for the CodeRabbit findings on orama PR 488 (commit 4899d17c) that touch the controller.

A prompt that starts with a hyphen is padded; an unresolved shim is refused, never run with the prompt;
KeyboardInterrupt and SystemExit are not swallowed; a release error is reported, not lost or raised.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_HERE = Path(__file__).resolve().parent
for p in (str(_HERE.parent / "scripts"), str(_HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402
from _cline_fakes import FakeProc  # noqa: E402
from _cline_fakes import isolated_cline_workdir  # noqa: E402,F401  (autouse fixture)

_AVAILABLE = {"available": True, "bin": "cline"}


class TestPromptPadding:
    """A task that would read as an option or as a lone command word gets the Task: prefix."""

    @pytest.mark.parametrize("task", ["-v check the logs", "  --help please", "single", "-"])
    def test_option_like_or_single_word_prompts_are_padded(self, task: str) -> None:
        """The last argument starts with the prefix, so Cline's parser cannot read it as an option or subcommand."""
        argv = car._cline_argv("cline", task)
        assert argv[-1].startswith("Task: ")

    def test_normal_multiword_prompt_is_unchanged(self) -> None:
        """A plain multi-word prompt is passed through as written."""
        assert car._cline_argv("cline", "review the lock module")[-1] == "review the lock module"


class TestUnresolvedShim:
    """The shim itself is never the launcher for a prompt."""

    def test_unresolved_shim_raises_instead_of_falling_back(self, tmp_path: Path) -> None:
        """A cmd shim with no node entry beside it cannot carry a prompt: building the command line refuses."""
        shim = tmp_path / "cline.cmd"
        shim.write_text("@echo off\r\n", encoding="ascii")
        with pytest.raises(RuntimeError, match="refusing to pass a prompt through a shell shim"):
            car._cline_argv(str(shim), "review & echo the logs")

    def test_dispatch_classifies_the_refusal_as_not_sent(self, tmp_path: Path) -> None:
        """dispatch_cline turns the refusal into not-sent and never starts a process."""
        shim = tmp_path / "cline.cmd"
        shim.write_text("@echo off\r\n", encoding="ascii")
        with patch.object(car, "cline_available", return_value={"available": True, "bin": str(shim)}), \
             patch.object(car.subprocess, "Popen") as popen:
            res = car.dispatch_cline("review & echo the logs")
        assert res["outcome"] == "not-sent" and res["ok"] is False
        popen.assert_not_called()


class TestInterruptsPropagate:
    """Operator interrupts stop the process; the child is still reaped."""

    @pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit])
    def test_interrupt_is_reraised_and_child_killed(self, exc: type) -> None:
        """The wait is interrupted: the child is killed and the interrupt propagates (record stays in flight)."""
        proc = FakeProc(0, "", "", comm_exc=exc())
        with patch.object(car, "cline_available", return_value=_AVAILABLE), \
             patch.object(car.subprocess, "Popen", return_value=proc), pytest.raises(exc):
            car.dispatch_cline("two word prompt")
        assert proc.killed is True

    def test_ordinary_error_after_start_is_still_unknown(self) -> None:
        """An ordinary I/O error after start stays an unknown outcome and the child is reaped."""
        proc = FakeProc(0, "", "", comm_exc=OSError("broken pipe"))
        with patch.object(car, "cline_available", return_value=_AVAILABLE), \
             patch.object(car.subprocess, "Popen", return_value=proc):
            res = car.dispatch_cline("two word prompt")
        assert res["outcome"] == "unknown" and proc.killed is True


class TestReleaseErrorIsReported:
    """A failing release keeps the dispatch result and says so in the returned dict."""

    @pytest.fixture()
    def wired(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Point the lock at a scratch file and stub the decision, recheck and send."""
        lockfile = tmp_path / "backend.lock"
        monkeypatch.setattr(car, "BACKEND_LOCK_WIN", lockfile)
        monkeypatch.setattr(car, "BACKEND_LOCK_MAC", lockfile)
        monkeypatch.setattr(car, "should_fallback_to_cline", lambda plat: {"should_fallback": True, "reason": "test"})
        monkeypatch.setattr(car, "_effect_boundary_ok", lambda plat: (True, ""))

    def test_release_error_after_a_completed_send_keeps_the_result(self, wired, monkeypatch: pytest.MonkeyPatch) -> None:
        """The Cline output and outcome survive a release failure; the error is in the result."""
        monkeypatch.setattr(car, "dispatch_cline", lambda task, plat=None: {"ok": True, "output": "DONE", "elapsed": 1.0, "outcome": "completed"})
        monkeypatch.setattr(arl.BackendLock, "release", lambda self, outcome: (_ for _ in ()).throw(OSError("disk full")))
        res = car.dispatch_autoresearcher("windows", "two word prompt")
        assert res["ok"] is True and res["outcome"] == "completed" and res["output"] == "DONE"
        assert "disk full" in res["release_error"]

    def test_clean_release_reports_no_error(self, wired, monkeypatch: pytest.MonkeyPatch) -> None:
        """When release succeeds the field is present and empty."""
        monkeypatch.setattr(car, "dispatch_cline", lambda task, plat=None: {"ok": True, "output": "DONE", "elapsed": 1.0, "outcome": "completed"})
        res = car.dispatch_autoresearcher("windows", "two word prompt")
        assert res["outcome"] == "completed" and res["release_error"] is None
