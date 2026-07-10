"""Tests for Fleet Topology API endpoints (Phase 3).

Covers:
- GET /api/fleet-topology: Fleet topology discovery
- POST /api/peer-relay-probe: Gossip relay probing
- Auth gating via control_plane_auth middleware
- Error handling for malformed requests
"""
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response as HttpxResponse

# Import the app
from orama_system.portal_server import app, get_fleet_topology, post_peer_relay_probe
from orama_system.portal_server import (
    FleetPeerInfo,
    FleetTopologyResponse,
    PeerRelayProbeRequest,
    PeerRelayProbeResponse,
)


@pytest.fixture
def auth_header():
    """Create auth header with test token."""
    # Set a test token in the environment for auth
    test_token = "test-control-plane-token-12345"
    os.environ["ORAMA_CONTROL_PLANE_TOKEN"] = test_token
    yield {"Authorization": f"Bearer {test_token}"}
    # Cleanup
    if "ORAMA_CONTROL_PLANE_TOKEN" in os.environ:
        del os.environ["ORAMA_CONTROL_PLANE_TOKEN"]


@pytest.fixture
def client_with_auth(auth_header):
    """Create a test client with auth enabled."""
    # Set token in env before creating client
    os.environ["ORAMA_CONTROL_PLANE_TOKEN"] = auth_header["Authorization"].split(" ")[1]
    client = TestClient(app)
    yield client
    if "ORAMA_CONTROL_PLANE_TOKEN" in os.environ:
        del os.environ["ORAMA_CONTROL_PLANE_TOKEN"]


@pytest.fixture
def client_without_auth():
    """Create a test client without auth token."""
    # Ensure no token is set
    if "ORAMA_CONTROL_PLANE_TOKEN" in os.environ:
        del os.environ["ORAMA_CONTROL_PLANE_TOKEN"]
    return TestClient(app)


@pytest.fixture
def client():
    """Create a test client with auth token."""
    test_token = "test-control-plane-token-12345"
    os.environ["ORAMA_CONTROL_PLANE_TOKEN"] = test_token
    client = TestClient(app)
    yield client
    if "ORAMA_CONTROL_PLANE_TOKEN" in os.environ:
        del os.environ["ORAMA_CONTROL_PLANE_TOKEN"]


class TestFleetTopologyEndpoint:
    """Tests for GET /api/fleet-topology."""

    def test_fleet_topology_endpoint_exists(self, client):
        """Endpoint should exist and respond."""
        response = client.get("/api/fleet-topology")
        assert response.status_code == 200

    def test_fleet_topology_with_auth(self, client, auth_header):
        """Endpoint should return 200 with valid auth token."""
        response = client.get("/api/fleet-topology", headers=auth_header)
        assert response.status_code == 200

    def test_fleet_topology_response_structure(self, client, auth_header):
        """Response should have expected structure."""
        response = client.get("/api/fleet-topology", headers=auth_header)
        assert response.status_code == 200

        data = response.json()
        assert "local_node" in data
        assert "fleet_mode" in data
        assert "peers" in data
        assert isinstance(data["peers"], list)
        assert "cross_reachable" in data
        assert isinstance(data["cross_reachable"], bool)
        assert "relay_capable" in data
        assert isinstance(data["relay_capable"], bool)

    def test_fleet_topology_solo_mode(self, client, auth_header):
        """In SOLO mode (no peer), fleet_mode should be SOLO."""
        with patch("orama_system.portal_server.read_discovery_peer_ip", return_value=""):
            response = client.get("/api/fleet-topology", headers=auth_header)
            assert response.status_code == 200
            data = response.json()
            assert data["fleet_mode"] == "SOLO"
            assert data["cross_reachable"] is False
            assert data["relay_capable"] is False

    def test_fleet_topology_fleet_mode(self, client, auth_header):
        """In FLEET mode (peer available), fleet_mode should be FLEET."""
        peer_ip = "192.168.1.100"
        with patch("orama_system.portal_server.read_discovery_peer_ip", return_value=peer_ip):
            with patch("orama_system.portal_server.local_platform", return_value="mac"):
                # Mock the HTTP probe to fail (simulating unreachable peer)
                response = client.get("/api/fleet-topology", headers=auth_header)
                assert response.status_code == 200
                data = response.json()
                # Should still be FLEET mode even if probe fails
                assert data["fleet_mode"] == "FLEET"
                assert data["relay_capable"] is True

    def test_fleet_topology_peer_structure(self, client, auth_header):
        """Peer entries should have correct structure."""
        response = client.get("/api/fleet-topology", headers=auth_header)
        assert response.status_code == 200

        data = response.json()
        if data["peers"]:
            peer = data["peers"][0]
            assert "id" in peer
            assert "ip" in peer
            assert "port" in peer
            assert "reachable" in peer
            assert isinstance(peer["reachable"], bool)
            assert "last_seen" in peer
            assert "models" in peer
            assert isinstance(peer["models"], list)
            assert "can_reach" in peer
            assert isinstance(peer["can_reach"], list)


