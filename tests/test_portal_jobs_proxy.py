#!/usr/bin/env python3
"""Tests for PT job proxy routes."""
from __future__ import annotations

from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server


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
        """
        Simulate a POST request to the fake PT jobs service and return a corresponding fake response.
        
        Parameters:
            url (str): The request URL; specific suffixes determine the response:
                - URL ending with "/cancel": responds with a cancel confirmation for the job.
                - URL ending with "/replay": responds with a replay job record (original and new job IDs and state).
                - any other URL: responds with a generic success payload, echoing `job_id` from `json` if present.
            json (optional): JSON payload sent with the request; used only to extract `job_id` for the generic response.
        
        Side effects:
            Appends ("POST", url, json) to self.calls. If self.fail is True, raises RuntimeError("pt down").
        
        Returns:
            _FakeResponse: A fake HTTP response whose JSON payload is:
                - {"job_id": <id>, "cancel_requested": True} for cancel requests.
                - {"original_job_id": <id>, "new_job_id": "<id>-replay", "state": "queued"} for replay requests.
                - {"ok": True, "job_id": "<job_id_from_json_or_empty>"} for other requests.
        """
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
    """
    Ensures GET /api/jobs returns the job list provided by the PT jobs service.
    
    Sets up a fake PT jobs client and asserts the endpoint responds with HTTP 200 and a JSON body whose "jobs" field equals [{"id": "job-1"}].
    """
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
    """
    Verifies that POST /api/jobs/{job_id}/cancel is proxied to the PT cancel endpoint and returns the cancellation result.
    
    Asserts the endpoint responds with HTTP 200, the JSON result indicates the cancel request was accepted (`cancel_requested` is `True`), and the proxy issued a POST to `{PT_URL}/v1/jobs/{job_id}/cancel` with no JSON payload.
    """
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









































































































































































    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


# ---------------------------------------------------------------------------
# Additional gap-filling tests
# ---------------------------------------------------------------------------


def test_jobs_proxy_cancel_source_is_literal_template(monkeypatch):
    """The cancel source field is the literal template string, not interpolated with the actual job_id."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/my-special-job/cancel")

    body = response.json()
    # The source value is a literal template, not substituted with the actual job_id
    assert body["source"] == "pt:/v1/jobs/{job_id}/cancel"
    assert "my-special-job" not in body["source"]


def test_jobs_proxy_replay_source_is_literal_template(monkeypatch):
    """The replay source field is the literal template string, not interpolated with the actual job_id."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/my-special-job/replay")

    body = response.json()
    # The source value is a literal template, not substituted with the actual job_id
    assert body["source"] == "pt:/v1/jobs/{job_id}/replay"
    assert "my-special-job" not in body["source"]


def test_jobs_proxy_cancel_error_source_is_literal_template(monkeypatch):
    """The source field in error cancel responses is also the literal template string."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/my-special-job/cancel")

    body = response.json()
    assert body["source"] == "pt:/v1/jobs/{job_id}/cancel"


def test_jobs_proxy_replay_error_source_is_literal_template(monkeypatch):
    """The source field in error replay responses is also the literal template string."""
    _FakeJobsClient.fail = True
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/my-special-job/replay")

    body = response.json()
    assert body["source"] == "pt:/v1/jobs/{job_id}/replay"


def test_jobs_proxy_cancel_success_has_no_error_key(monkeypatch):
    """A successful cancel response must not include an 'error' key."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/cancel")

    body = response.json()
    assert body["available"] is True
    assert "error" not in body


def test_jobs_proxy_replay_success_has_no_error_key(monkeypatch):
    """A successful replay response must not include an 'error' key."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/job-1/replay")

    body = response.json()
    assert body["available"] is True
    assert "error" not in body


def test_jobs_proxy_cancel_makes_exactly_one_upstream_call(monkeypatch):
    """Exactly one POST request is forwarded upstream per cancel call."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/cancel")

    post_calls = [c for c in _FakeJobsClient.calls if c[0] == "POST"]
    assert len(post_calls) == 1


def test_jobs_proxy_replay_makes_exactly_one_upstream_call(monkeypatch):
    """Exactly one POST request is forwarded upstream per replay call."""
    _FakeJobsClient.fail = False
    _FakeJobsClient.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        client.post("/api/jobs/job-1/replay")

    post_calls = [c for c in _FakeJobsClient.calls if c[0] == "POST"]
    assert len(post_calls) == 1


class _FakeJobsClientNotFound(_FakeJobsClient):
    """Returns a 404 HTTP error response for cancel and replay calls."""

    async def post(self, url: str, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        if url.endswith("/cancel") or url.endswith("/replay"):
            return _FakeResponse({"detail": "not found"}, status_code=404)
        return await super().post(url, json=json, **kwargs)


def test_jobs_proxy_cancel_pt_404_error(monkeypatch):
    """When PT returns 404, cancel returns available=False with an error message."""
    _FakeJobsClientNotFound.fail = False
    _FakeJobsClientNotFound.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClientNotFound)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/nonexistent-job/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]


def test_jobs_proxy_replay_pt_404_error(monkeypatch):
    """When PT returns 404, replay returns available=False with an error message."""
    _FakeJobsClientNotFound.fail = False
    _FakeJobsClientNotFound.calls = []
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClientNotFound)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/jobs/nonexistent-job/replay")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["result"] is None
    assert body["error"]
