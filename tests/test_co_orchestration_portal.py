"""Tests for co-orchestration portal inbox view."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server
from orama_system.co_orchestration_portal import build_co_orchestration_summary
from orama_system.portals.co_orchestration import resolve_skin_id


def test_build_co_orchestration_summary_directions():
    summary = build_co_orchestration_summary(
        local_role="mac",
        peer_ip="192.168.254.100",
        local_inbox=[
            {
                "filename": "gpu-results.md",
                "source": "win",
                "assignee": "mac",
                "topic": "autoresearch/results",
                "fanout_id": "batch-1",
                "received_at": 100,
            }
        ],
        peer_inbox=[
            {
                "filename": "win-gpu.md",
                "source": "mac",
                "assignee": "win",
                "topic": "autoresearch/gpu-run",
                "fanout_id": "batch-1",
                "received_at": 99,
            }
        ],
    )
    assert summary["local_inbox"][0]["direction"] == "inbound"
    assert summary["peer_inbox"][0]["direction"] == "outbound"
    assert summary["stats"]["inbound_from_peer"] == 1
    assert summary["stats"]["outbound_on_peer"] == 1


def test_resolve_skin_id_defaults_by_role():
    assert resolve_skin_id("mac") == "macos"
    assert resolve_skin_id("win") == "windows"
    assert resolve_skin_id("mac", explicit="windows") == "windows"


def test_api_co_orchestration_local_only(monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "co-orch-test")
    root = tmp_path / "lan_peer"
    monkeypatch.setattr("orama_system.lan_peer_files.lan_peer_state_dir", lambda: root)
    monkeypatch.setattr(portal_server, "read_discovery_peer_ip", lambda: "192.168.254.100")

    async def _empty_peer():
        return [], ""

    monkeypatch.setattr(portal_server, "_fetch_peer_inbox_remote", _empty_peer)

    from orama_system.lan_peer_files import write_inbox_file

    write_inbox_file("mac-task.md", "# Task\n", assignee="mac", source="win", topic="ops/test")
    headers = {"Authorization": "Bearer co-orch-test"}

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        resp = client.get("/api/co-orchestration", headers=headers)
        page = client.get("/co-orchestration/macos")
        macos = client.get("/co-orchestration/macos")

    assert resp.status_code == 200
    body = resp.json()
    assert body["local_role"] == portal_server.local_platform()
    assert len(body["local_inbox"]) == 1
    assert page.status_code == 200
    assert "co-orchestration" in page.text.lower()
    assert "OpenClaw" in macos.text


def test_co_orchestration_windows_skin_page(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "co-orch-token")

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        win_page = client.get("/co-orchestration/windows")

    assert win_page.status_code == 200
    assert "Hermes" in win_page.text


def test_co_orchestration_file_local_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "co-orch-test")
    root = tmp_path / "lan_peer"
    monkeypatch.setattr("orama_system.lan_peer_files.lan_peer_state_dir", lambda: root)

    from orama_system.lan_peer_files import write_inbox_file

    write_inbox_file("preview.md", "# Hello\n\n**bold**", assignee="mac", topic="test")
    headers = {"Authorization": "Bearer co-orch-test"}

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        resp = client.get("/api/co-orchestration/file/preview.md?scope=local", headers=headers)

    assert resp.status_code == 200
    assert "Hello" in resp.json()["body"]


def test_co_orchestration_loopback_page_no_auth(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "co-orch-token")

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        allowed = client.get("/co-orchestration")
        denied = client.get("/api/co-orchestration")

    assert allowed.status_code == 200
    assert "cpFetch" in allowed.text
    assert denied.status_code == 401