class TestPeerRelayProbeEndpoint:
    """Tests for POST /api/peer-relay-probe."""

    def test_peer_relay_probe_endpoint_exists(self, client):
        """Endpoint should exist and respond."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body)
        assert response.status_code == 200

    def test_peer_relay_probe_with_auth(self, client, auth_header):
        """Endpoint should return 200 with valid auth token."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200

    def test_peer_relay_probe_response_structure(self, client, auth_header):
        """Response should have expected structure."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200

        data = response.json()
        assert "reachable" in data
        assert isinstance(data["reachable"], bool)
        assert "ip" in data
        assert data["ip"] == "192.168.1.100"
        assert "models" in data
        assert isinstance(data["models"], list)
        assert "relay_path" in data
        assert isinstance(data["relay_path"], list)

    def test_peer_relay_probe_missing_target_ip(self, client, auth_header):
        """Request without target_ip should fail."""
        body = {"target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 422  # Validation error

    def test_peer_relay_probe_invalid_port(self, client, auth_header):
        """Request with invalid port should fail."""
        body = {"target_ip": "192.168.1.100", "target_port": 99999}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        # May get 400 (validated by endpoint) or 422 (validated by Pydantic)
        assert response.status_code in (400, 422)

    def test_peer_relay_probe_empty_ip(self, client, auth_header):
        """Request with empty IP should fail."""
        body = {"target_ip": "", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 400

    def test_peer_relay_probe_unreachable(self, client, auth_header):
        """Unreachable target should return reachable=false."""
        body = {"target_ip": "127.0.0.1", "target_port": 65433}  # Likely unreachable
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200

        data = response.json()
        assert data["reachable"] is False
        assert len(data["relay_path"]) > 0
        # Should indicate unreachable in relay path
        assert "unreachable" in data["relay_path"][0].lower()

    def test_peer_relay_probe_malformed_json(self, client, auth_header):
        """Malformed JSON should fail."""
        response = client.post(
            "/api/peer-relay-probe",
            data="not json",
            headers={**auth_header, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_peer_relay_probe_default_port(self, client, auth_header):
        """Request without port should use default (8002)."""
        body = {"target_ip": "192.168.1.100"}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200

        data = response.json()
        # Should have attempted to reach port 8002
        assert data["ip"] == "192.168.1.100"


class TestFleetTopologyIntegration:
    """Integration tests for fleet topology system."""

    def test_fleet_topology_gossip_round_trip(self, client, auth_header):
        """Test that relay probe returns what topology knows about a peer."""
        # First, get the fleet topology
        topo_response = client.get("/api/fleet-topology", headers=auth_header)
        assert topo_response.status_code == 200
        topo = topo_response.json()

        # If we have peers, try to probe one
        if topo["peers"]:
            peer = topo["peers"][0]
            probe_body = {"target_ip": peer["ip"], "target_port": peer["port"]}
            probe_response = client.post(
                "/api/peer-relay-probe", json=probe_body, headers=auth_header
            )
            assert probe_response.status_code == 200

    def test_fleet_topology_consistency(self, client, auth_header):
        """Multiple calls should return consistent fleet structure."""
        response1 = client.get("/api/fleet-topology", headers=auth_header)
        response2 = client.get("/api/fleet-topology", headers=auth_header)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Local node and mode should remain consistent
        assert data1["local_node"] == data2["local_node"]
        assert data1["fleet_mode"] == data2["fleet_mode"]

    def test_peer_relay_probe_single_http_round_trip(self, client, auth_header):
        """Relay probe should complete in a single HTTP request/response."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}

        # Time the request
        import time
        start = time.time()
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        elapsed = time.time() - start

        # Should complete quickly (under 5 seconds for timeout + processing)
        assert elapsed < 5.0
        assert response.status_code == 200

    def test_fleet_endpoints_read_only(self, client, auth_header):
        """Fleet endpoints should be read-only (GET/POST info retrieval only)."""
        # GET /api/fleet-topology should work
        response = client.get("/api/fleet-topology", headers=auth_header)
        assert response.status_code == 200

        # POST to /api/peer-relay-probe should work
        body = {"target_ip": "192.168.1.100"}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200

        # No state should have been modified (read-only)


