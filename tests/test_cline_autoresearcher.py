#!/usr/bin/env python3
"""Tests for cline_autoresearcher.py — ClinePass AutoResearcher resilience controller."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from cline_autoresearcher import (  # noqa: E402
    detect_platform,
    should_fallback_to_cline,
    dispatch_autoresearcher,
    full_status,
    _fallback_reason,
    cline_available,
    _find_cline,
    _find_hermes,
)


# ── Platform detection ────────────────────────────────────────────────────────

class TestPlatformDetection:
    """Platform detection returns windows or macos."""
    def test_detect_platform_returns_string(self):
        """The detected platform is a string."""
        result = detect_platform()
        assert result in ("windows", "macos")

    def test_detect_platform_windows(self):
        """A Windows host is detected as windows."""
        with patch("os.name", "nt"):
            with patch("platform.system", return_value="Windows"):
                assert detect_platform() == "windows"

    def test_detect_platform_macos(self):
        """A non-Windows host is detected as macos."""
        with patch("os.name", "posix"):
            with patch("platform.system", return_value="Darwin"):
                assert detect_platform() == "macos"


# ── Cline CLI ─────────────────────────────────────────────────────────────────

class TestClineCLI:
    """Discovery of the cline CLI."""
    def test_find_cline_returns_none_if_not_found(self):
        """A missing cline binary yields None."""
        with patch("shutil.which", return_value=None):
            with patch("cline_autoresearcher._is_windows", return_value=False):
                with patch("pathlib.Path.exists", return_value=False):
                    assert _find_cline() is None

    def test_cline_available_returns_false_if_not_found(self):
        """A missing cline binary reports unavailable."""
        with patch("cline_autoresearcher._find_cline", return_value=None):
            result = cline_available()
            assert result["available"] is False
            assert "not found" in result["reason"]


# ── Hermes CLI ────────────────────────────────────────────────────────────────

class TestHermesCLI:
    """Discovery of the hermes CLI."""
    def test_find_hermes_returns_none_if_not_found(self):
        """A missing hermes binary yields None."""
        with patch("shutil.which", return_value=None):
            with patch("os.getenv", return_value=None):
                assert _find_hermes() is None


# ── Fallback reason ───────────────────────────────────────────────────────────

class TestFallbackReason:
    """The one-line reason text for each fallback outcome."""
    def test_fallback_active(self):
        """An active fallback is explained as such."""
        gw = {"paused": True, "running": False, "rate_limited": False}
        backend = {"idle": True}
        cline = {"available": True}
        reason = _fallback_reason(gw, backend, cline, True)
        assert "fallback active" in reason

    def test_gateway_running_no_fallback(self):
        """A running gateway means no fallback is needed."""
        gw = {"paused": False, "running": True, "rate_limited": False}
        backend = {"idle": True}
        cline = {"available": True}
        reason = _fallback_reason(gw, backend, cline, False)
        assert "gateway running" in reason

    def test_backend_not_idle(self):
        """A busy local backend blocks the fallback and says why."""
        gw = {"paused": True, "running": False, "rate_limited": False}
        backend = {"idle": False, "reason": "GPU lock held"}
        cline = {"available": True}
        reason = _fallback_reason(gw, backend, cline, False)
        assert "not idle" in reason

    def test_cline_unavailable(self):
        """A missing cline CLI blocks the fallback and says why."""
        gw = {"paused": True, "running": False, "rate_limited": False}
        backend = {"idle": True}
        cline = {"available": False, "reason": "not found"}
        reason = _fallback_reason(gw, backend, cline, False)
        assert "Cline unavailable" in reason


# ── Should fallback to Cline ──────────────────────────────────────────────────

class TestShouldFallback:
    """The fallback decision from gateway, backend and cline state."""
    @patch("cline_autoresearcher.gateway_status")
    @patch("cline_autoresearcher.local_backend_idle")
    @patch("cline_autoresearcher.cline_available")
    def test_fallback_when_gateway_paused(self, mock_cline, mock_backend, mock_gw):
        """A paused gateway with an idle backend and cline triggers the fallback."""
        mock_gw.return_value = {"paused": True, "running": False, "rate_limited": False}
        mock_backend.return_value = {"idle": True, "reachable": True}
        mock_cline.return_value = {"available": True, "bin": "/usr/bin/cline"}

        result = should_fallback_to_cline("windows")
        assert result["should_fallback"] is True
        assert result["gateway"]["paused"] is True

    @patch("cline_autoresearcher.gateway_status")
    @patch("cline_autoresearcher.local_backend_idle")
    @patch("cline_autoresearcher.cline_available")
    def test_no_fallback_when_gateway_running(self, mock_cline, mock_backend, mock_gw):
        """A running gateway never triggers the fallback."""
        mock_gw.return_value = {"paused": False, "running": True, "rate_limited": False}
        mock_backend.return_value = {"idle": True, "reachable": True}
        mock_cline.return_value = {"available": True, "bin": "/usr/bin/cline"}

        result = should_fallback_to_cline("macos")
        assert result["should_fallback"] is False

    @patch("cline_autoresearcher.gateway_status")
    @patch("cline_autoresearcher.local_backend_idle")
    @patch("cline_autoresearcher.cline_available")
    def test_no_fallback_when_backend_busy(self, mock_cline, mock_backend, mock_gw):
        """A busy backend never triggers the fallback."""
        mock_gw.return_value = {"paused": True, "running": False, "rate_limited": False}
        mock_backend.return_value = {"idle": False, "reason": "GPU lock held"}
        mock_cline.return_value = {"available": True, "bin": "/usr/bin/cline"}

        result = should_fallback_to_cline("windows")
        assert result["should_fallback"] is False

    @patch("cline_autoresearcher.gateway_status")
    @patch("cline_autoresearcher.local_backend_idle")
    @patch("cline_autoresearcher.cline_available")
    def test_no_fallback_when_cline_missing(self, mock_cline, mock_backend, mock_gw):
        """A missing cline never triggers the fallback."""
        mock_gw.return_value = {"paused": True, "running": False, "rate_limited": False}
        mock_backend.return_value = {"idle": True, "reachable": True}
        mock_cline.return_value = {"available": False, "reason": "not found"}

        result = should_fallback_to_cline("macos")
        assert result["should_fallback"] is False

    @patch("cline_autoresearcher.gateway_status")
    @patch("cline_autoresearcher.local_backend_idle")
    @patch("cline_autoresearcher.cline_available")
    def test_fallback_when_rate_limited(self, mock_cline, mock_backend, mock_gw):
        """A rate-limited gateway triggers the fallback."""
        mock_gw.return_value = {"paused": False, "running": False, "rate_limited": True}
        mock_backend.return_value = {"idle": True, "reachable": True}
        mock_cline.return_value = {"available": True, "bin": "/usr/bin/cline"}

        result = should_fallback_to_cline("macos")
        assert result["should_fallback"] is True


# ── Dispatch AutoResearcher ───────────────────────────────────────────────────

class TestDispatchAutoResearcher:
    """Dispatching a task through the local backend or ClinePass."""
    @patch("cline_autoresearcher.should_fallback_to_cline")
    def test_dispatch_when_fallback_inactive(self, mock_check):
        """Dispatch uses the local backend when the fallback is inactive."""
        mock_check.return_value = {"should_fallback": False, "reason": "gateway running"}

        result = dispatch_autoresearcher("windows", "test task")
        assert result["ok"] is False
        assert result["fallback_active"] is False
        assert "not active" in result["output"]

    @patch("cline_autoresearcher.dispatch_cline")
    @patch("cline_autoresearcher.should_fallback_to_cline")
    def test_dispatch_local_backend_success(self, mock_check, mock_dispatch):
        """A successful local backend dispatch is reported as such."""
        mock_check.return_value = {"should_fallback": True, "reason": "gateway down"}
        mock_dispatch.return_value = {
            "ok": True,
            "output": "task completed",
            "elapsed": 5.0,
            "provider": "lm-studio",
            "model": "qwen3.5-27b",
        }

        result = dispatch_autoresearcher("windows", "test task")
        assert result["ok"] is True
        assert result["fallback_tier"] == "local-backend"
        assert result["fallback_active"] is True

    @patch("cline_autoresearcher.dispatch_cline")
    @patch("cline_autoresearcher.should_fallback_to_cline")
    def test_dispatch_fallback_to_cline_pass(self, mock_check, mock_dispatch):
        """A failed local dispatch falls back to ClinePass."""
        mock_check.return_value = {"should_fallback": True, "reason": "gateway down"}
        # First call (local backend) fails, second call (ClinePass) succeeds
        mock_dispatch.side_effect = [
            {"ok": False, "output": "local backend failed", "elapsed": 1.0},
            {"ok": True, "output": "cline-pass completed", "elapsed": 10.0},
        ]

        result = dispatch_autoresearcher("macos", "test task")
        assert result["ok"] is True
        assert result["fallback_tier"] == "cline-pass-credits"
        assert result["fallback_active"] is True
        assert result["local_backend_attempt"]["ok"] is False


# ── Full status ───────────────────────────────────────────────────────────────

class TestFullStatus:
    """The combined status including the peer session."""
    @patch("cline_autoresearcher.peer_session_status")
    @patch("cline_autoresearcher.should_fallback_to_cline")
    def test_full_status_structure(self, mock_check, mock_peer):
        """The combined status carries the expected keys."""
        mock_check.return_value = {
            "should_fallback": False,
            "reason": "gateway running",
            "gateway": {"running": True},
            "local_backend": {"idle": True},
            "cline": {"available": True},
        }
        mock_peer.return_value = {
            "ok": True,
            "mode": "co-orchestration",
            "failure_count": 0,
            "max_failures": 10,
        }

        status = full_status("windows")
        assert status["platform"] == "windows"
        assert "timestamp" in status
        assert "timestamp_iso" in status
        assert "autoresearcher" in status
        assert "peer_session" in status
        assert status["solo_mode"] is False
        assert status["peer_unreachable_count"] == 0

    @patch("cline_autoresearcher.peer_session_status")
    @patch("cline_autoresearcher.should_fallback_to_cline")
    def test_full_status_solo_mode(self, mock_check, mock_peer):
        """A solo peer session sets the solo flag and the failure count."""
        mock_check.return_value = {
            "should_fallback": True,
            "reason": "gateway down",
            "gateway": {"running": False, "paused": True},
            "local_backend": {"idle": True},
            "cline": {"available": True},
        }
        mock_peer.return_value = {
            "ok": True,
            "mode": "macos-only",
            "failure_count": 10,
            "max_failures": 10,
        }

        status = full_status("macos")
        assert status["solo_mode"] is True
        assert status["peer_unreachable_count"] == 10


class TestStaleCoderLock:
    """The idle gate must not be blocked forever by a lock whose owner is gone."""

    def test_missing_lock_is_not_held(self, tmp_path):
        """No lock file means not held."""
        from cline_autoresearcher import lock_is_held

        assert lock_is_held(tmp_path / "nope.lock") is False

    def test_live_owner_and_fresh_file_is_held(self, tmp_path):
        """A lock naming this very process, just written, is held."""
        from cline_autoresearcher import lock_is_held

        lock = tmp_path / "win_pulse.lock"
        lock.write_text(f"{os.getpid()} ", encoding="utf-8")
        assert lock_is_held(lock) is True

    def test_dead_owner_is_stale(self, tmp_path):
        """A lock naming a process that does not exist is stale (the 109-day-old July lock case)."""
        from cline_autoresearcher import lock_is_held

        lock = tmp_path / "win_pulse.lock"
        lock.write_text("4294967 ", encoding="utf-8")
        assert lock_is_held(lock) is False

    def test_old_file_is_stale_even_if_the_pid_is_alive(self, tmp_path):
        """A reused PID cannot keep a months-old lock alive: age over the limit is stale."""
        from cline_autoresearcher import LOCK_MAX_AGE_SECONDS, lock_is_held

        lock = tmp_path / "win_pulse.lock"
        lock.write_text(f"{os.getpid()} ", encoding="utf-8")
        assert lock_is_held(lock, now=lock.stat().st_mtime + LOCK_MAX_AGE_SECONDS + 1) is False

    @pytest.mark.parametrize("content", ["", "not-a-pid", "\n"])
    def test_unparseable_lock_is_treated_as_held(self, tmp_path, content):
        """When staleness cannot be proven the gate stays closed."""
        from cline_autoresearcher import lock_is_held

        lock = tmp_path / "win_pulse.lock"
        lock.write_text(content, encoding="utf-8")
        assert lock_is_held(lock) is True

    @patch("cline_autoresearcher._probe_http_ok", return_value=True)
    def test_windows_backend_is_idle_with_a_dead_owner_lock(self, _probe, tmp_path):
        """local_backend_idle reports idle for a Windows host whose lock owner died."""
        import cline_autoresearcher as car

        lock = tmp_path / "win_pulse.lock"
        lock.write_text("4294967 ", encoding="utf-8")
        with patch.object(car, "WIN_PULSE_LOCK", lock):
            assert car.local_backend_idle("windows")["idle"] is True

    @patch("cline_autoresearcher._probe_http_ok", return_value=True)
    def test_windows_backend_is_busy_with_a_live_owner_lock(self, _probe, tmp_path):
        """local_backend_idle still reports busy while the lock owner is alive."""
        import cline_autoresearcher as car

        lock = tmp_path / "win_pulse.lock"
        lock.write_text(f"{os.getpid()} ", encoding="utf-8")
        with patch.object(car, "WIN_PULSE_LOCK", lock):
            assert car.local_backend_idle("windows")["idle"] is False

    @patch("cline_autoresearcher._probe_http_ok", return_value=True)
    def test_macos_backend_ignores_a_dead_owner_lock(self, _probe, tmp_path):
        """The same stale-lock rule applies to the Mac coder lock."""
        import cline_autoresearcher as car

        lock = tmp_path / "mac_pulse.lock"
        lock.write_text("4294967 ", encoding="utf-8")
        with patch.object(car, "MAC_PULSE_LOCK", lock):
            assert car.local_backend_idle("macos")["idle"] is True
