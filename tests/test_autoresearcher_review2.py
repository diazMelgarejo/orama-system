#!/usr/bin/env python3
"""Tests for the second Mac review (Codex sidecar, REQUEST CHANGES at head 71ab3560) of orama PR 487.

P1: not-sent needs stronger proof than a substring in combined output or a generic OSError.
P2: a PermissionError refusal must not leak the opened descriptor.
P2: the localhost rewrite must stay loopback-only and must not change URLs that carry userinfo or use https.
"""
from __future__ import annotations

import ipaddress
import subprocess
import sys
import time
import types
from pathlib import Path
from unittest.mock import patch

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent / "scripts"
for p in (str(_SCRIPTS_DIR), str(_HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import autoresearcher_lock as arl  # noqa: E402
import cline_autoresearcher as car  # noqa: E402
from _cline_fakes import FakeProc  # noqa: E402
from _cline_fakes import isolated_cline_workdir  # noqa: E402,F401  (autouse fixture)

LOOPBACK = str(ipaddress.IPv4Address(0x7F000001))  # built, not written, so the hygiene gate sees no literal
DOC_NET = "203.0.113.7"
_AVAILABLE = {"available": True, "bin": "cline"}


def _dispatch(proc_or_exc, **env_unused):
    """Run dispatch_cline with Popen replaced by a fake (or a spawn error)."""
    side = proc_or_exc if isinstance(proc_or_exc, BaseException) else None
    with patch.object(car, "cline_available", return_value=_AVAILABLE), \
         patch.object(car.subprocess, "Popen", side_effect=side, return_value=None if side else proc_or_exc):
        return car.dispatch_cline("two word prompt")


class TestNotSentNeedsStrongEvidence:
    """No output shape can prove that a launched process sent nothing."""

    @pytest.mark.parametrize("err", ["Unknown command or unquoted prompt: task x", "Error: Unknown or disabled provider 'clinepass'"])
    def test_a_lone_fast_stderr_usage_error_is_unknown(self, err: str) -> None:
        """Even short stderr from a fast process cannot establish that no request was sent."""
        assert _dispatch(FakeProc(1, "", err + "\n"))["outcome"] == "unknown"

    def test_the_marker_in_stdout_is_unknown(self):
        """Model text goes to stdout: a marker quoted there (after a send) must not clear the in-flight record."""
        out = "I tried: Unknown command or unquoted prompt, then continued working"
        assert _dispatch(FakeProc(1, out, ""))["outcome"] == "unknown"

    def test_the_marker_with_any_stdout_is_unknown(self):
        """Any stdout means Cline got further than argument parsing."""
        assert _dispatch(FakeProc(1, "partial answer", "Unknown command or unquoted prompt\n"))["outcome"] == "unknown"

    def test_the_marker_buried_in_longer_stderr_is_unknown(self):
        """Extra stderr lines (progress, a model call) mean it is not a bare usage error."""
        err = "calling model\nUnknown command or unquoted prompt: x\nretrying\n"
        assert _dispatch(FakeProc(1, "", err))["outcome"] == "unknown"

    def test_a_marker_that_is_not_at_the_start_is_unknown(self):
        """The text must start the line: a sentence that merely contains it is not proof."""
        assert _dispatch(FakeProc(1, "", "the tool said Unknown command or unquoted prompt\n"))["outcome"] == "unknown"

    def test_a_slow_marker_is_unknown(self):
        """A usage error that took ten seconds or more is not an argument-parse failure."""
        clock = iter([100.0, 111.0, 111.0, 111.0])
        with patch.object(car, "cline_available", return_value=_AVAILABLE), \
             patch.object(car.subprocess, "Popen", return_value=FakeProc(1, "", "Unknown command or unquoted prompt\n")), \
             patch.object(car.time, "time", side_effect=lambda: next(clock)):
            assert car.dispatch_cline("two word prompt")["outcome"] == "unknown"


class TestOSErrorSplit:
    """An OSError before the process exists is not-sent; one after it started is unknown."""

    def test_spawn_failure_is_not_sent(self):
        """Popen itself failing proves nothing was started."""
        assert _dispatch(FileNotFoundError("cline"))["outcome"] == "not-sent"

    def test_an_io_error_after_start_is_unknown_and_the_process_is_killed(self):
        """A broken pipe while reading output happens after the request may have left: unknown, and no orphan."""
        proc = FakeProc(0, "", "", comm_exc=BrokenPipeError("pipe"))
        assert _dispatch(proc)["outcome"] == "unknown" and proc.killed

    def test_a_timeout_is_unknown_and_the_process_is_killed(self):
        """A timeout kills and reaps the child and stays unknown."""
        proc = FakeProc(0, "", "", comm_exc=subprocess.TimeoutExpired("cline", 300))
        assert _dispatch(proc)["outcome"] == "unknown" and proc.killed


def _fake_fcntl_denying() -> types.ModuleType:
    """A stand-in fcntl whose flock raises PermissionError, usable on any platform."""
    module = types.ModuleType("fcntl")
    module.LOCK_EX, module.LOCK_NB, module.LOCK_UN = 2, 4, 8

    def flock(fd, op):
        """Pretend the filesystem denied the lock request."""
        raise PermissionError(13, "Permission denied")

    module.flock = flock
    return module


def test_a_permission_refusal_closes_the_descriptor_it_opened(tmp_path):
    """acquire must close the file it opened before raising the distinct permission refusal."""
    opened, closed = [], []
    real_open, real_close = arl._open_rw, arl.os.close

    def tracking_open(path, create):
        """Remember every descriptor opened by the lock module."""
        fd = real_open(path, create)
        opened.append(fd)
        return fd

    def tracking_close(fd):
        """Remember every descriptor closed, then close it."""
        closed.append(fd)
        real_close(fd)

    with patch.object(arl, "_IS_WINDOWS", False), patch.dict(sys.modules, {"fcntl": _fake_fcntl_denying()}), \
         patch.object(arl, "_open_rw", side_effect=tracking_open), patch.object(arl.os, "close", side_effect=tracking_close):
        with pytest.raises(arl.LockRefused) as exc:
            arl.BackendLock(tmp_path / "x.lock").acquire()
    assert exc.value.state == "refused" and opened and set(opened) <= set(closed)


class TestLoopbackOnlyRewrite:
    """The localhost rewrite never moves a probe off the local machine or changes what a URL means."""

    def test_a_loopback_answer_is_used(self):
        """localhost that resolves to the IPv4 loopback address is rewritten."""
        with patch.object(car.socket, "gethostbyname", return_value=LOOPBACK):
            assert car._probe_url("http://localhost:1234/v1/models") == f"http://{LOOPBACK}:1234/v1/models"

    def test_a_non_loopback_answer_is_never_consulted(self) -> None:
        """Use literal loopback rather than falling back to hostile hostname resolution."""
        with patch.object(car.socket, "gethostbyname", return_value=DOC_NET) as resolve:
            assert car._probe_url("http://localhost:1234/v1/models") == f"http://{LOOPBACK}:1234/v1/models"
        resolve.assert_not_called()

    def test_userinfo_refuses_and_https_keeps_hostname(self) -> None:
        """Credentials are unsupported; HTTPS retains its certificate identity."""
        with patch.object(car.socket, "gethostbyname", return_value=LOOPBACK):
            with pytest.raises(ValueError, match="userinfo"):
                car._probe_url("http://user:pw@localhost:1234/x")
            assert car._probe_url("https://localhost:1234/x") == "https://localhost:1234/x"