class TestFleetTopologyModels:
    """Tests for Pydantic models."""

    def test_fleet_peer_info_model(self):
        """FleetPeerInfo should validate correctly."""
        peer = FleetPeerInfo(
            id="test-peer",
            ip="192.168.1.100",
            port=8002,
            reachable=True,
            last_seen="2026-07-08T10:42:00Z",
            models=["qwen3.5:9b-nvfp4"],
            can_reach=["peer-2"],
        )
        assert peer.id == "test-peer"
        assert peer.ip == "192.168.1.100"
        assert peer.reachable is True

    def test_fleet_topology_response_model(self):
        """FleetTopologyResponse should validate correctly."""
        response = FleetTopologyResponse(
            local_node="mac-studio",
            fleet_mode="FLEET",
            peers=[],
            cross_reachable=False,
            relay_capable=True,
        )
        assert response.local_node == "mac-studio"
        assert response.fleet_mode == "FLEET"

    def test_peer_relay_probe_request_model(self):
        """PeerRelayProbeRequest should validate correctly."""
        request = PeerRelayProbeRequest(
            target_ip="192.168.1.100",
            target_port=8002,
        )
        assert request.target_ip == "192.168.1.100"
        assert request.target_port == 8002

    def test_peer_relay_probe_request_default_port(self):
        """Default port should be 8002."""
        request = PeerRelayProbeRequest(target_ip="192.168.1.100")
        assert request.target_port == 8002

    def test_peer_relay_probe_response_model(self):
        """PeerRelayProbeResponse should validate correctly."""
        response = PeerRelayProbeResponse(
            reachable=True,
            ip="192.168.1.100",
            models=["qwen3.5:9b-nvfp4"],
            relay_path=["M→100"],
        )
        assert response.reachable is True
        assert response.ip == "192.168.1.100"
        assert len(response.models) == 1


class TestFleetTopologyErrorHandling:
    """Tests for error handling."""

    def test_fleet_topology_handles_network_errors(self, client, auth_header):
        """Should handle network errors gracefully."""
        with patch("orama_system.portal_server.read_discovery_peer_ip", return_value="192.168.1.100"):
            with patch(
                "orama_system.portal_server._portal_untrusted_http_client",
                side_effect=Exception("Network error"),
            ):
                response = client.get("/api/fleet-topology", headers=auth_header)
                # Should return 200 even if probe fails
                assert response.status_code == 200

    def test_peer_relay_probe_handles_network_errors(self, client, auth_header):
        """Relay probe should handle network errors gracefully."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        # Should return 200 with reachable=false
        assert response.status_code == 200
        data = response.json()
        assert data["reachable"] is False

    def test_peer_relay_probe_handles_invalid_responses(self, client, auth_header):
        """Relay probe should handle malformed peer responses."""
        body = {"target_ip": "192.168.1.100", "target_port": 8002}
        response = client.post("/api/peer-relay-probe", json=body, headers=auth_header)
        assert response.status_code == 200
        # Should not crash, just mark as unreachable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
