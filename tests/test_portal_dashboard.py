#!/usr/bin/env python3
"""Tests for /dashboard — no filesystem path leaks in error responses."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import portal_server


def test_dashboard_missing_returns_generic_404(monkeypatch, tmp_path):
    """When routing-dashboard.html is absent, 404 body must not expose repo paths."""
    monkeypatch.setattr(portal_server, "REPO_ROOT", tmp_path)
    client = TestClient(portal_server.app)
    response = client.get("/dashboard")
    assert response.status_code == 404
    body = response.text.lower()
    assert "dashboard not available" in body
    assert "docs/dashboard" not in body
    assert "routing-dashboard.html" not in body
    assert str(tmp_path).lower() not in body
    assert "users/" not in body
    assert "expected:" not in body


def test_dashboard_serves_html_when_present(monkeypatch, tmp_path):
    """When the dashboard file exists under REPO_ROOT, return 200 HTML."""
    dash_dir = tmp_path / "docs" / "dashboard"
    dash_dir.mkdir(parents=True)
    html_path = dash_dir / "routing-dashboard.html"
    html_path.write_text("<html><body>routing</body></html>", encoding="utf-8")
    monkeypatch.setattr(portal_server, "REPO_ROOT", tmp_path)
    client = TestClient(portal_server.app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "routing" in response.text
