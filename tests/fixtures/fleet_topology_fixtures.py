"""Fixtures for fleet topology testing (Phase 4).

Mock peer responses, topology states, and transition scenarios for
end-to-end coord_pulse integration testing.

Reference: orama-system/tests/test_coord_pulse_integration.py
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock Peer Topology Responses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def mock_peer_solo_response() -> Dict[str, Any]:
    """Mock response from peer in SOLO mode (no other peers visible)."""
    return {
        "local_node": "win-rtx3080",
        "fleet_mode": "SOLO",
        "peers": [],
        "cross_reachable": False,
        "relay_capable": False,
        "timestamp": time.time(),
    }


def mock_peer_pair_response() -> Dict[str, Any]:
    """Mock response from peer in PAIR mode (one peer visible)."""
    return {
        "local_node": "win-rtx3080",
        "fleet_mode": "PAIR",
        "peers": [
            {
                "id": "win-rtx5080",
                "ip": "192.168.1.102",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": ["mac-studio"],
            }
        ],
        "cross_reachable": False,
        "relay_capable": True,
        "timestamp": time.time(),
    }


def mock_peer_fleet_response() -> Dict[str, Any]:
    """Mock response from peer in FLEET mode (multiple cross-reachable peers)."""
    return {
        "local_node": "win-rtx3080",
        "fleet_mode": "FLEET",
        "peers": [
            {
                "id": "win-rtx5080",
                "ip": "192.168.1.102",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": ["mac-studio", "mac-mini"],
            },
            {
                "id": "mac-mini",
                "ip": "192.168.1.103",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": ["win-rtx5080"],
            },
        ],
        "cross_reachable": True,
        "relay_capable": True,
        "timestamp": time.time(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mac Local Topology Snapshots
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def mac_local_topology_solo() -> Dict[str, Any]:
    """Mac's local topology view in SOLO mode."""
    return {
        "local_node": "mac-studio",
        "fleet_mode": "SOLO",
        "peers": [],
        "cross_reachable": False,
        "relay_capable": False,
        "timestamp": time.time(),
    }


def mac_local_topology_pair() -> Dict[str, Any]:
    """Mac's local topology view in PAIR mode (1 peer reachable)."""
    return {
        "local_node": "mac-studio",
        "fleet_mode": "PAIR",
        "peers": [
            {
                "id": "win-rtx3080",
                "ip": "192.168.1.101",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": [],
            }
        ],
        "cross_reachable": False,
        "relay_capable": True,
        "timestamp": time.time(),
    }


