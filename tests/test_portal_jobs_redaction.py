"""Portal job list proxies must redact secrets but keep poller/list shape."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from utils.control_plane_auth import redact_job_record, redact_jobs_list


@pytest.mark.unit
def test_redact_job_record_strips_prompt_and_metadata() -> None:
    """Drop prompt/metadata while keeping list columns and elapsed_s."""
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
def test_redact_job_record_treats_event_ts_as_updated_at() -> None:
    """A lone lifecycle ``ts`` is the event time, not the job start."""
    safe = redact_job_record(
        {
            "job_id": "j1",
            "status": "RUNNING",
            "intent": "ops",
            "ts": "2026-10-01T12:00:00+00:00",
        }
    )
    assert "created_at" not in safe
    assert safe["updated_at"] == 1790856000.0
    assert "elapsed_s" not in safe


@pytest.mark.unit
def test_redact_job_record_elapsed_uses_created_and_updated() -> None:
    """Elapsed time comes from explicit start and latest timestamps."""
    safe = redact_job_record(
        {
            "job_id": "j1",
            "status": "SUCCEEDED",
            "intent": "echo",
            "backend_hint": "echo",
            "created_at": "2026-10-01T12:00:00+00:00",
            "updated_at": "2026-10-01T12:00:05+00:00",
        }
    )
    assert safe["created_at"] == 1790856000.0
    assert safe["updated_at"] == 1790856005.0
    assert safe["elapsed_s"] == 5.0
    assert safe["backend"] == "echo"


@pytest.mark.unit
def test_redact_job_record_rejects_non_finite_numeric_timestamps() -> None:
    """Omit created_at when coercion yields NaN or other non-finite values."""
    safe = redact_job_record(
        {
            "job_id": "j-nan",
            "status": "RUNNING",
            "created_at": "NaN",
        }
    )
    assert "created_at" not in safe


@pytest.mark.unit
def test_redact_job_record_hoists_spec_fields_for_lifecycle_events() -> None:
    """Copy intent/role/backend from nested spec when top-level fields are absent."""
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
def test_redact_jobs_list_accepts_pt_wrapper_or_bare_list() -> None:
    """Accept Perpetua ``{"jobs": [...]}`` or a bare supervisor list."""
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


@pytest.mark.unit
def test_redact_jobs_list_skips_malformed_row_without_breaking_list() -> None:
    """Skip rows that fail redaction without dropping the whole list response."""
    payload = {
        "jobs": [
            {"job_id": "ok", "status": "QUEUED", "created_at": "NaN"},
            {"job_id": "good", "status": "RUNNING", "ts": "2026-10-01T12:00:00+00:00"},
        ]
    }
    listed = redact_jobs_list(payload)
    assert len(listed) == 2
    assert listed[0]["job_id"] == "ok"
    assert "created_at" not in listed[1]
    assert listed[1]["updated_at"] == 1790856000.0


class _FakeJobsClient:
    """Minimal httpx.AsyncClient stand-in for ``GET /api/v1/jobs`` proxy tests."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Accept the same constructor signature as httpx.AsyncClient."""

    async def __aenter__(self) -> _FakeJobsClient:
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> bool:
        """Exit the async context manager without suppressing exceptions."""
        return False

    async def get(self, url: str, params: Any = None, **kwargs: Any) -> MagicMock:
        """Return a mocked Perpetua jobs list payload."""
        assert url.endswith("/v1/jobs")
        response = MagicMock()
        response.status_code = 200
        response.json = lambda: {
            "jobs": [
                {
                    "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "status": "SUCCEEDED",
                    "created_at": "2026-10-01T12:00:00+00:00",
                    "updated_at": "2026-10-01T12:00:05+00:00",
                    "result": {"output": "hidden"},
                    "spec": {
                        "intent": "ops",
                        "role": "executor-agent",
                        "backend_hint": "ollama",
                        "prompt": "hidden",
                        "metadata": {"n": 1},
                    },
                }
            ]
        }
        response.raise_for_status = lambda: None
        return response


def test_api_v1_jobs_returns_redacted_bare_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GET /api/v1/jobs`` returns a redacted bare list, not a wrapped object."""
    import orama_system.portal_server as portal_server

    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeJobsClient)
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        body = client.get("/api/v1/jobs").json()

    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["status"] == "SUCCEEDED"
    assert body[0]["intent"] == "ops"
    assert body[0]["role"] == "executor-agent"
    assert body[0]["backend"] == "ollama"
    assert body[0]["created_at"] == 1790856000.0
    assert body[0]["updated_at"] == 1790856005.0
    assert body[0]["elapsed_s"] == 5.0
    assert "prompt" not in body[0]
    assert "metadata" not in body[0]
    assert "spec" not in body[0]
    assert "result" not in body[0]
