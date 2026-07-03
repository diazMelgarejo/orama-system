#!/usr/bin/env python3
"""Regression tests for control-plane authentication and redaction."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

import orama_system.api_server as api_server
import orama_system.portal_server as portal_server


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


def test_peer_file_inbox_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")
    monkeypatch.setattr(
        "orama_system.lan_peer_files.lan_peer_state_dir",
        lambda: tmp_path / "lan_peer",
    )

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        denied = client.post(
            "/api/peer-file",
            json={"filename": "mac-task.md", "body": "# Mac task\n", "assignee": "mac"},
        )
        posted = client.post(
            "/api/peer-file",
            json={"filename": "mac-task.md", "body": "# Mac task\n", "assignee": "mac"},
            headers={"Authorization": "Bearer portal-test-token"},
        )
        listing = client.get(
            "/api/peer-inbox",
            headers={"Authorization": "Bearer portal-test-token"},
        )
        fetched = client.get(
            "/api/peer-inbox/mac-task.md",
            headers={"Authorization": "Bearer portal-test-token"},
        )

    assert denied.status_code == 401
    assert posted.status_code == 200
    assert listing.json()["files"]
    assert "Mac task" in fetched.json()["body"]


def test_peer_inbox_html_preview(monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")
    monkeypatch.setattr(
        "orama_system.lan_peer_files.lan_peer_state_dir",
        lambda: tmp_path / "lan_peer",
    )

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post(
            "/api/peer-file",
            json={"filename": "task.md", "body": "# Hello\n\n**peer**", "assignee": "mac"},
            headers={"Authorization": "Bearer portal-test-token"},
        )
        html_resp = client.get(
            "/api/peer-inbox/task.md/html",
            headers={"Authorization": "Bearer portal-test-token"},
        )
        page = client.get("/peer-inbox")

    assert html_resp.status_code == 200
    assert "<h1>Hello</h1>" in html_resp.json()["html"]
    assert page.status_code == 200
    assert "LAN peer inbox" in page.text
    assert "/api/peer-inbox" in page.text


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
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_LOCAL", raising=False)
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", raising=False)
    monkeypatch.delenv("PT_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    assert auth_enforced() is True

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


def test_portal_loopback_index_injects_cp_fetch_when_enforced(monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "loopback-ui-token")
    # Redirect _WEB_DIST to an empty tmp dir so the React FileResponse path is
    # skipped and the legacy HTML template (which injects cpFetch) is served.
    monkeypatch.setattr(portal_server, "_WEB_DIST", tmp_path)

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
    assert "loopback-ui-token" not in allowed.text
    assert "ORAMA_CP_TOKEN" not in allowed.text
    assert api_denied.status_code == 401
    assert api_allowed.status_code == 200


def test_portal_index_handles_redacted_agents_payload(monkeypatch, tmp_path):
    """index() must not 500 when api_status returns redacted agents wrapper dict."""
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    monkeypatch.setattr(portal_server, "_WEB_DIST", tmp_path)

    async def _fake_status():
        from utils.control_plane_auth import redact_portal_status_payload

        return redact_portal_status_payload(
            {
                "services": {"ollama_mac": {"ok": True, "busy": False}},
                "routing": None,
                "activity": [],
                "agents": [{"agent_id": "a1", "status": "idle", "role": "test"}],
                "tools": {},
                "queue_depth": 0,
                "hardware_policy": None,
                "supervisor_jobs": [],
            }
        )

    monkeypatch.setattr(portal_server, "api_status", _fake_status)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert "orama" in resp.text.lower() or "portal" in resp.text.lower()


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


def test_accept_peer_token_during_handoff(monkeypatch):
    from utils.control_plane_auth import (
        control_plane_auth_mode,
        token_matches_control_plane,
        verify_control_plane_auth,
    )

    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "mac-orama-token")
    monkeypatch.setenv("PT_CONTROL_PLANE_TOKEN", "win-pt-token")
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_LOCAL", raising=False)
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", raising=False)

    assert control_plane_auth_mode() == "joint"
    assert token_matches_control_plane("mac-orama-token", scope="orama")
    assert token_matches_control_plane("win-pt-token", scope="orama")
    assert token_matches_control_plane("win-pt-token", scope="pt")

    class _Req:
        headers = {"authorization": "Bearer win-pt-token"}

    verify_control_plane_auth(_Req())


def test_pt_only_rejects_orama_lane_key(monkeypatch, tmp_path):
    from utils.control_plane_auth import control_plane_auth_mode, token_matches_control_plane

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("pt-only-token", encoding="utf-8")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("PT_CONTROL_PLANE_TOKEN", raising=False)

    assert control_plane_auth_mode() == "pt_only"
    assert token_matches_control_plane("pt-only-token", scope="pt")
    assert not token_matches_control_plane("orama-other-token", scope="pt")


def test_outbound_prefers_peer_token(monkeypatch):
    from utils.control_plane_auth import outbound_control_plane_tokens, resolved_control_plane_token

    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "symmetric-token")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", "peer-only-token")

    assert outbound_control_plane_tokens()[0] == "peer-only-token"
    assert resolved_control_plane_token() == "peer-only-token"

