#!/usr/bin/env python3
"""Tests for fail-closed swarm launch."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import orama_system.portal_server as portal_server
from orama_system import swarm_approval


class _FakeResponse:
    """Minimal httpx response stub for swarm launch client fakes."""

    def __init__(self, payload, status_code: int = 200):
        """Store JSON payload and HTTP status for ``raise_for_status``."""
        self._payload = payload
        self.status_code = status_code

    def json(self):
        """Return the configured JSON body."""
        return self._payload

    def raise_for_status(self):
        """Raise ``HTTPStatusError`` for non-success status codes."""
        if self.status_code >= 400:
            request = portal_server.httpx.Request("POST", "http://pt.test/v1/jobs")
            response = portal_server.httpx.Response(self.status_code, request=request)
            raise portal_server.httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=response,
            )


class _FakeLaunchClient:
    """Record swarm launch posts/cancels and simulate Perpetua dispatch failures."""

    submitted = []
    cancelled = []
    fail_role = None
    fail_role_ambiguous = False
    omit_job_id_for: set[str] = set()
    cancel_raises_for: set[str] = set()
    cancel_terminal_state = "cancelled"
    cancel_worker_kind = None
    cancel_containment_state = None
    route_payload = {"backend_hint": "lmstudio-mac", "model_hint": "Qwen3.5-9B-MLX-4bit"}

    def __init__(self, *args, **kwargs):
        """Accept the same constructor signature as ``httpx.AsyncClient``."""

    async def __aenter__(self):
        """Return the fake client instance."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Propagate exceptions from the wrapped block."""
        return False

    async def post(self, url: str, json=None, **kwargs):
        """Simulate Perpetua routing, job submit, and cancel endpoints."""
        if url.endswith("/models/route"):
            return _FakeResponse(self.route_payload)
        if url.endswith("/cancel"):
            job_id = url.rsplit("/", 2)[-2]
            if job_id in self.cancel_raises_for:
                raise RuntimeError("cancel failed")
            self.cancelled.append(job_id)
            payload = {
                "job_id": job_id,
                "cancel_requested": True,
                "terminal_state": self.cancel_terminal_state,
            }
            if self.cancel_worker_kind is not None:
                payload["worker_kind"] = self.cancel_worker_kind
            if self.cancel_containment_state is not None:
                payload["containment_state"] = self.cancel_containment_state
            return _FakeResponse(payload)
        if url.endswith("/v1/jobs"):
            self.submitted.append(json)
            role = json["metadata"]["role"]
            if role == self.fail_role:
                if self.fail_role_ambiguous:
                    raise RuntimeError("dispatch failed")
                return _FakeResponse({"detail": "dispatch failed"}, status_code=503)
            if role in self.omit_job_id_for:
                return _FakeResponse({})
            return _FakeResponse({"job_id": f"job-{role}"})
        raise AssertionError(f"unexpected POST {url}")


def _portal_status(ok=True):
    """Build a minimal ``hardware_policy`` block for portal status stubs."""
    return {
        "hardware_policy": {
            "ok": ok,
            "violations": [] if ok else ["NEVER_MAC bad-model advertised by lmstudio-mac"],
            "safe_defaults": {"mac": ["mac-model"], "win": []},
        }
    }


def _patch_hardware_policy(monkeypatch: pytest.MonkeyPatch, *, ok: bool = True) -> None:
    """Stub portal hardware probes so launch tests skip live LM Studio calls."""

    async def fake_hardware_policy() -> dict[str, Any]:
        """Return a minimal hardware_policy block with the requested ok flag."""
        return _portal_status(ok=ok)["hardware_policy"]

    monkeypatch.setattr(
        portal_server,
        "_portal_hardware_policy_snapshot",
        fake_hardware_policy,
    )


