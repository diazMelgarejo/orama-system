#!/usr/bin/env python3
"""Tests for stateless swarm preview generation."""
from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server


class _FakeResponse:
    """Minimal httpx response stub for swarm preview route tests."""

    def __init__(self, payload, status_code: int = 200):
        """Initialize the test double."""
        self._payload = payload
        self.status_code = status_code

    def json(self):
        """Return the JSON body."""
        return self._payload

    def raise_for_status(self):
        """Raise when the HTTP status indicates failure."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeRouteClient:
    """Shared recorder for swarm-preview route posts."""

    fail = False
    posts: ClassVar[list] = []

    def __init__(self, *args, **kwargs):
        """Initialize the test double."""
        pass

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager."""
        return False

    async def post(self, url: str, json=None, **kwargs):
        """Handle a POST request in the fake client."""
        self.posts.append(json)
        if self.fail:
            raise RuntimeError("route unavailable")
        return _FakeResponse({
            "backend_hint": f"pt-{json['role']}",
            "model_hint": "model-for-preview",
        })


def _portal_status():
    """Support  portal status."""
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


def _patch_hardware_policy(monkeypatch):
    """Stub hardware probes so preview tests do not call live LM Studio endpoints."""

    async def fake_hardware_policy():
        """Return the default ok hardware_policy snapshot used by preview routes."""
        return _portal_status()["hardware_policy"]

    monkeypatch.setattr(
        portal_server,
        "_portal_hardware_policy_snapshot",
        fake_hardware_policy,
    )


def test_swarm_preview_returns_worker_assignments(monkeypatch):
    """Preview includes routed worker assignments for each swarm role."""
    _patch_hardware_policy(monkeypatch)
    _FakeRouteClient.fail = False
    _FakeRouteClient.posts = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Ship app state"})

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


def test_swarm_preview_rejects_empty_objective():
    """Verify swarm preview rejects empty objective."""
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "   "})

    assert response.status_code == 422


def test_swarm_preview_includes_backend_hints(monkeypatch):
    """Verify swarm preview includes backend hints."""
    _patch_hardware_policy(monkeypatch)
    _FakeRouteClient.fail = False
    _FakeRouteClient.posts = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Review contracts"})

    assert response.status_code == 200
    first = response.json()["assignments"][0]
    assert first["backend_hint"] == "pt-context-agent"
    assert first["model_hint"] == "model-for-preview"
    assert first["routing_source"] == "pt:/models/route"
    posted = {item["role"]: item["specialization"] for item in _FakeRouteClient.posts}
    assert posted["context-agent"] == "codebase-map"
    assert posted["executor-agent"] == "code-change"
    assert all("specialization" in item for item in _FakeRouteClient.posts)


def test_swarm_preview_marks_routing_fallback(monkeypatch):
    """Verify swarm preview marks routing fallback."""
    _patch_hardware_policy(monkeypatch)
    _FakeRouteClient.fail = True
    _FakeRouteClient.posts = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Review contracts"})

    assert response.status_code == 200
    body = response.json()
    assert body["routing_source"] == "portal:fallback"
    assert {item["routing_source"] for item in body["assignments"]} == {"portal:fallback"}
    assert all(item["backend_hint"] for item in body["assignments"])


@pytest.mark.asyncio
async def test_swarm_preview_does_not_publish_status_notification(monkeypatch):
    """Preview must not publish api_status notifications (hardware snapshot only)."""
    _patch_hardware_policy(monkeypatch)
    _FakeRouteClient.fail = False
    _FakeRouteClient.posts = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeRouteClient)
    publish = AsyncMock()
    monkeypatch.setattr(portal_server._notification_publisher, "publish", publish)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/preview", json={"objective": "Review contracts"})

    assert response.status_code == 200
    publish.assert_not_called()
