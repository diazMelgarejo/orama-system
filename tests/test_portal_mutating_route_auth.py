#!/usr/bin/env python3
"""Regression: mutating portal routes deny unauthenticated access when auth is enforced."""
from __future__ import annotations

from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server


def _auth_client(token: str = "portal-route-test-token") -> TestClient:
    return TestClient(portal_server.app, raise_server_exceptions=False)


def _enforce_auth(monkeypatch, token: str = "portal-route-test-token") -> None:
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", token)
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")


def test_spawn_agent_requires_bearer_when_enforced(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        denied = client.post(
            "/api/spawn-agent",
            json={"agent": "codex", "task": "echo test"},
        )
        allowed = client.post(
            "/api/spawn-agent",
            json={"agent": "codex", "task": "echo test"},
            headers={"Authorization": "Bearer portal-route-test-token"},
        )
    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_configure_tool_requires_bearer_when_enforced(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        denied = client.post(
            "/api/configure-tool",
            json={"env_var": "GITHUB_TOKEN", "value": "test-configure-tool-placeholder"},
        )
    assert denied.status_code == 401


def test_swarm_launch_requires_bearer_when_enforced(monkeypatch):
    _enforce_auth(monkeypatch)

    async def fake_preview(req):
        return {
            "objective": req.objective,
            "task_type": req.task_type,
            "optimize_for": req.optimize_for,
            "preferred_device": req.preferred_device,
            "assignments": [],
            "hardware_policy": {"ok": True, "violations": []},
        }

    monkeypatch.setattr(portal_server, "_build_swarm_preview", fake_preview)
    with _auth_client() as client:
        denied = client.post(
            "/api/swarm/launch",
            json={"objective": "test", "approved": True},
        )
    assert denied.status_code == 401


def test_stop_and_restart_require_bearer_when_enforced(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        stop_denied = client.post("/api/stop")
        restart_denied = client.post("/api/restart/portal")
    assert stop_denied.status_code == 401
    assert restart_denied.status_code == 401


def test_job_detail_requires_bearer_when_enforced(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        denied = client.get("/api/jobs/00000000-0000-4000-8000-000000000001")
    assert denied.status_code == 401


def test_portal_http_clients_split_trust_boundary(monkeypatch):
    """Trusted client carries bearer; untrusted model-probe client does not."""
    _enforce_auth(monkeypatch)
    trusted = portal_server._portal_trusted_http_client()
    untrusted = portal_server._portal_untrusted_http_client()
    assert trusted.headers.get("Authorization", "").startswith("Bearer ")
    assert not untrusted.headers.get("Authorization")
