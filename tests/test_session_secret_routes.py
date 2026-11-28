"""Write-only session key routes: names come out, values go in, never back.

A value must never appear in a response body, a log line or an exception text, and no route may answer 200 when it
did nothing. The sealed store lives outside the repository, and save is the one deliberate plain-text export.
"""

from __future__ import annotations

import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orama_system import session_secret_routes
from orama_system.session_secret_routes import router

pytestmark = pytest.mark.unit

SECRET = "fixture-value-not-a-real-key-1234567890"
NAME = "WANDB_API_KEY"


@pytest.fixture(autouse=True)
def _isolated_session(tmp_path, monkeypatch):
    """Fresh caches, an isolated state folder, a working key source and a repository under tmp."""
    monkeypatch.setattr(session_secret_routes, "_STORES", {})
    monkeypatch.setattr(session_secret_routes, "_CALLS", {})
    monkeypatch.setattr(session_secret_routes, "_token_source", lambda: "routes-test-token")
    monkeypatch.setattr(session_secret_routes, "_repo_root", lambda: tmp_path / "repo")
    monkeypatch.setenv("ORAMA_SESSION_SECRETS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ORAMA_SESSION_KEY_MODE", "dev-control-plane")


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=True)


def _put(client: TestClient, name: str = NAME, value: str = SECRET):
    return client.put("/api/session-secrets/%s" % name, json={"value": value})


# ---------------------------------------------------------------- authorisation


def test_every_route_requires_the_control_plane_token(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "routes-test-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    client = _client()
    denied = [
        client.get("/api/session-secrets"),
        _put(client),
        client.post("/api/session-secrets/save"),
        client.delete("/api/session-secrets"),
    ]
    assert [response.status_code for response in denied] == [401, 401, 401, 401]
    for response in denied:
        assert SECRET not in response.text
    allowed = client.get("/api/session-secrets", headers={"Authorization": "Bearer routes-test-token"})
    assert allowed.status_code == 200
    assert allowed.json() == {"names": [], "status": {}}


# ---------------------------------------------------------------- write-only


def test_names_are_listed_and_the_value_never_comes_back(tmp_path, caplog):
    (tmp_path / "repo").mkdir()
    client = _client()
    with caplog.at_level(logging.DEBUG):
        put = _put(client)
        listing = client.get("/api/session-secrets")
        saved = client.post("/api/session-secrets/save")
        purged = client.delete("/api/session-secrets")
    assert put.status_code == 200
    assert put.json() == {"name": NAME, "state": "set"}
    assert listing.json() == {"names": [NAME], "status": {NAME: "set"}}
    assert saved.status_code == 200
    assert set(saved.json()) == {"kind", "file"}
    assert purged.json() == {"purged": True, "names": []}
    for response in (put, listing, saved, purged):
        assert SECRET not in response.text
    assert SECRET not in caplog.text


def test_the_sealed_file_lives_outside_the_repository(tmp_path):
    client = _client()
    assert _put(client).status_code == 200
    sealed = list((tmp_path / "state").rglob("session-*.enc"))
    assert len(sealed) == 1
    assert list((tmp_path / "repo").rglob("*.enc")) == []
    assert SECRET.encode() not in sealed[0].read_bytes()


def test_a_refused_value_is_reported_without_echoing_it():
    client = _client()
    for value in ("", "line1\nline2", "x" * 9000, "nul\x00byte"):
        response = _put(client, value=value)
        assert response.status_code == 422
        assert "line1" not in response.text
        assert "nul" not in response.text


def test_a_body_outside_the_expected_shape_is_refused_without_echoing_it():
    client = _client()
    for body in ({"value": 9876543210}, {"val": SECRET}, {"value": SECRET, "extra": "x"}, []):
        response = client.put("/api/session-secrets/%s" % NAME, json=body)
        assert response.status_code == 422
        assert "9876543210" not in response.text
        assert SECRET not in response.text
    raw = client.put("/api/session-secrets/%s" % NAME, content=b"not json")
    assert raw.status_code == 422
    assert SECRET not in raw.text


def test_a_file_sealed_under_another_key_is_a_clean_refusal(monkeypatch):
    client = _client()
    assert _put(client).status_code == 200
    # The provider reads the token at key time, so a rotated token makes this session's file unreadable.
    store = next(iter(session_secret_routes._STORES.values()))
    monkeypatch.setattr(store._keys, "_token_source", lambda: "a-different-token")
    response = client.get("/api/session-secrets")
    assert response.status_code == 409
    assert SECRET not in response.text


# ---------------------------------------------------------------- no key source


def test_without_a_key_source_every_route_answers_503_and_names_the_setting(monkeypatch):
    monkeypatch.delenv("ORAMA_SESSION_KEY_MODE", raising=False)
    client = _client()
    responses = [
        client.get("/api/session-secrets"),
        _put(client),
        client.post("/api/session-secrets/save"),
        client.delete("/api/session-secrets"),
    ]
    for response in responses:
        assert response.status_code == 503
        assert "ORAMA_SESSION_KEY_MODE" in response.json()["detail"]
        assert SECRET not in response.text


# ---------------------------------------------------------------- save targets


def test_save_writes_env_when_it_has_no_filled_value(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env.example").write_text("# keys\nWANDB_API_KEY=\n", encoding="utf-8")
    client = _client()
    assert _put(client).status_code == 200
    saved = client.post("/api/session-secrets/save")
    assert saved.status_code == 200
    assert saved.json() == {"kind": "env", "file": ".env"}
    assert "WANDB_API_KEY='%s'" % SECRET in (repo / ".env").read_text(encoding="utf-8")
    assert SECRET not in saved.text


def test_save_goes_to_a_new_session_file_and_never_touches_a_populated_env(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("WANDB_API_KEY=existing-value\n", encoding="utf-8")
    client = _client()
    assert _put(client, "OPENROUTER_API_KEY").status_code == 200
    saved = client.post("/api/session-secrets/save")
    assert saved.status_code == 200
    body = saved.json()
    assert body["kind"] == "session-env"
    assert re.fullmatch(r"\.env\.[A-Za-z0-9]{6,32}", body["file"])
    assert SECRET not in saved.text
    assert (repo / ".env").read_text(encoding="utf-8") == "WANDB_API_KEY=existing-value\n"
    assert SECRET in (repo / body["file"]).read_text(encoding="utf-8")


# ---------------------------------------------------------------- purge


def test_purge_removes_the_sealed_file(tmp_path):
    client = _client()
    assert _put(client).status_code == 200
    purged = client.delete("/api/session-secrets")
    assert purged.status_code == 200
    assert purged.json() == {"purged": True, "names": []}
    assert list((tmp_path / "state").rglob("session-*.enc")) == []
    assert client.get("/api/session-secrets").json() == {"names": [], "status": {}}


# ---------------------------------------------------------------- names and limits


@pytest.mark.parametrize("name", ["lower", "A", "MIXED-case", "has space", "X" * 70, "A=B"])
def test_a_bad_name_is_refused_with_422(name):
    client = _client()
    response = _put(client, name)
    assert response.status_code == 422
    assert SECRET not in response.text


def test_writes_are_rate_limited_per_client(monkeypatch):
    monkeypatch.setattr(session_secret_routes, "_WRITE_MAX_CALLS", 2)
    client = _client()
    assert _put(client, value="one").status_code == 200
    assert _put(client, value="two").status_code == 200
    assert _put(client, value="three").status_code == 429
