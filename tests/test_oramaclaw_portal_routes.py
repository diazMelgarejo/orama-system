#!/usr/bin/env python3
"""Tests for /api/oramaclaw/conflicts routes in portal_server.py."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server


def _make_resolution(resolution_id: str = "res-001") -> dict:
    return {
        "resolution_id": resolution_id,
        "transaction_id": "txn-abc123",
        "created_at": "2026-06-21T00:00:00+00:00",
        "resolved_at": None,
        "chosen": None,
        "conflict": {
            "resource_key": "some-resource",
            "manager": "example-manager",
            "managed_path": "/models/providers/example",
            "base_fingerprint": None,
            "observed_fingerprint": None,
            "desired_fingerprint": "sha256:deadbeef",
            "security_topology": False,
            "choices": ["keep", "overwrite", "skip"],
            "resolution_id": resolution_id,
        },
    }


def test_get_conflicts_empty_when_no_state_dir(monkeypatch, tmp_path):
    """GET /api/oramaclaw/conflicts with no state dir returns 200 with empty list."""
    missing_dir = tmp_path / "nonexistent"
    monkeypatch.setenv("ORAMACLAW_STATE_DIR", str(missing_dir))

    client = TestClient(portal_server.app)
    response = client.get("/api/oramaclaw/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert data == {"conflicts": []}


def test_get_conflicts_returns_pending(monkeypatch, tmp_path):
    """GET /api/oramaclaw/conflicts returns records from seeded pending-resolutions.json."""
    state_dir = tmp_path / "oramaclaw"
    state_dir.mkdir(parents=True)
    records = [_make_resolution("res-001"), _make_resolution("res-002")]
    (state_dir / "pending-resolutions.json").write_text(
        json.dumps(records), encoding="utf-8"
    )
    monkeypatch.setenv("ORAMACLAW_STATE_DIR", str(state_dir))

    client = TestClient(portal_server.app)
    response = client.get("/api/oramaclaw/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert len(data["conflicts"]) == 2
    ids = {c["resolution_id"] for c in data["conflicts"]}
    assert ids == {"res-001", "res-002"}


def test_resolve_conflict_success(monkeypatch, tmp_path):
    """POST /api/oramaclaw/conflicts/{id}/resolve with valid id returns 200 ok=true."""
    state_dir = tmp_path / "oramaclaw"
    state_dir.mkdir(parents=True)
    records = [_make_resolution("res-abc")]
    (state_dir / "pending-resolutions.json").write_text(
        json.dumps(records), encoding="utf-8"
    )
    monkeypatch.setenv("ORAMACLAW_STATE_DIR", str(state_dir))

    client = TestClient(portal_server.app)
    response = client.post(
        "/api/oramaclaw/conflicts/res-abc/resolve",
        json={"choice": "keep"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["resolution_id"] == "res-abc"
    assert data["chosen"] == "keep"

    # Verify the file was updated atomically
    updated = json.loads(
        (state_dir / "pending-resolutions.json").read_text(encoding="utf-8")
    )
    assert len(updated) == 1
    assert updated[0]["chosen"] == "keep"
    assert updated[0]["resolved_at"] is not None


def test_resolve_conflict_not_found(monkeypatch, tmp_path):
    """POST /api/oramaclaw/conflicts/{id}/resolve with unknown id returns 404."""
    state_dir = tmp_path / "oramaclaw"
    state_dir.mkdir(parents=True)
    records = [_make_resolution("res-xyz")]
    (state_dir / "pending-resolutions.json").write_text(
        json.dumps(records), encoding="utf-8"
    )
    monkeypatch.setenv("ORAMACLAW_STATE_DIR", str(state_dir))

    client = TestClient(portal_server.app, raise_server_exceptions=False)
    response = client.post(
        "/api/oramaclaw/conflicts/res-does-not-exist/resolve",
        json={"choice": "overwrite"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data.get("detail", data)
