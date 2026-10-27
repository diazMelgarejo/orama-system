"""Regression coverage for durable self-migration retry scheduling."""
from __future__ import annotations

import importlib.util
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit


ROOT = Path(__file__).resolve().parents[1]
DISCOVER_SCRIPT = ROOT / "scripts" / "discover.py"


def _load_discover() -> ModuleType:
    """Load an isolated discover module for scheduler tests."""
    spec = importlib.util.spec_from_file_location("discover_migration_retry_test", DISCOVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cached_discovery_retries_pending_migration_before_cache_return(tmp_path: Path) -> None:
    """A warm cached run still retries durable migration delivery."""
    discover = _load_discover()
    discover.DISCOVERY_JSON = tmp_path / "discovery.json"
    discover.DISCOVERY_JSON.write_text(
        '{"timestamp": "' + datetime.now(timezone.utc).isoformat() + '"}',
        encoding="utf-8",
    )
    retries: list[None] = []

    class NoLock:
        """No-op lock for an isolated cached-return test."""

        def __enter__(self) -> "NoLock":
            """Enter the no-op lock."""
            assert retries == [None]
            return self

        def __exit__(self, *_: object) -> bool:
            """Exit the no-op lock without suppressing errors."""
            return False

    discover._Lock = NoLock
    discover._retry_pending_self_migration = lambda: retries.append(None)

    assert discover.run_discovery(force=False, cached=True) == 0
    assert retries == [None]


@pytest.mark.parametrize("topology_changed", [False, True])
def test_watch_poll_retries_pending_migration(
    monkeypatch: pytest.MonkeyPatch,
    topology_changed: bool,
) -> None:
    """Every poll retries once; only changed topology invokes full discovery."""
    discover = _load_discover()
    retries: list[None] = []
    discovery_runs: list[dict[str, bool]] = []

    class OnePollEvent:
        """Allow exactly one watch-loop iteration."""

        def __init__(self) -> None:
            """Initialize the polling counter."""
            self.wait_calls = 0

        def wait(self, timeout: float | None = None) -> bool:
            """Return false once, then end the watch loop."""
            del timeout
            self.wait_calls += 1
            return self.wait_calls > 1

        def set(self) -> None:
            """Provide the event interface used by the signal handler."""

        def clear(self) -> None:
            """Provide the event interface used by the scutil listener."""

        def is_set(self) -> bool:
            """Report that the test event remains unset."""
            return False

    class NoStartThread:
        """Prevent the macOS listener from running during this unit test."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            """Accept the production thread constructor arguments."""
            del args, kwargs

        def start(self) -> None:
            """Leave the background listener inactive."""

    monkeypatch.setattr(threading, "Event", OnePollEvent)
    monkeypatch.setattr(threading, "Thread", NoStartThread)
    monkeypatch.setattr(signal, "signal", lambda *_: None)
    discover._retry_pending_self_migration = lambda: retries.append(None)
    discover.run_discovery = lambda **kwargs: discovery_runs.append(kwargs) or 0
    discover._load_json = lambda _: None
    addresses = iter(["", "changed", "changed"] if topology_changed else ["", ""])
    discover._mac_lan_ip = lambda: next(addresses)
    discover._query_peer_topology_on_change = lambda: None

    discover._watch_loop(interval=0)

    assert retries == [None]
    expected = [{"force": True, "cached": False, "retry_self_migration": False}]
    assert discovery_runs == (expected if topology_changed else [])


def test_retry_failure_is_logged_without_aborting_discovery(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed delivery remains observable without terminating the watch loop."""
    discover = _load_discover()

    def fail() -> None:
        """Simulate an unavailable identity store."""
        raise OSError("synthetic unavailable identity")

    monkeypatch.setattr(discover, "check_and_announce_self_migration", fail)
    discover._retry_pending_self_migration()
    assert "self IP migration announcement failed" in caplog.text
