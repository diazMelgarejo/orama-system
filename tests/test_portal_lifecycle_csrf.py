#!/usr/bin/env python3
"""Regression: lifecycle routes reject cross-origin POSTs when auth is enforced."""
from __future__ import annotations

from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server

_TEST_OPERATOR_BEARER = "test-operator-bearer-not-a-real-secret"


def _auth_client() -> TestClient:
    return TestClient(portal_server.app, raise_server_exceptions=False)


def _enforce_auth(monkeypatch, bearer: str = _TEST_OPERATOR_BEARER) -> None:
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", bearer)
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")


def test_stop_rejects_cross_origin_with_bearer(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/stop",
            headers={
                "Authorization": f"Bearer {_TEST_OPERATOR_BEARER}",
                "Origin": "http://evil.example",
            },
        )
    assert response.status_code == 403


def test_stop_allows_loopback_cross_port_origin(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/stop",
            headers={
                "Authorization": f"Bearer {_TEST_OPERATOR_BEARER}",
                "Origin": "http://localhost:8000",
            },
        )
    assert response.status_code != 403


def test_restart_allows_missing_origin_for_cli(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/restart/portal",
            headers={"Authorization": f"Bearer {_TEST_OPERATOR_BEARER}"},
        )
    assert response.status_code != 403


def test_rediscover_rejects_cross_origin_referer(monkeypatch):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/rediscover",
            headers={
                "Authorization": f"Bearer {_TEST_OPERATOR_BEARER}",
                "Referer": "http://attacker.example/dashboard",
            },
        )
    assert response.status_code == 403