@pytest.fixture(autouse=True)
def _isolated_swarm_state(monkeypatch: pytest.MonkeyPatch):
    """Reset swarm approval caches and legacy env flags before each test."""
    swarm_approval._cache.clear()
    swarm_approval._in_flight.clear()
    monkeypatch.delenv("ORAMA_SWARM_APPROVAL_SECRET", raising=False)
    monkeypatch.delenv("ORAMA_SWARM_LEGACY_APPROVE", raising=False)
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.cancelled = []
    _FakeLaunchClient.cancel_raises_for = set()
    _FakeLaunchClient.cancel_terminal_state = "cancelled"
    _FakeLaunchClient.cancel_worker_kind = None
    _FakeLaunchClient.cancel_containment_state = None
    _FakeLaunchClient.fail_role = None
    _FakeLaunchClient.fail_role_ambiguous = False
    _FakeLaunchClient.omit_job_id_for = set()
    _FakeLaunchClient.route_payload = {
        "backend_hint": "lmstudio-mac",
        "model_hint": "Qwen3.5-9B-MLX-4bit",
    }
    yield
    swarm_approval._cache.clear()
    swarm_approval._in_flight.clear()


def test_swarm_launch_requires_approval(monkeypatch):
    """Verify swarm launch requires approval."""
    _patch_hardware_policy(monkeypatch)
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post("/api/swarm/launch", json={"objective": "Ship launch"})

    assert response.status_code == 422


def _approved_payload(
    client: TestClient,
    objective: str,
    **options: Any,
) -> dict[str, Any]:
    """Build a launch body with credentials from ``/api/swarm/preview``."""
    request = {"objective": objective, **options}
    preview = client.post("/api/swarm/preview", json=request).json()
    return {
        **request,
        "approved": True,
        "preview_id": preview["preview_id"],
        "approval_token": preview["approval_token"],
    }


def test_swarm_launch_rejects_boolean_only_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify swarm launch rejects boolean only approval."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "0")

    _patch_hardware_policy(monkeypatch)
    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/launch",
            json={"objective": "Ship launch", "approved": True},
        )

    assert response.status_code == 422
    assert "preview_id" in response.json()["detail"]


def test_swarm_launch_blocks_on_hardware_policy(monkeypatch):
    """Verify swarm launch blocks on hardware policy."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")

    _patch_hardware_policy(monkeypatch, ok=False)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.cancelled = []
    _FakeLaunchClient.cancel_raises_for = set()
    _FakeLaunchClient.fail_role = None
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/swarm/launch",
            json=_approved_payload(client, "Ship launch"),
        )

    assert response.status_code == 409
    assert response.json()["detail"]["blocked"] is True
    assert _FakeLaunchClient.submitted == []


def test_hardware_block_does_not_consume_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify hardware block does not consume approval."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    status = {"ok": True}

    async def fake_hardware_policy():
        """Support fake hardware policy."""
        return _portal_status(ok=status["ok"])["hardware_policy"]

    monkeypatch.setattr(
        portal_server,
        "_portal_hardware_policy_snapshot",
        fake_hardware_policy,
    )
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        status["ok"] = False
        blocked = client.post("/api/swarm/launch", json=payload)
        status["ok"] = True
        retried = client.post("/api/swarm/launch", json=payload)

    assert blocked.status_code == 409
    assert retried.status_code == 200
    assert len(_FakeLaunchClient.submitted) == 5


def test_invalid_token_is_rejected_before_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject forged approval tokens before any Perpetua job POST is attempted."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        payload["approval_token"] = "deadbeef" * 8
        response = client.post("/api/swarm/launch", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid approval_token"
    assert _FakeLaunchClient.submitted == []


@pytest.mark.parametrize(
    ("field", "preview_value", "launch_value"),
    [
        ("objective", "Original objective", "Different objective"),
        ("task_type", "coding", "research"),
        ("optimize_for", "reliability", "speed"),
        ("preferred_device", "auto", "windows"),
    ],
)
def test_launch_rejects_request_drift_from_cached_preview(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    preview_value: str,
    launch_value: str,
) -> None:
    """Verify launch rejects request drift from cached preview."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")

    _patch_hardware_policy(monkeypatch)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)
    preview_request = {
        "objective": "Ship launch",
        "task_type": "coding",
        "optimize_for": "reliability",
        "preferred_device": "auto",
        field: preview_value,
    }

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(
            client,
            preview_request.pop("objective"),
            **preview_request,
        )
        payload[field] = launch_value
        response = client.post("/api/swarm/launch", json=payload)

    assert response.status_code == 422
    assert "preview drift" in response.json()["detail"]
    assert _FakeLaunchClient.submitted == []


