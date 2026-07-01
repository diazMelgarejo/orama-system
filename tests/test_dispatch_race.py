"""Tests for _dispatch_race and dispatch_race in spawn_agents.py.

Uses unittest.mock.patch to mock the individual dispatch legs so tests
run without real CLIs, network, or GPU.

Cases:
  1. cursor wins → winner="cursor"
  2. hermes wins → winner="hermes-lmstudio-win"
  3. both fail → fallback to direct-lmstudio-win → winner="direct-lmstudio-win"
  4. all fail → ok=False, winner=None
  5. regression: _dispatch_hermes_lmstudio_win fallback does not raise NameError
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import spawn_agents  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine to completion in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


def _ok(output: str, elapsed: float = 0.1) -> dict:
    return {"ok": True, "output": output, "elapsed": elapsed}


def _fail(output: str, elapsed: float = 0.1) -> dict:
    return {"ok": False, "output": output, "elapsed": elapsed}


# ── Test 1: cursor wins ───────────────────────────────────────────────────────

def test_cursor_wins_race():
    """When cursor returns ok, race should return cursor output with winner='cursor'."""
    with patch.object(spawn_agents, "_dispatch_cursor", new_callable=AsyncMock) as mock_cursor, \
         patch.object(spawn_agents, "_dispatch_hermes_lmstudio_win", new_callable=AsyncMock) as mock_hermes, \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        mock_cursor.return_value = _ok("CURSOR_OK")
        mock_hermes.return_value = _fail("hermes failed")
        mock_direct.return_value = _fail("direct failed")

        result = _run(spawn_agents.dispatch_race("test task"))

    assert result["ok"] is True
    assert result["winner"] == "cursor"
    assert "CURSOR_OK" in result["output"]
    assert "[RACE WINNER: cursor]" in result["output"]


# ── Test 2: hermes wins ───────────────────────────────────────────────────────

def test_hermes_wins_race():
    """When hermes returns ok, race should return hermes output with winner='hermes-lmstudio-win'."""
    with patch.object(spawn_agents, "_dispatch_cursor", new_callable=AsyncMock) as mock_cursor, \
         patch.object(spawn_agents, "_dispatch_hermes_lmstudio_win", new_callable=AsyncMock) as mock_hermes, \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        mock_cursor.return_value = _fail("cursor failed")
        mock_hermes.return_value = _ok("HERMES_OK")
        mock_direct.return_value = _fail("direct failed")

        result = _run(spawn_agents.dispatch_race("test task"))

    assert result["ok"] is True
    assert result["winner"] == "hermes-lmstudio-win"
    assert "HERMES_OK" in result["output"]
    assert "[RACE WINNER: hermes-lmstudio-win]" in result["output"]


# ── Test 3: both fail → fallback to direct-lmstudio-win ───────────────────────

def test_both_fail_fallback_to_direct_lmstudio():
    """When both racers fail but direct lmstudio succeeds, winner='direct-lmstudio-win'."""
    with patch.object(spawn_agents, "_dispatch_cursor", new_callable=AsyncMock) as mock_cursor, \
         patch.object(spawn_agents, "_dispatch_hermes_lmstudio_win", new_callable=AsyncMock) as mock_hermes, \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        mock_cursor.return_value = _fail("cursor failed")
        mock_hermes.return_value = _fail("hermes failed")
        mock_direct.return_value = _ok("DIRECT_OK")

        result = _run(spawn_agents.dispatch_race("test task"))

    assert result["ok"] is True
    assert result["winner"] == "direct-lmstudio-win"
    assert "DIRECT_OK" in result["output"]
    assert "[RACE FALLBACK: direct-lmstudio-win]" in result["output"]


# ── Test 4: all fail ──────────────────────────────────────────────────────────

def test_all_fail_returns_failure():
    """When all legs fail, race should return ok=False with winner=None."""
    with patch.object(spawn_agents, "_dispatch_cursor", new_callable=AsyncMock) as mock_cursor, \
         patch.object(spawn_agents, "_dispatch_hermes_lmstudio_win", new_callable=AsyncMock) as mock_hermes, \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        mock_cursor.return_value = _fail("cursor failed")
        mock_hermes.return_value = _fail("hermes failed")
        mock_direct.return_value = _fail("direct failed")

        result = _run(spawn_agents.dispatch_race("test task"))

    assert result["ok"] is False
    assert result["winner"] is None
    assert "All raced Windows agents failed" in result["output"]
    assert "cursor" in result["output"]
    assert "hermes-lmstudio-win" in result["output"]
    assert "direct-lmstudio-win" in result["output"]


# ── Test 5: regression — _exc NameError in fallback path ──────────────────────

def test_hermes_fallback_no_name_error():
    """Regression: _dispatch_hermes_lmstudio_win fallback must not raise NameError.

    The old code referenced `_exc` which was never defined, causing a NameError
    when the hermes leg timed out and fell back to direct lmstudio. This test
    mocks the hermes subprocess to time out and verifies the fallback path
    completes without raising.
    """
    with patch.object(spawn_agents, "_find_hermes", return_value="/fake/hermes"), \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        # Simulate the direct lmstudio call succeeding (fallback path)
        mock_direct.return_value = _ok("FALLBACK_OK")

        # We need to make the hermes subprocess timeout. We patch
        # asyncio.create_subprocess_exec to return a mock proc whose
        # communicate() raises TimeoutError.
        async def _fake_communicate():
            raise asyncio.TimeoutError()

        class _FakeProc:
            def kill(self):
                pass

        async def _fake_subprocess_exec(*args, **kwargs):
            proc = _FakeProc()
            proc.communicate = _fake_communicate
            return proc

        with patch.object(spawn_agents.asyncio, "create_subprocess_exec", side_effect=_fake_subprocess_exec):
            result = _run(spawn_agents._dispatch_hermes_lmstudio_win("test task"))

    # The fallback should succeed (direct lmstudio returned ok)
    assert result["ok"] is True
    assert "FALLBACK_OK" in result["output"]
    assert "[RACE LEG: hermes-lmstudio-win" in result["output"]
    # No NameError should be raised — if we got here, the regression is fixed


# ── Test 6: winner field always present ───────────────────────────────────────

def test_winner_field_always_present():
    """The winner field must always be present in race results, even on failure."""
    with patch.object(spawn_agents, "_dispatch_cursor", new_callable=AsyncMock) as mock_cursor, \
         patch.object(spawn_agents, "_dispatch_hermes_lmstudio_win", new_callable=AsyncMock) as mock_hermes, \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        mock_cursor.return_value = _ok("CURSOR_OK")
        mock_hermes.return_value = _fail("hermes failed")
        mock_direct.return_value = _fail("direct failed")

        result = _run(spawn_agents.dispatch_race("test task"))

    assert "winner" in result
    assert result["winner"] == "cursor"