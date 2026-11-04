#!/usr/bin/env python3
"""/api/status latency: CLI version checks are cached and overlap the network probes."""
from __future__ import annotations

import asyncio
import subprocess
import time
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from orama_system import portal_server

DELAY = 0.4


@pytest.fixture(autouse=True)
def _fresh_cli_cache() -> Iterator[None]:
    """Start and end every test with an empty CLI version cache."""
    getattr(portal_server, "_cli_version_cache", {}).clear()
    yield
    getattr(portal_server, "_cli_version_cache", {}).clear()


def test_cli_version_runs_each_binary_once_within_the_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated status polls reuse a CLI's --version result instead of relaunching it."""
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        """Record the launch and report a healthy CLI."""
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout=b"tool 1.2.3\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    first = portal_server._cli_version("/fake/bin/tool")
    second = portal_server._cli_version("/fake/bin/tool")

    assert first == second == (0, "tool 1.2.3\n")
    assert calls == [["/fake/bin/tool", "--version"]]


def test_cli_version_caches_a_failed_launch_and_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CLI that times out is not relaunched on every poll, but is retried after the TTL."""
    calls: list[str] = []

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        """Simulate a CLI that hangs until the timeout."""
        calls.append(argv[0])
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert portal_server._cli_version("/fake/bin/slow") is None
    assert portal_server._cli_version("/fake/bin/slow") is None
    assert calls == ["/fake/bin/slow"]

    monkeypatch.setattr(portal_server, "_CLI_VERSION_TTL_SECONDS", 0.0)
    assert portal_server._cli_version("/fake/bin/slow") is None
    assert calls == ["/fake/bin/slow", "/fake/bin/slow"]


def test_status_payload_overlaps_tool_checks_and_ollama_ps_with_network_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool checks, the Ollama ps probe and the other probes run concurrently, not in sequence."""

    async def slow(result: Any) -> Any:
        """Return *result* after the shared probe delay."""
        await asyncio.sleep(DELAY)
        return result

    def slow_tools() -> dict[str, dict[str, bool]]:
        """Stand in for the synchronous tool checks, blocking for the probe delay."""
        time.sleep(DELAY)
        return {"codex-cli": {"ok": True}, "gemini-cli": {"ok": False}}

    monkeypatch.setattr(portal_server, "_get_win_lms_url", lambda: "http://192.0.2.10:1234")
    monkeypatch.setattr(portal_server, "_get_win_ollama_url", lambda: "http://192.0.2.10:11434")
    monkeypatch.setattr(portal_server, "_probe_http", lambda client, url: slow((True, "1")))
    monkeypatch.setattr(portal_server, "_probe_lms_models", lambda client, ep, tok: slow((False, [])))
    monkeypatch.setattr(portal_server, "_probe_ollama_models", lambda client, ep: slow((False, [])))
    monkeypatch.setattr(portal_server, "_probe_ollama_ps", lambda client, ep: slow(True))
    monkeypatch.setattr(portal_server, "_probe_activity", lambda client: slow([]))
    monkeypatch.setattr(portal_server, "_probe_agents", lambda client: slow([]))
    monkeypatch.setattr(portal_server, "_probe_routing", lambda client: slow(None))
    monkeypatch.setattr(portal_server, "_probe_queue_depth", lambda client: slow(0))
    monkeypatch.setattr(portal_server, "_probe_supervisor_jobs", lambda client: slow([]))
    monkeypatch.setattr(portal_server, "_probe_tools_sync", slow_tools)
    monkeypatch.setattr(portal_server, "_hardware_policy_status", lambda services: {})

    started = time.perf_counter()
    payload = asyncio.run(portal_server._build_portal_status_payload())
    elapsed = time.perf_counter() - started

    assert payload["services"]["ollama_mac"]["busy"] is True
    assert payload["codex_available"] is True
    assert payload["gemini_available"] is False
    # Sequential phases would take at least 3 * DELAY; concurrent ones about 1 * DELAY.
    assert elapsed < 2 * DELAY, f"status payload took {elapsed:.2f}s; phases ran in sequence"