def test_legacy_launch_does_not_mint_reusable_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify legacy launch does not mint reusable approval."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "1")

    _patch_hardware_policy(monkeypatch)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/launch",
            json={"objective": "Legacy launch", "approved": True},
        )

    assert response.status_code == 200
    assert "preview_id" not in response.json()["preview"]
    assert "approval_token" not in response.json()["preview"]
    assert swarm_approval._cache == {}
    assert len(_FakeLaunchClient.submitted) == 5


def test_swarm_launch_submits_metadata_compatible_pt_jobs(monkeypatch):
    """Verify swarm launch submits metadata compatible pt jobs."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")

    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.cancelled = []
    _FakeLaunchClient.cancel_raises_for = set()
    _FakeLaunchClient.fail_role = None
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/launch",
            json=_approved_payload(client, "Ship launch"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert len(body["accepted_jobs"]) == 5
    first = _FakeLaunchClient.submitted[0]
    assert first["role"] == "context-agent"
    assert first["task_type"] == "implementation"
    assert first["metadata"]["role"] == "context-agent"
    assert first["metadata"]["artifact_policy"] == "summary_and_refs_only"
    assert first["metadata"]["model"]
    assert "approval_token" not in body["preview"]
    assert "preview_id" not in body["preview"]


def test_swarm_launch_returns_partial_dispatch_failure(monkeypatch):
    """Verify swarm launch returns partial dispatch failure."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")

    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.fail_role = "verifier-agent"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/launch",
            json=_approved_payload(client, "Ship launch"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["failed_jobs"][0]["role"] == "verifier-agent"
    assert "request" not in body["failed_jobs"][0]
    assert body["accepted_jobs"] == []
    assert len(body["cancelled_jobs"]) == 3
    assert _FakeLaunchClient.cancelled == [
        "job-context-agent",
        "job-architect-agent",
        "job-executor-agent",
    ]


def test_swarm_launch_blocks_retry_when_orphans_remain(monkeypatch):
    """Block a second launch when partial dispatch left orphaned Perpetua jobs."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.cancelled = []
    _FakeLaunchClient.cancel_raises_for = {"job-context-agent"}
    _FakeLaunchClient.fail_role = "verifier-agent"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json()["launch_blocked"] is True
    assert first.json()["orphaned_jobs"]
    assert retry.status_code == 422


def test_swarm_launch_blocks_retry_when_cli_containment_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI jobs with unresolved direct-child containment keep the approval consumed."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.fail_role = "verifier-agent"
    _FakeLaunchClient.cancel_worker_kind = "cli"
    _FakeLaunchClient.cancel_containment_state = "unresolved"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json()["orphaned_jobs"] == [
        "job-context-agent",
        "job-architect-agent",
        "job-executor-agent",
    ]
    assert first.json()["launch_blocked"] is True
    assert retry.status_code == 422


def test_swarm_launch_restores_when_cli_containment_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified CLI containment does not block preview restoration on rollback."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.fail_role = "verifier-agent"
    _FakeLaunchClient.cancel_worker_kind = "cli"
    _FakeLaunchClient.cancel_containment_state = "verified"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json().get("launch_blocked") is not True
    assert len(first.json().get("cancelled_jobs", [])) == 3
    assert retry.status_code == 200


def test_swarm_launch_restores_when_containment_fields_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mixed deploy: missing containment fields keeps legacy rollback behavior."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.fail_role = "verifier-agent"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json().get("launch_blocked") is not True


def test_swarm_launch_blocks_retry_when_cancel_is_only_acknowledged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not reuse approval until each PT cancellation is terminally confirmed."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.fail_role = "verifier-agent"
    _FakeLaunchClient.cancel_terminal_state = "running"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert "cancelled_jobs" not in first.json()
    assert first.json()["orphaned_jobs"] == [
        "job-context-agent",
        "job-architect-agent",
        "job-executor-agent",
    ]
    assert first.json()["launch_blocked"] is True
    assert retry.status_code == 422


def test_swarm_launch_blocks_retry_when_accepted_job_has_no_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful but unidentifiable PT submit consumes the approval."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.omit_job_id_for = {"context-agent"}
    _FakeLaunchClient.fail_role = "verifier-agent"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json()["launch_blocked"] is True
    assert first.json()["orphaned_jobs"] == ["unknown:context-agent"]
    assert retry.status_code == 422


def test_swarm_launch_blocks_retry_on_ambiguous_submission(monkeypatch):
    """Keep approval consumed when a submit error leaves PT acceptance unknown."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.fail_role = "context-agent"
    _FakeLaunchClient.fail_role_ambiguous = True
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json()["launch_blocked"] is True
    assert "unknown:context-agent" in first.json()["orphaned_jobs"]
    assert retry.status_code == 422


def test_swarm_launch_retry_after_partial_dispatch_failure(monkeypatch):
    """Allow one retry after rollback when every accepted job was cancelled."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _patch_hardware_policy(monkeypatch)
    _FakeLaunchClient.submitted = []
    _FakeLaunchClient.cancelled = []
    _FakeLaunchClient.fail_role = "verifier-agent"
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship launch")
        first = client.post("/api/swarm/launch", json=payload)
        _FakeLaunchClient.fail_role = None
        _FakeLaunchClient.submitted = []
        retry = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert first.json()["accepted"] is False
    assert retry.status_code == 200
    assert retry.json()["accepted"] is True
    assert len(retry.json()["accepted_jobs"]) == 5


def test_swarm_launch_approval_is_single_use_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP launch consumes approval; a second POST with the same token fails."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")

    _patch_hardware_policy(monkeypatch)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        payload = _approved_payload(client, "Ship once")
        first = client.post("/api/swarm/launch", json=payload)
        replay = client.post("/api/swarm/launch", json=payload)

    assert first.status_code == 200
    assert replay.status_code == 422
    assert len(_FakeLaunchClient.submitted) == 5


def test_non_string_route_hints_are_not_dispatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify non string route hints are not dispatched."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    _FakeLaunchClient.route_payload = {
        "backend_hint": ["lmstudio-mac"],
        "model_hint": {"id": "model-a"},
    }

    _patch_hardware_policy(monkeypatch)
    monkeypatch.setattr(portal_server.httpx, "AsyncClient", _FakeLaunchClient)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/swarm/launch",
            json=_approved_payload(client, "Ship launch"),
        )

    assert response.status_code == 200
    first = _FakeLaunchClient.submitted[0]
    assert first["backend_hint"] == "lmstudio-mac"
    assert "model" not in first["metadata"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task_type", "bogus"),
        ("optimize_for", "bogus"),
        ("preferred_device", "bogus"),
    ],
)
def test_swarm_request_rejects_invalid_enum_fields(field: str, value: str) -> None:
    """Verify swarm request rejects invalid enum fields."""
    with pytest.raises(ValidationError):
        portal_server.SwarmPreviewRequest(objective="Ship launch", **{field: value})


def test_swarm_launch_requires_strict_approval_and_well_formed_credentials() -> None:
    """Verify swarm launch requires strict approval and well formed credentials."""
    with pytest.raises(ValidationError):
        portal_server.SwarmLaunchRequest(
            objective="Ship launch",
            approved="true",
            preview_id="not-an-id",
            approval_token="not-a-token",
        )


def test_swarm_request_rejects_oversized_objective() -> None:
    """Verify swarm request rejects oversized objective."""
    with pytest.raises(ValidationError):
        portal_server.SwarmPreviewRequest(objective="x" * 4001)
