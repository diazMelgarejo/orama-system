"""
Tests for Fleet Status Display (Phase 5).

Covers:
- load_fleet_topology() from mock JSON
- format_banner() for each fleet mode
- format_json() for scripting
- format_text() for human reading
- Missing/malformed JSON handling
- Time-until-next-query calculation
- Peer info formatting with model names
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from orama_system.display_fleet_status import (
    load_fleet_topology,
    format_banner,
    format_json,
    format_text,
    get_time_until_next_query,
    FleetStatus,
    FleetPeer,
    get_fleet_topology_path,
    COORD_PULSE_INTERVAL_SEC,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def solo_fleet_json() -> dict:
    """Fleet topology JSON for SOLO mode."""
    now = datetime.now(timezone.utc).timestamp()
    return {
        "local_node": "mac-studio",
        "fleet_mode": "SOLO",
        "peers": [],
        "cross_reachable": False,
        "relay_capable": False,
        "timestamp": now,
    }


@pytest.fixture
def pair_fleet_json() -> dict:
    """Fleet topology JSON for PAIR mode."""
    now = datetime.now(timezone.utc).timestamp()
    return {
        "local_node": "mac-studio",
        "fleet_mode": "PAIR",
        "peers": [
            {
                "id": "win-rtx3080",
                "ip": "192.168.1.101",
                "port": 8002,
                "reachable": True,
                "models": ["qwen3.5-27b"],
                "last_seen": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "cross_reachable": False,
        "relay_capable": True,
        "timestamp": now,
    }


@pytest.fixture
def fleet_fleet_json() -> dict:
    """Fleet topology JSON for FLEET mode."""
    now = datetime.now(timezone.utc).timestamp()
    return {
        "local_node": "mac-studio",
        "fleet_mode": "FLEET",
        "peers": [
            {
                "id": "win-rtx3080",
                "ip": "192.168.1.101",
                "port": 8002,
                "reachable": True,
                "models": ["qwen3.5-27b"],
                "last_seen": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "win-rtx5080",
                "ip": "192.168.1.102",
                "port": 8002,
                "reachable": True,
                "models": ["gemma-4-26b"],
                "last_seen": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "cross_reachable": True,
        "relay_capable": True,
        "timestamp": now,
    }


@pytest.fixture
def temp_topology_file(solo_fleet_json) -> Path:
    """Create temporary fleet_topology.json file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(solo_fleet_json, f)
        path = Path(f.name)
    yield path
    path.unlink()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: load_fleet_topology
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLoadFleetTopology:
    """Tests for load_fleet_topology()."""

    def test_load_solo_mode(self, temp_topology_file, solo_fleet_json):
        """Should load SOLO mode topology correctly."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(solo_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            assert status is not None
            assert status.fleet_mode == "SOLO"
            assert len(status.peers) == 0
            assert status.cross_reachable is False
        finally:
            path.unlink()

    def test_load_pair_mode(self, pair_fleet_json):
        """Should load PAIR mode topology with one peer."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(pair_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            assert status is not None
            assert status.fleet_mode == "PAIR"
            assert len(status.peers) == 1
            assert status.peers[0].id == "win-rtx3080"
            assert status.peers[0].reachable is True
            assert "qwen3.5-27b" in status.peers[0].models
        finally:
            path.unlink()

    def test_load_fleet_mode(self, fleet_fleet_json):
        """Should load FLEET mode topology with multiple peers."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(fleet_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            assert status is not None
            assert status.fleet_mode == "FLEET"
            assert len(status.peers) == 2
            assert status.cross_reachable is True
            assert status.peers_reachable == 2
        finally:
            path.unlink()

    def test_load_missing_file(self):
        """Should return None if file doesn't exist."""
        status = load_fleet_topology(Path("/nonexistent/path/fleet_topology.json"))
        assert status is None

    def test_load_malformed_json(self):
        """Should return None if JSON is malformed."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json")
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            assert status is None
        finally:
            path.unlink()

    def test_load_missing_fields_safe_defaults(self):
        """Should handle missing fields with safe defaults."""
        incomplete_json = {
            "fleet_mode": "SOLO",
            "local_node": "test-node",
            # peers, cross_reachable, timestamp missing
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(incomplete_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            assert status is not None
            assert status.fleet_mode == "SOLO"
            assert len(status.peers) == 0
            assert status.cross_reachable is False
            assert status.timestamp == 0.0
        finally:
            path.unlink()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: format_banner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFormatBanner:
    """Tests for format_banner()."""

    def test_banner_solo_mode(self, solo_fleet_json):
        """Banner should display SOLO mode correctly."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(solo_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            banner = format_banner(status)
            assert "FLEET TOPOLOGY STATUS" in banner
            assert "SOLO" in banner
            assert "0/0 reachable" in banner
        finally:
            path.unlink()

    def test_banner_pair_mode(self, pair_fleet_json):
        """Banner should display PAIR mode correctly."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(pair_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            banner = format_banner(status)
            assert "PAIR" in banner
            assert "1/1 reachable" in banner
            assert "win-rtx3080" in banner
            assert "192.168.1.101" in banner
        finally:
            path.unlink()

    def test_banner_fleet_mode(self, fleet_fleet_json):
        """Banner should display FLEET mode with multiple peers."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(fleet_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            banner = format_banner(status)
            assert "FLEET" in banner
            assert "2/2 reachable" in banner
            assert "Cross-Reachable: YES" in banner
            assert "win-rtx3080" in banner
            assert "win-rtx5080" in banner
            assert "qwen3.5-27b" in banner
            assert "gemma-4-26b" in banner
        finally:
            path.unlink()

    def test_banner_none_status(self):
        """Banner should handle None status gracefully."""
        banner = format_banner(None)
        assert "FLEET TOPOLOGY STATUS" in banner
        assert "SOLO" in banner
        assert "Initializing" in banner


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: format_json
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFormatJson:
    """Tests for format_json()."""

    def test_json_output_structure(self, fleet_fleet_json):
        """JSON output should have expected structure."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(fleet_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            json_str = format_json(status)
            data = json.loads(json_str)

            assert "fleet_mode" in data
            assert "peers_reachable" in data
            assert "cross_reachable" in data
            assert "relay_capable" in data
            assert "peers" in data
            assert isinstance(data["peers"], list)
            assert "last_query" in data
            assert "next_query_in_seconds" in data
        finally:
            path.unlink()

    def test_json_peer_info(self, pair_fleet_json):
        """JSON should include peer details with models."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(pair_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            json_str = format_json(status)
            data = json.loads(json_str)

            assert len(data["peers"]) == 1
            peer = data["peers"][0]
            assert peer["id"] == "win-rtx3080"
            assert peer["ip"] == "192.168.1.101"
            assert peer["reachable"] is True
            assert "qwen3.5-27b" in peer["models"]
        finally:
            path.unlink()

    def test_json_none_status(self):
        """JSON should handle None status with safe defaults."""
        json_str = format_json(None)
        data = json.loads(json_str)

        assert data["fleet_mode"] == "UNKNOWN"
        assert data["peers_reachable"] == 0
        assert data["cross_reachable"] is False
        assert data["peers"] == []
        assert data["status"] == "unavailable"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: format_text
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFormatText:
    """Tests for format_text()."""

    def test_text_output_solo(self, solo_fleet_json):
        """Text output should display SOLO mode."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(solo_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            text = format_text(status)
            assert "SOLO" in text
            assert "0/0 peers reachable" in text
            assert "(no peers)" in text
        finally:
            path.unlink()

    def test_text_output_fleet(self, fleet_fleet_json):
        """Text output should display FLEET mode with peers."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(fleet_fleet_json, f)
            path = Path(f.name)

        try:
            status = load_fleet_topology(path)
            text = format_text(status)
            assert "FLEET" in text
            assert "2/2 peers reachable" in text
            assert "win-rtx3080" in text
            assert "win-rtx5080" in text
            assert "qwen3.5-27b" in text
            assert "gemma-4-26b" in text
        finally:
            path.unlink()

    def test_text_output_none_status(self):
        """Text output should handle None status."""
        text = format_text(None)
        assert "UNAVAILABLE" in text
        assert "fleet_topology.json" in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: get_time_until_next_query
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTimeUntilNextQuery:
    """Tests for get_time_until_next_query()."""

    def test_time_calculation_fresh(self):
        """Should calculate time correctly for fresh query."""
        now = datetime.now(timezone.utc).timestamp()
        status = FleetStatus(
            fleet_mode="SOLO",
            local_node="test",
            peers=[],
            cross_reachable=False,
            timestamp=now,
        )
        seconds = get_time_until_next_query(status)
        # Should be close to COORD_PULSE_INTERVAL_SEC (900)
        assert 890 <= seconds <= 900

    def test_time_calculation_stale(self):
        """Should calculate time correctly for stale query."""
        now = datetime.now(timezone.utc).timestamp()
        old_time = now - 600  # 10 minutes ago
        status = FleetStatus(
            fleet_mode="SOLO",
            local_node="test",
            peers=[],
            cross_reachable=False,
            timestamp=old_time,
        )
        seconds = get_time_until_next_query(status)
        # Should be ~300 (5 minutes remaining of 15 minute cycle)
        assert 290 <= seconds <= 310

    def test_time_calculation_overdue(self):
        """Should return 0 if next query is overdue."""
        now = datetime.now(timezone.utc).timestamp()
        old_time = now - 1000  # ~16 minutes ago (past the 15 minute mark)
        status = FleetStatus(
            fleet_mode="SOLO",
            local_node="test",
            peers=[],
            cross_reachable=False,
            timestamp=old_time,
        )
        seconds = get_time_until_next_query(status)
        assert seconds == 0

    def test_time_calculation_none_status(self):
        """Should return 0 for None status."""
        seconds = get_time_until_next_query(None)
        assert seconds == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: FleetStatus properties
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFleetStatusProperties:
    """Tests for FleetStatus dataclass properties."""

    def test_peers_reachable_count(self):
        """peers_reachable should count reachable peers."""
        peers = [
            FleetPeer("p1", "1.1.1.1", 8002, True, ["model1"], "2026-07-11T00:00:00Z"),
            FleetPeer("p2", "2.2.2.2", 8002, False, ["model2"], "2026-07-11T00:00:00Z"),
            FleetPeer("p3", "3.3.3.3", 8002, True, ["model3"], "2026-07-11T00:00:00Z"),
        ]
        status = FleetStatus(
            fleet_mode="FLEET",
            local_node="test",
            peers=peers,
            cross_reachable=True,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
        assert status.peers_reachable == 2

    def test_last_query_iso_format(self):
        """last_query_iso should return ISO8601 timestamp."""
        # Use current time so the test is stable
        now = datetime.now(timezone.utc).timestamp()
        status = FleetStatus(
            fleet_mode="SOLO",
            local_node="test",
            peers=[],
            cross_reachable=False,
            timestamp=now,
        )
        iso = status.last_query_iso
        assert "T" in iso
        assert "+" in iso or "Z" in iso  # ISO8601 timezone indicator

    def test_next_query_formatted(self):
        """next_query_formatted should return human-readable time."""
        now = datetime.now(timezone.utc).timestamp()
        status = FleetStatus(
            fleet_mode="SOLO",
            local_node="test",
            peers=[],
            cross_reachable=False,
            timestamp=now,
        )
        formatted = status.next_query_formatted
        assert "in" in formatted
        # Should contain 'm' for minutes since we're near a full cycle
        assert "m" in formatted or "s" in formatted