def mac_local_topology_fleet() -> Dict[str, Any]:
    """Mac's local topology view in FLEET mode (multiple cross-reachable peers)."""
    return {
        "local_node": "mac-studio",
        "fleet_mode": "FLEET",
        "peers": [
            {
                "id": "win-rtx3080",
                "ip": "192.168.1.101",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": ["win-rtx5080"],
            },
            {
                "id": "win-rtx5080",
                "ip": "192.168.1.102",
                "port": 8002,
                "reachable": True,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "models": ["qwen3.5:9b-nvfp4"],
                "can_reach": ["win-rtx3080"],
            },
        ],
        "cross_reachable": True,
        "relay_capable": True,
        "timestamp": time.time(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mode Transition Scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ModeTransitionScenario:
    """Represents a sequence of fleet mode transitions."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.transitions = []

    def add_transition(
        self,
        old_mode: str,
        new_mode: str,
        peer_count: int,
        cross_reachable: bool,
    ):
        """Add a transition step to the scenario."""
        self.transitions.append(
            {
                "old_mode": old_mode,
                "new_mode": new_mode,
                "peer_count": peer_count,
                "cross_reachable": cross_reachable,
            }
        )

    def to_json(self) -> str:
        """Serialize scenario to JSON."""
        return json.dumps(
            {
                "name": self.name,
                "description": self.description,
                "transitions": self.transitions,
            }
        )


# Scenario 1: Peer discovery (SOLO → PAIR → FLEET)
peer_discovery_scenario = ModeTransitionScenario(
    name="peer-discovery",
    description="Progressive peer discovery from SOLO to FLEET",
)
peer_discovery_scenario.add_transition("SOLO", "PAIR", 1, False)
peer_discovery_scenario.add_transition("PAIR", "FLEET", 2, True)

# Scenario 2: Peer failure (FLEET → PAIR → SOLO)
peer_failure_scenario = ModeTransitionScenario(
    name="peer-failure",
    description="Progressive peer loss from FLEET to SOLO",
)
peer_failure_scenario.add_transition("FLEET", "PAIR", 1, False)
peer_failure_scenario.add_transition("PAIR", "SOLO", 0, False)

# Scenario 3: Network partition (FLEET → PAIR, then recovery)
network_partition_scenario = ModeTransitionScenario(
    name="network-partition",
    description="Mesh partition and recovery",
)
network_partition_scenario.add_transition("FLEET", "PAIR", 1, False)
network_partition_scenario.add_transition("PAIR", "FLEET", 2, True)

# Scenario 4: Stable topology (FLEET → FLEET)
stable_topology_scenario = ModeTransitionScenario(
    name="stable-topology",
    description="Stable FLEET mode with peer changes",
)
stable_topology_scenario.add_transition("FLEET", "FLEET", 3, True)
stable_topology_scenario.add_transition("FLEET", "FLEET", 2, True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gossip Event Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_topology_transition_event(
    old_mode: str,
    new_mode: str,
    peer_count: int,
    cross_reachable: bool,
) -> Dict[str, Any]:
    """Create a fleet_topology_transition gossip event."""
    return {
        "event_type": "fleet_topology_transition",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "old_mode": old_mode,
        "new_mode": new_mode,
        "peer_count": peer_count,
        "cross_reachable": cross_reachable,
        "source_node": "mac-studio",
    }


def create_gossip_event_log_entry(
    event_type: str,
    data: Dict[str, Any],
) -> str:
    """Create a JSONL gossip event log entry."""
    entry = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    return json.dumps(entry)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Error Response Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def malformed_peer_response() -> Dict[str, Any]:
    """Intentionally malformed peer response."""
    return {
        "invalid": "structure",
        "missing_required": "fields",
    }


def peer_network_error() -> Dict[str, Any]:
    """Simulated network error response."""
    return {
        "error": "Network timeout",
        "status": "unreachable",
        "retry_after": 30,
    }


def peer_auth_error() -> Dict[str, Any]:
    """Simulated auth error response."""
    return {
        "error": "Unauthorized",
        "status": 401,
        "message": "Invalid control plane token",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Topology Merge Test Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TopologyMergeTestCase:
    """Represents a topology merge test scenario."""

    def __init__(
        self,
        name: str,
        mac_local: Dict[str, Any],
        peer_responses: List[Dict[str, Any]],
        expected_mode: str,
        expected_peer_count: int,
        expected_cross_reachable: bool,
    ):
        self.name = name
        self.mac_local = mac_local
        self.peer_responses = peer_responses
        self.expected_mode = expected_mode
        self.expected_peer_count = expected_peer_count
        self.expected_cross_reachable = expected_cross_reachable


# Test case 1: Single reachable peer
single_peer_merge = TopologyMergeTestCase(
    name="single-reachable-peer",
    mac_local=mac_local_topology_solo(),
    peer_responses=[mock_peer_solo_response()],
    expected_mode="PAIR",
    expected_peer_count=1,
    expected_cross_reachable=False,
)

# Test case 2: Multiple cross-reachable peers
multi_peer_merge = TopologyMergeTestCase(
    name="multi-reachable-peers",
    mac_local=mac_local_topology_pair(),
    peer_responses=[mock_peer_fleet_response()],
    expected_mode="FLEET",
    expected_peer_count=2,
    expected_cross_reachable=True,
)

# Test case 3: All peers unreachable
no_peer_merge = TopologyMergeTestCase(
    name="no-reachable-peers",
    mac_local=mac_local_topology_solo(),
    peer_responses=[],
    expected_mode="SOLO",
    expected_peer_count=0,
    expected_cross_reachable=False,
)
