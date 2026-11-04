"""Tests for POST /api/tools/refresh limits and the bounded port-check resolver."""

from __future__ import annotations

import asyncio
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterator, List

import pytest
from fastapi import HTTPException

from orama_system import portal_server


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isolate the rate limiter and pending counter for every test."""
    monkeypatch.setattr(portal_server, "_CONFIGURE_RATE", {})
    monkeypatch.setattr(portal_server, "_port_check_pending", 0, raising=False)
    yield


def test_refresh_is_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """Excess refreshes in the window get HTTP 429 and never clear the cache."""
    clears: List[int] = []
    monkeypatch.setattr(portal_server, "_clear_cli_version_cache", lambda: clears.append(1))
    monkeypatch.setattr(portal_server, "_probe_tools_sync", lambda: {"ok": True})

    async def run() -> None:
        """Call the route up to the limit, then once more."""
        for _ in range(portal_server._TOOLS_REFRESH_MAX_CALLS):
            assert await portal_server.api_tools_refresh() == {"ok": True}
        with pytest.raises(HTTPException) as exc:
            await portal_server.api_tools_refresh()
        assert exc.value.status_code == 429

    asyncio.run(run())
    assert len(clears) == portal_server._TOOLS_REFRESH_MAX_CALLS


def test_refresh_clears_cache_off_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cache is cleared on an executor worker, before the probe runs."""
    seen: List[Any] = []

    def fake_clear() -> None:
        """Record the thread that clears the cache."""
        seen.append(("clear", threading.current_thread()))

    def fake_probe() -> Dict[str, Any]:
        """Record probe order."""
        seen.append(("probe", threading.current_thread()))
        return {}

    monkeypatch.setattr(portal_server, "_clear_cli_version_cache", fake_clear)
    monkeypatch.setattr(portal_server, "_probe_tools_sync", fake_probe)

    async def run() -> threading.Thread:
        """Run the route and return the event-loop thread."""
        await portal_server.api_tools_refresh()
        return threading.current_thread()

    loop_thread = asyncio.run(run())
    assert [name for name, _ in seen] == ["clear", "probe"]
    assert seen[0][1] is not loop_thread


def test_tcp_port_open_cancels_queued_lookup_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A lookup still queued when the budget expires is cancelled and never runs."""
    gate = threading.Event()
    started = threading.Semaphore(0)
    executed: List[str] = []
    pool = ThreadPoolExecutor(max_workers=2)
    monkeypatch.setattr(portal_server, "_port_check_resolver", pool)

    def fake_getaddrinfo(host: str, *_args: Any, **_kwargs: Any) -> List[Any]:
        """Block until released, recording which hosts actually ran."""
        executed.append(host)
        started.release()
        gate.wait(timeout=10)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    try:
        blockers = [pool.submit(socket.getaddrinfo, name, 80) for name in ("busy-a", "busy-b")]
        assert started.acquire(timeout=5) and started.acquire(timeout=5)
        assert portal_server._tcp_port_open("queued-host", 80, 0.2) is False
    finally:
        gate.set()
        pool.shutdown(wait=True)
    assert [f.result() for f in blockers] == [[], []]
    assert "queued-host" not in executed
    assert portal_server._port_check_pending == 0


def test_tcp_port_open_bounded_pending_skips_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    """At the pending cap the port counts as closed without submitting a lookup."""
    submitted: List[Any] = []

    class _Pool:
        """Resolver stand-in that records submissions."""

        def submit(self, *args: Any, **kwargs: Any) -> Any:
            """Record the submission and fail loudly."""
            submitted.append(args)
            raise AssertionError("lookup must not be submitted")

    monkeypatch.setattr(portal_server, "_port_check_resolver", _Pool())
    monkeypatch.setattr(portal_server, "_port_check_pending", portal_server._PORT_CHECK_MAX_PENDING)
    assert portal_server._tcp_port_open("host.invalid", 80, 5.0) is False
    assert submitted == []
    assert portal_server._port_check_pending == portal_server._PORT_CHECK_MAX_PENDING
