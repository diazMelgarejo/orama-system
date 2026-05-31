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
# cancel proxy — new /v1/jobs/{job_id}/cancel endpoint
# ---------------------------------------------------------------------------


def test_cancel_sends_no_json_body(monkeypatch):
    """Cancel must POST without a JSON body (no job_id in payload)."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-99/cancel")

    assert _FakeJobsClient.calls[0][2] is None  # json= kwarg must be absent/None


def test_cancel_url_contains_job_id_in_path(monkeypatch):
    """Cancel must embed the job_id in the URL path, not as a query/body param."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/abc-123/cancel")

    method, url, _ = _FakeJobsClient.calls[0]
    assert method == "POST"
    assert url == f"{portal_server.PT_URL}/v1/jobs/abc-123/cancel"


def test_cancel_available_true_on_success(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    body = response.json()
    assert body["available"] is True
    assert "error" not in body


def test_cancel_result_reflects_pt_response(monkeypatch):
    """The 'result' key must pass through the PT response payload."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    result = response.json()["result"]
    assert result["job_id"] == "job-1"
    assert result["cancel_requested"] is True


def test_cancel_source_is_literal_template_string(monkeypatch):
    """source must be the literal string 'pt:/v1/jobs/{job_id}/cancel', not interpolated."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    assert response.json()["source"] == "pt:/v1/jobs/{job_id}/cancel"


def test_cancel_handles_pt_down(monkeypatch):
    """When PT is unreachable, cancel returns available=False with an error message."""
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


def test_cancel_error_source_is_literal_template_string(monkeypatch):
    """Even in the error path the source must be the literal template string."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-42/cancel")

    assert response.json()["source"] == "pt:/v1/jobs/{job_id}/cancel"


def test_cancel_different_job_ids_routed_correctly(monkeypatch):
    """Each job_id must appear in the outbound URL, not bleed across calls."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        for job_id in ("alpha", "beta", "gamma-99"):
            client.post(f"/api/jobs/{job_id}/cancel")

    urls = [call[1] for call in _FakeJobsClient.calls]
    assert urls == [
        f"{portal_server.PT_URL}/v1/jobs/alpha/cancel",
        f"{portal_server.PT_URL}/v1/jobs/beta/cancel",
        f"{portal_server.PT_URL}/v1/jobs/gamma-99/cancel",
    ]


def test_cancel_pt_http_error_returns_unavailable(monkeypatch):
    """When PT returns an HTTP error status, the proxy must return available=False."""

    class _ErrorClient(_FakeJobsClient):
        async def post(self, url: str, json=None, **kwargs):
            self.calls.append(("POST", url, json))
            return _FakeResponse({}, status_code=500)

    _ErrorClient.fail = False
    _ErrorClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _ErrorClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


# ---------------------------------------------------------------------------
# replay proxy — new /v1/jobs/{job_id}/replay endpoint
# ---------------------------------------------------------------------------


def test_replay_sends_no_json_body(monkeypatch):
    """Replay must POST without a JSON body."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-99/replay")

    assert _FakeJobsClient.calls[0][2] is None


def test_replay_url_contains_job_id_in_path(monkeypatch):
    """Replay must embed the job_id in the URL path."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/abc-123/replay")

    method, url, _ = _FakeJobsClient.calls[0]
    assert method == "POST"
    assert url == f"{portal_server.PT_URL}/v1/jobs/abc-123/replay"


def test_replay_available_true_on_success(monkeypatch):
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    body = response.json()
    assert body["available"] is True
    assert "error" not in body


def test_replay_result_reflects_pt_response(monkeypatch):
    """The 'result' key must pass through the PT response payload."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    result = response.json()["result"]
    assert result["original_job_id"] == "job-1"
    assert result["new_job_id"] == "job-1-replay"
    assert result["state"] == "queued"


def test_replay_source_is_literal_template_string(monkeypatch):
    """source must be the literal string 'pt:/v1/jobs/{job_id}/replay', not interpolated."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    assert response.json()["source"] == "pt:/v1/jobs/{job_id}/replay"


def test_replay_handles_pt_down(monkeypatch):
    """When PT is unreachable, replay returns available=False with an error message."""
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


def test_replay_error_source_is_literal_template_string(monkeypatch):
    """Even in the error path the source must be the literal template string."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-42/replay")

    assert response.json()["source"] == "pt:/v1/jobs/{job_id}/replay"


def test_replay_different_job_ids_routed_correctly(monkeypatch):
    """Each job_id must appear in the outbound URL."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        for job_id in ("alpha", "beta", "gamma-99"):
            client.post(f"/api/jobs/{job_id}/replay")

    urls = [call[1] for call in _FakeJobsClient.calls]
    assert urls == [
        f"{portal_server.PT_URL}/v1/jobs/alpha/replay",
        f"{portal_server.PT_URL}/v1/jobs/beta/replay",
        f"{portal_server.PT_URL}/v1/jobs/gamma-99/replay",
    ]


def test_replay_pt_http_error_returns_unavailable(monkeypatch):
    """When PT returns an HTTP error status, the proxy must return available=False."""

    class _ErrorClient(_FakeJobsClient):
        async def post(self, url: str, json=None, **kwargs):
            self.calls.append(("POST", url, json))
            return _FakeResponse({}, status_code=500)

    _ErrorClient.fail = False
    _ErrorClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _ErrorClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


# ---------------------------------------------------------------------------
# Regression: old-style body-based endpoints must no longer be called
# ---------------------------------------------------------------------------


def test_cancel_does_not_use_old_body_based_endpoint(monkeypatch):
    """Regression: the old POST /cancel with json body must not be used."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/cancel")

    _, url, body = _FakeJobsClient.calls[0]
    # Must NOT end with the bare "/cancel" path that included a body
    assert "/v1/jobs/" in url
    assert body is None  # no JSON body sent


def test_replay_does_not_use_old_body_based_endpoint(monkeypatch):
    """Regression: the old POST /replay with json body must not be used."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/replay")

    _, url, body = _FakeJobsClient.calls[0]
    assert "/v1/jobs/" in url
    assert body is None
