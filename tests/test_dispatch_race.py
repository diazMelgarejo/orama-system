"""Tests for _dispatch_race and dispatch_race in spawn_agents.py.

Uses unittest.mock.patch to mock the individual dispatch legs so tests
run without real CLIs, network, or GPU.

Cases:
  1. cursor wins → winner="cursor"
  2. hermes wins → winner="hermes-lmstudio-win"
  3. both fail → fallback to direct-lmstudio-win → winner="direct-lmstudio-win"
  4. all fail → ok=False, winner=None
  5. regression: _dispatch_hermes_lmstudio_win fallback does not raise NameError

NOTE (2026-07-03): commit 60db9b7 temporarily narrowed _dispatch_race's racers
dict to a single "direct-lmstudio-win" leg pending cursor-agent standalone
stability validation (see .logs/cursor_standalone_retry_due.txt). Tests 1, 2,
4, and 6 assert the full 3-way race (cursor/hermes/direct) and are skipped
while that deferral is active — this file is the tripwire that re-enables
them automatically once the retry-due date passes, so the coverage isn't
silently lost or permanently deleted.
"""
from __future__ import annotations

import asyncio
import datetime
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import spawn_agents  # noqa: E402

_RETRY_DUE_FILE = Path(__file__).parent.parent / ".logs" / "cursor_standalone_retry_due.txt"


def _cursor_race_leg_deferred() -> str | None:
    """Return a skip reason if the cursor/hermes race legs are still deferred, else None."""
    if not _RETRY_DUE_FILE.exists():
        return None
    text = _RETRY_DUE_FILE.read_text(encoding="utf-8").strip()
    try:
        due = datetime.date.fromisoformat(text.rsplit(":", 1)[-1].strip())
    except ValueError:
        return f"cursor race leg deferred (unparseable due-date marker: {text!r})"
    if datetime.date.today() < due:
        return f"cursor race leg deferred until {due.isoformat()} ({text!r})"
    return None


_CURSOR_RACE_SKIP = _cursor_race_leg_deferred()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine to completion in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


def _ok(output: str, elapsed: float = 0.1) -> dict:
    return {"ok": True, "output": output, "elapsed": elapsed}


def _fail(output: str, elapsed: float = 0.1) -> dict:
    return {"ok": False, "output": output, "elapsed": elapsed}


# ── Test 1: cursor wins ───────────────────────────────────────────────────────

@pytest.mark.skipif(bool(_CURSOR_RACE_SKIP), reason=str(_CURSOR_RACE_SKIP))
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

@pytest.mark.skipif(bool(_CURSOR_RACE_SKIP), reason=str(_CURSOR_RACE_SKIP))
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

@pytest.mark.skipif(bool(_CURSOR_RACE_SKIP), reason=str(_CURSOR_RACE_SKIP))
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

@pytest.mark.skipif(bool(_CURSOR_RACE_SKIP), reason=str(_CURSOR_RACE_SKIP))
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

def test_hermes_timeout_fails_cleanly_without_internal_fallback():
    """Regression + design test for _dispatch_hermes_lmstudio_win's timeout path.

    Originally a regression test for a NameError (`_exc` referenced but
    never defined) when this function's old internal fallback-to-direct-
    lmstudio path was reached on timeout. That internal fallback has since
    been removed entirely (review 4837854088: fallback handling belongs
    in _dispatch_race() alone, not duplicated here) -- so this now
    verifies the timeout path fails cleanly with no crash AND, just as
    importantly, does NOT call _dispatch_lmstudio() itself anymore.
    """
    with patch.object(spawn_agents, "_find_hermes", return_value="/fake/hermes"), \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        async def _fake_communicate():
            raise asyncio.TimeoutError()

        class _FakeProc:
            def __init__(self):
                self.returncode = None

            def kill(self):
                self.returncode = -9

            async def wait(self):
                return self.returncode

        async def _fake_subprocess_exec(*args, **kwargs):
            proc = _FakeProc()
            proc.communicate = _fake_communicate
            return proc

        with patch.object(spawn_agents.asyncio, "create_subprocess_exec", side_effect=_fake_subprocess_exec):
            result = _run(spawn_agents._dispatch_hermes_lmstudio_win("test task"))

    # No NameError or other crash — if we got here, that regression stays fixed.
    assert result["ok"] is False
    assert "hermes-lmstudio-win" in result["output"]
    # The single-layer-fallback contract: this function must not itself
    # call _dispatch_lmstudio() anymore. That's _dispatch_race()'s job.
    mock_direct.assert_not_awaited()


@pytest.mark.unit
def test_hermes_nonzero_exit_with_output_is_failure() -> None:
    """Non-zero Hermes exit must not count as success even with stdout text."""
    with patch.object(spawn_agents, "_find_hermes", return_value="/fake/hermes"), \
         patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:

        class _FakeProc:
            returncode = 1

            async def communicate(self):
                return (b"stderr-ish output", b"")

            async def kill(self):
                self.returncode = -9

            async def wait(self):
                return self.returncode

        async def _fake_subprocess_exec(*args, **kwargs):
            return _FakeProc()

        with patch.object(spawn_agents.asyncio, "create_subprocess_exec", side_effect=_fake_subprocess_exec):
            result = _run(spawn_agents._dispatch_hermes_lmstudio_win("test task"))

    assert result["ok"] is False
    mock_direct.assert_not_awaited()


@pytest.mark.unit
def test_hermes_uses_win_coder_endpoint_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hermes subprocess env must route through $WIN_CODER_ENDPOINTS."""
    monkeypatch.setattr(spawn_agents, "WIN_CODER_ENDPOINT", "http://win-coder.example:1234")

    captured: dict = {}

    with patch.object(spawn_agents, "_find_hermes", return_value="/fake/hermes"):

        class _FakeProc:
            returncode = 0

            async def communicate(self):
                return (b"HERMES_OK", b"")

        async def _fake_subprocess_exec(*args, **kwargs):
            captured["env"] = kwargs.get("env", {})
            return _FakeProc()

        with patch.object(spawn_agents.asyncio, "create_subprocess_exec", side_effect=_fake_subprocess_exec):
            result = _run(spawn_agents._dispatch_hermes_lmstudio_win("test task"))

    assert result["ok"] is True
    assert captured["env"]["LM_STUDIO_WIN_ENDPOINTS"] == "http://win-coder.example:1234"


# ── Test 6: winner field always present ───────────────────────────────────────

@pytest.mark.skipif(bool(_CURSOR_RACE_SKIP), reason=str(_CURSOR_RACE_SKIP))
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


# ── Test 7: current deferred-state behavior (60db9b7) ─────────────────────────

@pytest.mark.skipif(not bool(_CURSOR_RACE_SKIP), reason="only meaningful while cursor race leg is deferred")
def test_direct_lmstudio_only_racer_while_deferred():
    """While cursor/hermes race legs are deferred, dispatch_race must call
    direct-lmstudio-win exactly once (as the sole racer) and win outright —
    never as a "[RACE FALLBACK: ...]" (that phrasing implies cursor/hermes
    were tried first and failed, which is false during the deferral)."""
    with patch.object(spawn_agents, "_dispatch_lmstudio", new_callable=AsyncMock) as mock_direct:
        mock_direct.return_value = _ok("DIRECT_OK")
        result = _run(spawn_agents.dispatch_race("test task"))

    assert mock_direct.await_count == 1
    assert result["ok"] is True
    assert result["winner"] == "direct-lmstudio-win"
    assert "[RACE WINNER: direct-lmstudio-win]" in result["output"]