def test_tcp_port_open_detects_a_listening_port() -> None:
    """A real loopback listener is reported open."""
    import socket

    with socket.create_server(("localhost", 0)) as server:
        port = server.getsockname()[1]
        assert portal_server._tcp_port_open("localhost", port, budget_seconds=1.0) is True


def test_tcp_port_open_shares_one_budget_across_resolved_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two unreachable addresses cost one budget in total, not one budget each."""
    import socket

    budget = 0.3
    addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.1", 9)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.2", 9)),
    ]

    class HangingSocket:
        """Socket stand-in whose connect waits out its timeout, like a dropped SYN."""

        def __init__(self, *args: Any) -> None:
            """Accept the family/type/proto arguments and start with no timeout."""
            self.timeout = None

        def __enter__(self) -> Any:
            """Support use as a context manager."""
            return self

        def __exit__(self, *exc: Any) -> bool:
            """Nothing to close."""
            return False

        def settimeout(self, value: float) -> None:
            """Remember the per-attempt timeout."""
            self.timeout = value

        def connect(self, addr: tuple[str, int]) -> None:
            """Block for the remaining timeout, then fail."""
            time.sleep(self.timeout)
            raise socket.timeout("timed out")

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrs)
    monkeypatch.setattr(socket, "socket", HangingSocket)

    started = time.perf_counter()
    assert portal_server._tcp_port_open("example.test", 9, budget_seconds=budget) is False
    assert time.perf_counter() - started < 1.5 * budget


def test_tcp_port_open_reaches_a_live_second_address_after_a_dead_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """A dead first address must not use up the budget the live one needs."""
    import socket

    addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.1", 9)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.2", 9)),
    ]

    class FirstDeadSocket:
        """Socket stand-in: the first address hangs out its timeout, the second accepts."""

        def __init__(self, *args: Any) -> None:
            """Start with no timeout."""
            self.timeout = None

        def __enter__(self) -> Any:
            """Support use as a context manager."""
            return self

        def __exit__(self, *exc: Any) -> bool:
            """Nothing to close."""
            return False

        def settimeout(self, value: float) -> None:
            """Remember the per-attempt timeout."""
            self.timeout = value

        def connect(self, addr: tuple[str, int]) -> None:
            """Hang on the first address; connect instantly to the second."""
            if addr == addrs[0][4]:
                time.sleep(self.timeout)
                raise socket.timeout("timed out")

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrs)
    monkeypatch.setattr(socket, "socket", FirstDeadSocket)

    assert portal_server._tcp_port_open("example.test", 9, budget_seconds=0.4) is True


def test_cli_launch_limit_is_one_hour() -> None:
    """Policy: request paths launch each CLI at most once per hour."""
    assert portal_server._CLI_VERSION_TTL_SECONDS == 3600.0


def _fake_cli_env(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    """Make codex and gemini resolvable and record every --version launch."""
    import shutil

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        """Record the launch and report a healthy CLI."""
        calls.append(argv[0])
        return SimpleNamespace(returncode=0, stdout=b"cli 1.0\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda name: f"/fake/bin/{name}")
    monkeypatch.setattr(portal_server.os.path, "exists", lambda p: str(p).startswith("/fake/bin/"))
    monkeypatch.setattr(portal_server, "_tcp_port_open", lambda *a, **k: False)


def test_repeated_tool_probes_launch_each_cli_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Many status/tools polls inside the hour launch codex and gemini once each."""
    calls: list[str] = []
    _fake_cli_env(monkeypatch, calls)

    for _ in range(5):
        tools = portal_server._probe_tools_sync()

    assert tools["codex-cli"]["ok"] is True
    assert tools["gemini-cli"]["ok"] is True
    assert sorted(calls) == ["/fake/bin/codex", "/fake/bin/gemini"]


