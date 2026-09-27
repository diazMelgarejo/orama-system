from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orama_system.knowledge_gateway import router

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
    monkeypatch.setenv("ORAMA_DOCS_ROOT", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


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


def test_knowledge_search_requires_bearer_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-operator-bearer-not-a-real-secret")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")

    import orama_system.portal_server as portal_server

    with TestClient(portal_server.app, raise_server_exceptions=False) as portal:
        denied = portal.get("/api/knowledge/search?q=human")
    assert denied.status_code == 401
