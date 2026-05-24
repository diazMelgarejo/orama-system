#!/usr/bin/env python3
"""Regression tests for control-plane authentication and redaction."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

import api_server
import portal_server


def test_portal_operator_routes_require_token_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        denied = client.get("/api/status")
        allowed = client.get(
            "/api/status",
            headers={"Authorization": "Bearer portal-test-token"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    body = allowed.json()
    assert "paths" not in str(body)
    assert "runtime" not in body.get("routing", {})


def test_portal_health_stays_public_when_enforced(monkeypatch):
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_server_ultrathink_requires_token_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "orama-test-token")

    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "ok", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=False) as client:
        denied = client.post(
            "/ultrathink",
            json={
                "task_description": "test task",
                "optimize_for": "speed",
                "task_type": "analysis",
            },
        )
        allowed = client.post(
            "/ultrathink",
            json={
                "task_description": "test task",
                "optimize_for": "speed",
                "task_type": "analysis",
            },
            headers={"Authorization": "Bearer orama-test-token"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_api_server_runtime_state_redacts_payload(monkeypatch, tmp_path):
    state_file = tmp_path / "routing.json"
    state_file.write_text(
        '{"gateway": {"gateway_ready": true, "paths": {"secret": "/tmp"}}, '
        '"routing": {"distributed": true, "backend_url": "http://secret"}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("PT_AGENTS_STATE", str(state_file))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "orama-test-token")

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.get(
            "/runtime-state",
            headers={"Authorization": "Bearer orama-test-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    runtime = body["runtime"]
    assert runtime["gateway_ready"] is True
    assert runtime["distributed"] is True
    assert "paths" not in runtime
    assert "backend_url" not in str(body)


def test_auth_enforced_matrix(monkeypatch):
    from utils.control_plane_auth import auth_enforced

    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    assert auth_enforced() is False

    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "secret")
    assert auth_enforced() is True

    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    assert auth_enforced() is False

    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    assert auth_enforced() is True


def test_auth_headers_reads_pt_persisted_token(monkeypatch, tmp_path):
    from utils.control_plane_auth import auth_headers

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("pt-file-token", encoding="utf-8")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)

    headers = auth_headers()

    assert headers == {"Authorization": "Bearer pt-file-token"}


def test_pt_auth_module_available_in_sibling_checkout():
    pytest = __import__("pytest")
    from pathlib import Path

    pt_root = Path(__file__).resolve().parents[1].parent / "Perpetua-Tools"
    auth_module = pt_root / "orchestrator" / "control_plane_auth.py"
    if not auth_module.is_file():
        pytest.skip("Perpetua-Tools sibling checkout not present")
    assert "ORAMA_CONTROL_PLANE_TOKEN" in auth_module.read_text(encoding="utf-8")