def test_manual_refresh_relaunches_each_cli_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /api/tools/refresh is the explicit way to relaunch CLIs inside the hour."""
    calls: list[str] = []
    _fake_cli_env(monkeypatch, calls)

    portal_server._probe_tools_sync()
    asyncio.run(portal_server.api_tools_refresh())

    assert sorted(calls) == ["/fake/bin/codex", "/fake/bin/codex", "/fake/bin/gemini", "/fake/bin/gemini"]


def test_manual_refresh_requires_control_plane_auth() -> None:
    """The refresh route is not public: it needs mesh credentials like other /api routes."""
    from utils.control_plane_auth import portal_requires_auth

    assert portal_requires_auth("/api/tools/refresh", "POST") is True


def test_tcp_port_open_bounds_slow_address_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """A hanging name lookup is cut off at the budget instead of stalling the status response."""
    import socket

    def slow_getaddrinfo(*args: Any, **kwargs: Any) -> list[Any]:
        """Simulate a resolver that answers long after the budget."""
        time.sleep(1.0)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", slow_getaddrinfo)

    started = time.perf_counter()
    assert portal_server._tcp_port_open("example.test", 9, budget_seconds=0.2) is False
    assert time.perf_counter() - started < 0.6


def test_cli_version_expires_on_the_clock_at_one_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real one-hour TTL is honoured: no relaunch at 3599 s, exactly one at 3601 s."""
    launches: list[str] = []
    now = {"t": 1000.0}

    def fake_monotonic() -> float:
        """Return the controllable fake clock."""
        return now["t"]

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        """Record the launch and report a healthy CLI."""
        launches.append(argv[0])
        return SimpleNamespace(returncode=0, stdout=b"tool 1.0\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(portal_server.time, "monotonic", fake_monotonic)
    assert portal_server._CLI_VERSION_TTL_SECONDS == 3600.0

    t0 = now["t"]
    portal_server._cli_version("/fake/bin/tool")
    assert len(launches) == 1

    now["t"] = t0 + 3599
    portal_server._cli_version("/fake/bin/tool")
    assert len(launches) == 1

    now["t"] = t0 + 3601
    portal_server._cli_version("/fake/bin/tool")
    assert len(launches) == 2

    # The relaunch re-stamped the cache at t0 + 3601, so the next poll is cached again.
    portal_server._cli_version("/fake/bin/tool")
    assert len(launches) == 2


def test_tcp_port_open_recovers_after_the_resolver_pool_saturates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hung lookups fill both resolver workers; callers still fail fast, then work once released."""
    import socket
    import threading

    real_getaddrinfo = socket.getaddrinfo
    release = threading.Event()
    started = {"blocked-a.test": threading.Event(), "blocked-b.test": threading.Event()}

    def fake_getaddrinfo(host: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Block the two named hosts until released; resolve nothing for the queued host."""
        if host in started:
            started[host].set()
            release.wait(timeout=10.0)
            return []
        if host == "queued.test":
            return []
        return real_getaddrinfo(host, *args, **kwargs)

    results: dict[str, bool] = {}

    # Earlier tests can leave a slow lookup in the shared pool; wait until both workers are idle.
    idle = threading.Barrier(2, timeout=10.0)

    def rendezvous() -> None:
        """Return only once both resolver workers are free at the same moment."""
        idle.wait()

    for drain in [portal_server._port_check_resolver.submit(rendezvous) for _ in range(2)]:
        drain.result(timeout=15.0)

    def blocked_call(host: str) -> None:
        """Run a port check whose lookup hangs; it gives up after its own budget."""
        results[host] = portal_server._tcp_port_open(host, 9, budget_seconds=1.0)

    threads = [threading.Thread(target=blocked_call, args=(host,), daemon=True) for host in started]
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    try:
        for thread in threads:
            thread.start()
        for event in started.values():
            assert event.wait(timeout=5.0), "a resolver worker never picked up its blocking lookup"

        begun = time.perf_counter()
        assert portal_server._tcp_port_open("queued.test", 9, budget_seconds=0.3) is False
        assert time.perf_counter() - begun < 0.8
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5.0)

    assert results == {"blocked-a.test": False, "blocked-b.test": False}

    monkeypatch.setattr(socket, "getaddrinfo", real_getaddrinfo)
    with socket.create_server(("localhost", 0)) as server:
        port = server.getsockname()[1]
        assert portal_server._tcp_port_open("localhost", port, budget_seconds=2.0) is True
