"""Portal job list proxies must redact secrets but keep poller/list shape."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from utils.control_plane_auth import redact_job_record, redact_jobs_list


@pytest.mark.unit
def test_redact_job_record_strips_prompt_and_metadata():
    raw = {
        "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "status": "SUCCEEDED",
        "prompt": "secret objective text",
        "metadata": {"session_id": "swarm-abc", "model": "qwen"},
        "intent": "freeform",
        "backend": "echo",
        "created_at": 1000.0,
        "updated_at": 1005.5,
    }
    safe = redact_job_record(raw)
    assert "prompt" not in safe
    assert "metadata" not in safe
    assert safe["intent"] == "freeform"
    assert safe["status"] == "SUCCEEDED"
    assert safe["backend"] == "echo"
    assert safe["elapsed_s"] == 5.5


@pytest.mark.unit
def test_redact_job_record_normalizes_iso_ts_to_epoch_for_panel():
    safe = redact_job_record(
        {
            "job_id": "j1",
            "status": "RUNNING",
            "intent": "ops",
            "ts": "2026-10-01T12:00:00+00:00",
        }
    )
    assert safe["created_at"] == 1790856000.0
    assert isinstance(safe["created_at"], float)


@pytest.mark.unit
def test_redact_job_record_hoists_spec_fields_for_lifecycle_events():
    safe = redact_job_record(
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "QUEUED",
            "spec": {
                "intent": "code-review",
                "role": "executor-agent",
                "backend_hint": "lmstudio-win",
                "prompt": "do not leak",
            },
        }
    )
    assert safe["intent"] == "code-review"
    assert safe["role"] == "executor-agent"
    assert safe["backend"] == "lmstudio-win"
    assert "spec" not in safe
    assert "prompt" not in safe


@pytest.mark.unit
def test_redact_jobs_list_accepts_pt_wrapper_or_bare_list():
    wrapped = {
        "jobs": [
            {
                "job_id": "a",
                "status": "FAILED",
                "metadata": {"x": 1},
            }
        ]
    }
    listed = [{"job_id": "b", "status": "QUEUED", "prompt": "p"}]
    assert len(redact_jobs_list(wrapped)) == 1
    assert len(redact_jobs_list(listed)) == 1
    assert "metadata" not in redact_jobs_list(wrapped)[0]
    assert "prompt" not in redact_jobs_list(listed)[0]


def test_api_v1_jobs_returns_redacted_bare_list(monkeypatch: pytest.MonkeyPatch):
    import orama_system.portal_server as portal_server

    class _FakeJobsClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, params=None, **kwargs):
            assert url.endswith("/v1/jobs")
            response = MagicMock()
            response.status_code = 200
            response.json = lambda: {
                "jobs": [
                    {
                        "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "status": "RUNNING",
                        "intent": "ops",
                        "backend_hint": "ollama",
                        "prompt": "hidden",
                        "metadata": {"n": 1},
                    }
                ]
            }
            response.raise_for_status = lambda: None
            return response

    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        body = client.get("/api/v1/jobs").json()

    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["status"] == "RUNNING"
    assert body[0]["backend"] == "ollama"
    assert "prompt" not in body[0]
    assert "metadata" not in body[0]
