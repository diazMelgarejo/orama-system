#!/usr/bin/env python3
"""/api/status latency: CLI version checks are cached and overlap the network probes."""
from __future__ import annotations

import asyncio
import subprocess
import time
from types import SimpleNamespace

import pytest

from orama_system import portal_server

DELAY = 0.4


@pytest.fixture(autouse=True)
def _fresh_cli_cache():
    """Start and end every test with an empty CLI version cache."""
    getattr(portal_server, "_cli_version_cache", {}).clear()
    yield
    getattr(portal_server, "_cli_version_cache", {}).clear()


def test_cli_version_runs_each_binary_once_within_the_ttl(monkeypatch):
    """Repeated status polls reuse a CLI's --version result instead of relaunching it."""
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        """Record the launch and report a healthy CLI."""
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout=b"tool 1.2.3\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    first = portal_server._cli_version("/fake/bin/tool")
    second = portal_server._cli_version("/fake/bin/tool")

    assert first == second == (0, "tool 1.2.3\n")
    assert calls == [["/fake/bin/tool", "--version"]]


def test_cli_version_caches_a_failed_launch_and_expires(monkeypatch):
    """A CLI that times out is not relaunched on every poll, but is retried after the TTL."""
    calls: list[str] = []

    def fake_run(argv, **kwargs):
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


def test_status_payload_overlaps_tool_checks_and_ollama_ps_with_network_probes(monkeypatch):
    """Tool checks, the Ollama ps probe and the other probes run concurrently, not in sequence."""

    async def slow(result):
        """Return *result* after the shared probe delay."""
        await asyncio.sleep(DELAY)
        return result

    def slow_tools():
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


def test_tcp_port_open_detects_a_listening_port():
    """A real loopback listener is reported open."""
    import socket

    with socket.create_server(("localhost", 0)) as server:
        port = server.getsockname()[1]
        assert portal_server._tcp_port_open("localhost", port, budget_seconds=1.0) is True


def test_tcp_port_open_shares_one_budget_across_resolved_addresses(monkeypatch):
    """Two unreachable addresses cost one budget in total, not one budget each."""
    import socket

    budget = 0.3
    addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.1", 9)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.2", 9)),
    ]

    class HangingSocket:
        """Socket stand-in whose connect waits out its timeout, like a dropped SYN."""

        def __init__(self, *args):
            """Accept the family/type/proto arguments and start with no timeout."""
            self.timeout = None

        def __enter__(self):
            """Support use as a context manager."""
            return self

        def __exit__(self, *exc):
            """Nothing to close."""
            return False

        def settimeout(self, value):
            """Remember the per-attempt timeout."""
            self.timeout = value

        def connect(self, addr):
            """Block for the remaining timeout, then fail."""
            time.sleep(self.timeout)
            raise socket.timeout("timed out")

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrs)
    monkeypatch.setattr(socket, "socket", HangingSocket)

    started = time.perf_counter()
    assert portal_server._tcp_port_open("example.test", 9, budget_seconds=budget) is False
    assert time.perf_counter() - started < 1.5 * budget


def test_tcp_port_open_reaches_a_live_second_address_after_a_dead_first(monkeypatch):
    """A dead first address must not use up the budget the live one needs."""
    import socket

    addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.1", 9)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.0.2.2", 9)),
    ]

    class FirstDeadSocket:
        """Socket stand-in: the first address hangs out its timeout, the second accepts."""

        def __init__(self, *args):
            """Start with no timeout."""
            self.timeout = None

        def __enter__(self):
            """Support use as a context manager."""
            return self

        def __exit__(self, *exc):
            """Nothing to close."""
            return False

        def settimeout(self, value):
            """Remember the per-attempt timeout."""
            self.timeout = value

        def connect(self, addr):
            """Hang on the first address; connect instantly to the second."""
            if addr == addrs[0][4]:
                time.sleep(self.timeout)
                raise socket.timeout("timed out")

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrs)
    monkeypatch.setattr(socket, "socket", FirstDeadSocket)

    assert portal_server._tcp_port_open("example.test", 9, budget_seconds=0.4) is True
