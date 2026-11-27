"""The portal states which front end it serves and which build, so a missing or stale web/dist is never silent."""

from __future__ import annotations

import json

import pytest

from fastapi.testclient import TestClient

from orama_system import portal_server


async def _fake_status():
    return {"services": {}, "routing": None, "activity": [], "agents": []}


def _client(monkeypatch, dist):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    monkeypatch.setattr(portal_server, "_WEB_DIST", dist)
    monkeypatch.setattr(portal_server, "api_status", _fake_status)
    return TestClient(portal_server.app, raise_server_exceptions=False)


def test_without_a_build_it_says_legacy_and_why(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path / "missing") as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["x-portal-surface"] == "legacy"
    assert resp.headers["x-portal-surface-reason"] == "no-web-dist"
    assert "<html" in resp.text.lower()
    assert "x-portal-build" not in resp.headers


def test_with_a_stamped_build_it_says_react_and_names_the_build(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "build-info.json").write_text(json.dumps({"git_sha": "abc1234", "built_at": "2026-11-27T08:00:00Z"}), encoding="utf-8")
    with _client(monkeypatch, tmp_path) as client:
        resp = client.get("/")
    assert resp.headers["x-portal-surface"] == "react"
    assert resp.headers["x-portal-build"] == "abc1234"
    assert "<title>x</title>" in resp.text


def test_an_unstamped_build_is_served_but_flagged_unknown(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    with _client(monkeypatch, tmp_path) as client:
        resp = client.get("/")
    assert resp.headers["x-portal-surface"] == "react"
    assert resp.headers["x-portal-build"] == "unstamped"


def test_a_corrupt_stamp_never_breaks_the_page(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "build-info.json").write_text("{not json", encoding="utf-8")
    with _client(monkeypatch, tmp_path) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["x-portal-build"] == "unstamped"


def test_the_legacy_fallback_logs_a_warning_once_not_per_request(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(portal_server, "_LEGACY_SURFACE_LOGGED", False)
    with caplog.at_level("WARNING"), _client(monkeypatch, tmp_path / "missing") as client:
        client.get("/")
        client.get("/")
        client.get("/")
    assert sum("legacy" in r.getMessage().lower() for r in caplog.records) == 1
    assert any("legacy" in r.getMessage().lower() and "web/dist" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("stamp", [{"git_sha": 123}, {"git_sha": ""}, [], {"git_sha": "abc\r\nX-Evil: 1"}, {"git_sha": "not-hex!"}, {"git_sha": "unknown"}])
def test_a_stamp_that_is_not_a_hex_commit_is_reported_unstamped(monkeypatch, tmp_path, stamp):
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "build-info.json").write_text(json.dumps(stamp), encoding="utf-8")
    with _client(monkeypatch, tmp_path) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["x-portal-build"] == "unstamped"
    assert "x-evil" not in resp.headers


def test_a_full_commit_hash_is_shortened_in_the_header(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "build-info.json").write_text(json.dumps({"git_sha": "0123456789abcdef0123456789abcdef01234567"}), encoding="utf-8")
    with _client(monkeypatch, tmp_path) as client:
        resp = client.get("/")
    assert resp.headers["x-portal-build"] == "0123456789ab"
