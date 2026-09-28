from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orama_system.knowledge_gateway import _search_docs, router

pytestmark = pytest.mark.unit

_MCP_HEADERS = {
    "Mcp-Protocol-Version": "2026-07-28",
    "Mcp-Method": "tools/call",
    "Mcp-Name": "search_docs",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "guide.md").write_text(
        "# Human Approval\nThe Amplifier Principle requires a human gate.",
        encoding="utf-8",
    )
    (tmp_path / "deploiement.md").write_text(
        "# Déploiement\nLe déploiement Nêxtwork est documenté ici.",
        encoding="utf-8",
    )
    monkeypatch.setenv("ORAMA_DOCS_ROOT", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=True)


def test_end_user_search(client):
    response = client.get("/api/knowledge/search?q=human%20gate")
    assert response.status_code == 200
    assert response.json()["hits"][0]["path"] == "guide.md"
    assert response.json()["read_only"] is True


def test_mcp_initialize_and_tools_list(client):
    init = client.post(
        "/api/mcp",
        headers={"Mcp-Protocol-Version": "2026-07-28", "Mcp-Method": "initialize"},
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
    )
    assert init.status_code == 200
    assert init.json()["result"]["protocolVersion"] == "2026-07-28"

    listed = client.post(
        "/api/mcp",
        headers={"Mcp-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/list"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert listed.json()["result"]["tools"][0]["name"] == "search_docs"
    assert listed.json()["result"]["tools"][0]["annotations"]["readOnlyHint"] is True
    assert listed.json()["result"]["tools"][0]["inputSchema"]["properties"]["query"]["maxLength"] == 200


def test_mcp_server_discover(client):
    discovered = client.post(
        "/api/mcp",
        headers={"Mcp-Protocol-Version": "2026-07-28", "Mcp-Method": "server/discover"},
        json={"jsonrpc": "2.0", "id": "discover-1", "method": "server/discover", "params": {}},
    )
    assert discovered.status_code == 200
    result = discovered.json()["result"]
    assert result["protocolVersion"] == "2026-07-28"
    assert result["serverInfo"] == {"name": "orama-knowledge", "version": "1.0.0"}
    assert result["capabilities"] == {"tools": {"listChanged": False}}


def test_mcp_search_requires_current_headers(client):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search_docs", "arguments": {"query": "Amplifier"}},
    }
    missing = client.post("/api/mcp", json=payload)
    assert missing.json()["error"]["code"] == -32600

    response = client.post("/api/mcp", headers=_MCP_HEADERS, json=payload)
    assert response.status_code == 200
    assert response.json()["result"]["structuredContent"]["hits"][0]["path"] == "guide.md"


def test_a2a_discovery_and_direct_message(client):
    card = client.get("/.well-known/agent-card.json").json()
    assert card["skills"][0]["id"] == "search-docs"
    response = client.post(
        "/api/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "a2a-1",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "m-1",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Amplifier Principle"}],
                }
            },
        },
    )
    assert response.json()["result"]["kind"] == "message"
    assert response.json()["result"]["parts"][0]["data"]["hits"]


def test_mcp_initialized_notification_returns_202(client):
    response = client.post(
        "/api/mcp",
        headers={"Mcp-Protocol-Version": "2026-07-28", "Mcp-Method": "notifications/initialized"},
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert response.status_code == 202
    assert response.content == b""


def test_accented_query_matches_folded_docs(client):
    response = client.get("/api/knowledge/search?q=deploiement")
    assert response.status_code == 200
    assert response.json()["hits"][0]["path"] == "deploiement.md"
    assert "Déploiement" in response.json()["hits"][0]["excerpt"]


def test_excerpt_centers_on_late_match(tmp_path, monkeypatch):
    prefix = "Opening prose. " * 40
    body = f"# Intro\n{prefix}Accented Déploiement UNIQUE_NEEDLE sits far from the opening.\n"
    (tmp_path / "late.md").write_text(body, encoding="utf-8")
    monkeypatch.setenv("ORAMA_DOCS_ROOT", str(tmp_path))
    hits = _search_docs("UNIQUE_NEEDLE")
    excerpt = hits[0]["excerpt"]
    leading = " ".join(body.split())[:280]
    assert hits[0]["path"] == "late.md"
    assert "UNIQUE_NEEDLE" in excerpt
    assert excerpt != leading
    assert excerpt.startswith("…")
    assert "Déploiement" in excerpt


def test_knowledge_router_enforces_operator_token_without_portal_middleware(tmp_path, monkeypatch):
    (tmp_path / "guide.md").write_text("# Human Approval\nA human gate.", encoding="utf-8")
    monkeypatch.setenv("ORAMA_DOCS_ROOT", str(tmp_path))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-operator-bearer-not-a-real-secret")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, raise_server_exceptions=True) as isolated:
        denied = isolated.get("/api/knowledge/search?q=human")
        assert denied.status_code == 401
        allowed = isolated.get(
            "/api/knowledge/search?q=human",
            headers={"Authorization": "Bearer test-operator-bearer-not-a-real-secret"},
        )
    assert allowed.status_code == 200
    assert allowed.json()["hits"][0]["path"] == "guide.md"


def test_mcp_query_over_200_is_invalid_params(client):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search_docs", "arguments": {"query": "ab" + "x" * 199}},
    }
    response = client.post("/api/mcp", headers=_MCP_HEADERS, json=payload)
    assert response.json()["error"]["code"] == -32602


def test_a2a_non_string_text_part_is_invalid_params(client):
    response = client.post(
        "/api/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "a2a-bad",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "m-bad",
                    "role": "user",
                    "parts": [{"kind": "text", "text": 42}],
                }
            },
        },
    )
    assert response.json()["error"]["code"] == -32602


def test_a2a_query_over_200_is_invalid_params(client):
    response = client.post(
        "/api/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "a2a-long",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "m-long",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "ab" + "x" * 199}],
                }
            },
        },
    )
    assert response.json()["error"]["code"] == -32602


def test_mcp_malformed_json_returns_parse_error(client):
    response = client.post(
        "/api/mcp",
        headers={
            "Mcp-Protocol-Version": "2026-07-28",
            "Mcp-Method": "initialize",
            "Content-Type": "application/json",
        },
        content="{not-json",
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32700


def test_a2a_non_object_json_returns_invalid_request(client):
    response = client.post("/api/a2a", json=["not", "an", "object"])
    assert response.json()["error"]["code"] == -32600


def test_a2a_malformed_json_returns_parse_error(client):
    response = client.post(
        "/api/a2a",
        headers={"Content-Type": "application/json"},
        content="{not-json",
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32700


def test_knowledge_search_requires_bearer_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-operator-bearer-not-a-real-secret")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")

    import orama_system.portal_server as portal_server

    with TestClient(portal_server.app, raise_server_exceptions=False) as portal:
        denied = portal.get("/api/knowledge/search?q=human")
    assert denied.status_code == 401
