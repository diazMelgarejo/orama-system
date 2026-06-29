#!/usr/bin/env python3
"""Tests for stateless swarm preview generation."""
from __future__ import annotations

from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeRouteClient:
    fail = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json=None, **kwargs):
        if self.fail:
            raise RuntimeError("route unavailable")
        return _FakeResponse({
            "backend_hint": f"pt-{json['role']}",
            "model_hint": "model-for-preview",
        })


def _portal_status():
    return {
        "hardware_policy": {
            "ok": True,
            "violations": [],
            "safe_defaults": {
                "mac": ["mac-model"],
                "win": ["win-model"],
            },
        }
    }


def _preview_auth(monkeypatch):
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "swarm-preview-test-token")
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")


def _auth_headers():
    return {"Authorization": "Bearer swarm-preview-test-token"}


def test_swarm_preview_returns_worker_assignments(monkeypatch):
    _preview_auth(monkeypatch)
    async def fake_api_status():
        return _portal_status()

    monkeypatch.setattr(portal_server, "api_status", fake_api_status)
    _FakeRouteClient.fail = False
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Ship app state"}, headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["dispatch_allowed"] is False
    assert [item["role"] for item in body["assignments"]] == [
        "context-agent",
        "architect-agent",
        "executor-agent",
        "verifier-agent",
        "crystallizer-agent",
    ]
    assert all(item["dispatch_allowed"] is False for item in body["assignments"])


def test_swarm_preview_rejects_empty_objective(monkeypatch):
    _preview_auth(monkeypatch)
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "   "}, headers=_auth_headers())

    assert response.status_code == 422


def test_swarm_preview_includes_backend_hints(monkeypatch):
    _preview_auth(monkeypatch)
    async def fake_api_status():
        return _portal_status()

    monkeypatch.setattr(portal_server, "api_status", fake_api_status)
    _FakeRouteClient.fail = False
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Review contracts"}, headers=_auth_headers())

    assert response.status_code == 200
    first = response.json()["assignments"][0]
    assert first["backend_hint"] == "pt-context-agent"
    assert first["model_hint"] == "model-for-preview"
    assert first["routing_source"] == "pt:/models/route"


def test_swarm_preview_marks_routing_fallback(monkeypatch):
    _preview_auth(monkeypatch)
    async def fake_api_status():
        return _portal_status()

    monkeypatch.setattr(portal_server, "api_status", fake_api_status)
    _FakeRouteClient.fail = True
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Review contracts"}, headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["routing_source"] == "portal:fallback"
    assert {item["routing_source"] for item in body["assignments"]} == {"portal:fallback"}
    assert all(item["backend_hint"] for item in body["assignments"])


def test_swarm_preview_returns_approval_tokens(monkeypatch):
    _preview_auth(monkeypatch)

    async def fake_api_status():
        return _portal_status()

    monkeypatch.setattr(portal_server, "api_status", fake_api_status)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Ship signed preview"}, headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["preview_id"]
    assert body["approval_token"]
    assert body["expires_at"].endswith("Z")


def test_swarm_preview_signing_round_trip(monkeypatch):
    from utils.control_plane_auth import verify_operator_payload

    _preview_auth(monkeypatch)

    async def fake_api_status():
        return _portal_status()

    monkeypatch.setattr(portal_server, "api_status", fake_api_status)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/preview",
            json={
                "objective": "Verify token",
                "task_type": "implementation",
                "optimize_for": "reliability",
                "preferred_device": "auto",
            },
            headers=_auth_headers(),
        )

    body = response.json()
    payload = {
        "preview_id": body["preview_id"],
        "objective": body["objective"],
        "task_type": body["task_type"],
        "optimize_for": body["optimize_for"],
        "preferred_device": body["preferred_device"],
        "assignments_hash": portal_server._swarm_assignments_hash(body["assignments"]),
    }
    assert verify_operator_payload(payload, body["approval_token"], body["expires_at"])


def test_swarm_assignments_hash_is_stable(monkeypatch):
    assignments = [
        {"role": "context-agent", "backend_hint": "pt-context-agent", "dispatch_allowed": False},
        {"role": "architect-agent", "backend_hint": "pt-architect-agent", "dispatch_allowed": False},
    ]
    first = portal_server._swarm_assignments_hash(assignments)
    second = portal_server._swarm_assignments_hash(assignments)
    assert first == second
    assert len(first) == 64
