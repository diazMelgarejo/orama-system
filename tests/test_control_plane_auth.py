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
            "/oramasys",
            json={
                "task_description": "test task",
                "optimize_for": "speed",
                "task_type": "analysis",
            },
        )
        allowed = client.post(
            "/oramasys",
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


def test_auth_headers_discovers_pt_token_from_sibling_checkout(monkeypatch, tmp_path):
    """Portal must read PT token without PERPETUA_TOOLS_ROOT when repos are siblings."""
    from utils.control_plane_auth import auth_headers

    pt_root = tmp_path / "Perpetua-Tools"
    (pt_root / "orchestrator").mkdir(parents=True)
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("")
    token_path = pt_root / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("sibling-token", encoding="utf-8")

    monkeypatch.setattr(
        "utils.control_plane_auth._resolve_perpetua_tools_root",
        lambda: pt_root,
    )
    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "ORAMA_CONTROL_PLANE_TOKEN"):
        monkeypatch.delenv(key, raising=False)

    assert auth_headers() == {"Authorization": "Bearer sibling-token"}


def test_verify_accepts_pt_persisted_token_without_env(monkeypatch, tmp_path):
    from utils.control_plane_auth import resolved_control_plane_token, verify_control_plane_auth

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("pt-only-token", encoding="utf-8")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)

    class _Req:
        headers = {"authorization": "Bearer pt-only-token"}

    verify_control_plane_auth(_Req())
    assert resolved_control_plane_token() == "pt-only-token"


def test_portal_loopback_index_injects_cp_fetch_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "loopback-ui-token")

    async def _fake_status():
        return {"services": {}, "routing": None, "activity": [], "agents": []}

    monkeypatch.setattr(portal_server, "api_status", _fake_status)

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        allowed = client.get("/")
        api_denied = client.get("/api/status")
        api_allowed = client.get(
            "/api/status",
            headers={"Authorization": "Bearer loopback-ui-token"},
        )

    assert allowed.status_code == 200
    assert "cpFetch" in allowed.text
    assert "loopback-ui-token" in allowed.text
    assert api_denied.status_code == 401
    assert api_allowed.status_code == 200


def test_portal_index_requires_auth_when_not_loopback(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "loopback-ui-token")
    monkeypatch.setattr(
        "utils.control_plane_auth.request_is_loopback",
        lambda _request: False,
    )

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        denied = client.get("/")

    assert denied.status_code == 401


def test_pt_auth_module_available_in_sibling_checkout():
    pytest = __import__("pytest")
    from pathlib import Path

    pt_root = Path(__file__).resolve().parents[1].parent / "Perpetua-Tools"
    auth_module = pt_root / "orchestrator" / "control_plane_auth.py"
    if not auth_module.is_file():
        pytest.skip("Perpetua-Tools sibling checkout not present")
    assert "ORAMA_CONTROL_PLANE_TOKEN" in auth_module.read_text(encoding="utf-8")

