#!/usr/bin/env python3
"""Tests for PT job proxy routes."""
from __future__ import annotations

from fastapi.testclient import TestClient

import portal_server


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeJobsClient:
    fail = False
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if self.fail:
            raise RuntimeError("pt down")
        if url.endswith("/v1/jobs"):
            return _FakeResponse({"jobs": [{"id": "job-1"}]})
        if url.endswith("/v1/jobs/job-1"):
            return _FakeResponse({"id": "job-1", "status": "running"})
        raise AssertionError(f"unexpected GET {url}")

    async def post(self, url: str, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        if self.fail:
            raise RuntimeError("pt down")
        if url.endswith("/cancel"):
            job_id = url.rsplit("/", 2)[-2]
            return _FakeResponse({"job_id": job_id, "cancel_requested": True})
        if url.endswith("/replay"):
            job_id = url.rsplit("/", 2)[-2]
            return _FakeResponse(
                {
                    "original_job_id": job_id,
                    "new_job_id": f"{job_id}-replay",
                    "state": "queued",
                }
            )
        return _FakeResponse({"ok": True, "job_id": (json or {}).get("job_id", "")})


def test_jobs_proxy_lists_pt_jobs(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/api/jobs")

    assert response.status_code == 200
    assert response.json()["jobs"] == [{"id": "job-1"}]


def test_jobs_proxy_gets_detail(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/api/jobs/job-1")

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "running"


def test_jobs_proxy_cancel_posts_to_pt(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    assert response.status_code == 200
    assert response.json()["result"]["cancel_requested"] is True
    assert _FakeJobsClient.calls[0] == (
        "POST",
        f"{portal_server.PT_URL}/v1/jobs/job-1/cancel",
        None,
    )


def test_jobs_proxy_replay_posts_to_pt(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    assert response.status_code == 200
    assert response.json()["result"]["original_job_id"] == "job-1"
    assert _FakeJobsClient.calls[0] == (
        "POST",
        f"{portal_server.PT_URL}/v1/jobs/job-1/replay",
        None,
    )


def test_jobs_proxy_handles_pt_down(monkeypatch):
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/api/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["jobs"] == []
    assert body["error"]


# ---------------------------------------------------------------------------
# Additional tests for the new /v1/jobs/{job_id}/cancel and /replay endpoints
# ---------------------------------------------------------------------------


def test_jobs_proxy_cancel_pt_down(monkeypatch):
    """When PT is unavailable, cancel returns available=False with error info."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


def test_jobs_proxy_replay_pt_down(monkeypatch):
    """When PT is unavailable, replay returns available=False with error info."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


def test_jobs_proxy_cancel_uses_job_id_in_url(monkeypatch):
    """The cancel URL must embed the actual job_id path segment."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/abc-999/cancel")

    assert response.status_code == 200
    called_url = _FakeJobsClient.calls[0][1]
    assert called_url.endswith("/v1/jobs/abc-999/cancel")
    assert response.json()["result"]["job_id"] == "abc-999"


def test_jobs_proxy_replay_uses_job_id_in_url(monkeypatch):
    """The replay URL must embed the actual job_id path segment."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/abc-999/replay")

    assert response.status_code == 200
    called_url = _FakeJobsClient.calls[0][1]
    assert called_url.endswith("/v1/jobs/abc-999/replay")
    assert response.json()["result"]["original_job_id"] == "abc-999"


def test_jobs_proxy_cancel_sends_no_request_body(monkeypatch):
    """Cancel must POST with no JSON body (new v1 endpoint style)."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/cancel")

    _, _, json_body = _FakeJobsClient.calls[0]
    assert json_body is None


def test_jobs_proxy_replay_sends_no_request_body(monkeypatch):
    """Replay must POST with no JSON body (new v1 endpoint style)."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/replay")

    _, _, json_body = _FakeJobsClient.calls[0]
    assert json_body is None


def test_jobs_proxy_cancel_success_response_structure(monkeypatch):
    """Successful cancel response contains available=True, source, and result."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    body = response.json()
    assert body["available"] is True
    assert "source" in body
    assert "result" in body
    assert body["result"] is not None


def test_jobs_proxy_replay_success_response_structure(monkeypatch):
    """Successful replay response contains available=True, source, result with new_job_id."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    body = response.json()
    assert body["available"] is True
    assert "source" in body
    assert body["result"]["new_job_id"] == "job-1-replay"
    assert body["result"]["state"] == "queued"


def test_jobs_proxy_cancel_error_response_structure(monkeypatch):
    """Error cancel response contains available=False, source, result=None, and error."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    body = response.json()
    assert body["available"] is False
    assert "source" in body
    assert body["result"] is None
    assert isinstance(body["error"], str)
    assert len(body["error"]) > 0


def test_jobs_proxy_replay_error_response_structure(monkeypatch):
    """Error replay response contains available=False, source, result=None, and error."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    body = response.json()
    assert body["available"] is False
    assert "source" in body
    assert body["result"] is None
    assert isinstance(body["error"], str)
    assert len(body["error"]) > 0


class _FakeJobsClientHTTPError(_FakeJobsClient):
    """Returns a 500 HTTP error response for cancel and replay calls."""

    async def post(self, url: str, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        if url.endswith("/cancel") or url.endswith("/replay"):
            return _FakeResponse({"detail": "internal error"}, status_code=500)
        return await super().post(url, json=json, **kwargs)


def test_jobs_proxy_cancel_pt_http_error(monkeypatch):
    """When PT returns an HTTP error status, cancel returns available=False."""
    _FakeJobsClientHTTPError.fail = False
    _FakeJobsClientHTTPError.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClientHTTPError)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


def test_jobs_proxy_replay_pt_http_error(monkeypatch):
    """When PT returns an HTTP error status, replay returns available=False."""
    _FakeJobsClientHTTPError.fail = False
    _FakeJobsClientHTTPError.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClientHTTPError)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]
