#!/usr/bin/env python3
"""Regression: lifecycle routes reject cross-origin POSTs when auth is enforced."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server

_TEST_OPERATOR_BEARER = "test-operator-bearer-not-a-real-secret"
_FAKE_PID_BASE = 900_000  # an allowed request must see these, never the pid of a real listener


@pytest.fixture(autouse=True)
def lifecycle_effects(monkeypatch, tmp_path):
    """Record what the lifecycle routes would signal and start, and do neither.

    An allowed /api/stop or /api/restart signals whatever listens on 8000-8002 and starts a detached
    service, so without this the suite stops the services running on the machine that runs it.
    """
    effects = {"signalled": [], "spawned": []}
    monkeypatch.setattr(portal_server, "_pid_on_port", lambda port: _FAKE_PID_BASE + port)
    monkeypatch.setattr(portal_server.os, "kill", lambda pid, sig: effects["signalled"].append(pid))
    monkeypatch.setattr(portal_server.subprocess, "Popen",
                        lambda cmd, **kwargs: effects["spawned"].append(cmd))
    monkeypatch.setattr(portal_server, "REPO_ROOT", tmp_path)  # the restart log lands in the temp dir
    return effects


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


def test_stop_allows_loopback_cross_port_origin(monkeypatch, lifecycle_effects):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/stop",
            headers={
                "Authorization": f"Bearer {_TEST_OPERATOR_BEARER}",
                "Origin": "http://localhost:8000",
            },
        )
    assert response.status_code == 200
    assert lifecycle_effects["signalled"] == [_FAKE_PID_BASE + port for port in (8000, 8001, 8002)]


def test_restart_allows_missing_origin_for_cli(monkeypatch, lifecycle_effects):
    _enforce_auth(monkeypatch)
    with _auth_client() as client:
        response = client.post(
            "/api/restart/portal",
            headers={"Authorization": f"Bearer {_TEST_OPERATOR_BEARER}"},
        )
    assert response.status_code == 200
    assert len(lifecycle_effects["spawned"]) == 1
    if not portal_server._restart_plan("portal", windows=portal_server.os.name == "nt")["delegated"]:
        assert lifecycle_effects["signalled"] == [_FAKE_PID_BASE + 8002]


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
