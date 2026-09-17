#!/usr/bin/env python3
"""
test_api_server.py
==================
Request/response tests for the HTTP bridge.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

import orama_system.api_server as api_server
from bin.shared.bridge_contract import (
    optimize_for_to_reasoning_depth,
    reasoning_depth_to_optimize_for,
)


class _FakeHTTPResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, **kwargs):
        return _FakeHTTPResponse(200)

    async def post(self, url: str, **kwargs):
        return _FakeHTTPResponse(200)


def test_optimize_for_to_reasoning_depth_mapping_is_exact():
    assert optimize_for_to_reasoning_depth("reliability") == "ultra"
    assert optimize_for_to_reasoning_depth("creativity") == "deep"
    assert optimize_for_to_reasoning_depth("speed") == "standard"

    assert reasoning_depth_to_optimize_for("ultra").value == "reliability"
    assert reasoning_depth_to_optimize_for("deep").value == "creativity"
    assert reasoning_depth_to_optimize_for("standard").value == "speed"


def test_http_bridge_maps_optimize_for_to_reasoning_depth(monkeypatch):
    captured = {}

    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        return "mapped output", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "optimize_for": "reliability",
                "task_type": "planning",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"] == "mapped output"
    assert body["reasoning_depth"] == "ultra"
    assert body["model_used"] == api_server.DEFAULT_MODEL
    assert body["metadata"]["mapped_optimize_for"] == "reliability"
    assert body["metadata"]["mapping_source"] == "optimize_for"
    assert body["metadata"]["bridge_mode"] == "http_primary"
    assert "ultra-depth reasoning" in captured["prompt"]


def test_http_bridge_prefers_explicit_reasoning_depth(monkeypatch):
    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "explicit depth output", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Review a code migration plan",
                "reasoning_depth": "standard",
                "optimize_for": "reliability",
                "task_type": "planning",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reasoning_depth"] == "standard"
    assert body["model_used"] == api_server.FAST_MODEL
    assert body["metadata"]["mapped_optimize_for"] == "speed"
    assert body["metadata"]["mapping_source"] == "reasoning_depth"


def test_http_bridge_preserves_legacy_default_reasoning_depth(monkeypatch):
    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "legacy default output", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Analyze a backup path",
                "task_type": "analysis",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reasoning_depth"] == "standard"
    assert body["model_used"] == api_server.FAST_MODEL
    assert body["metadata"]["mapped_optimize_for"] == "speed"
    assert body["metadata"]["mapping_source"] == "default"


def test_http_bridge_honors_model_hint(monkeypatch):
    captured = {}

    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        captured["model"] = model
        return "hinted output", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Analyze failover design",
                "task_type": "analysis",
                "model_hint": "custom-model",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "hinted output"
    assert body["model_used"] == "custom-model"
    assert body["metadata"]["model_hint_used"] is True
    assert captured["model"] == "custom-model"


def test_legacy_ultrathink_route_shims_to_oramasys(monkeypatch):
    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "legacy shim output", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/ultrathink",
            json={"task_description": "verify old route compatibility"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "legacy shim output"
    assert body["nodes_visited"] == ["oramasys_node"]


@pytest.mark.integration
def test_http_bridge_uses_guarded_pt_pipeline_when_approval_refs_are_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {}

    class FakePipelineClient:
        async def run(self, **kwargs: Any) -> Any:
            calls.update(kwargs)
            return type(
                "Result",
                (),
                {
                    "output": "tiered output",
                    "models_used": {
                        "classify": "fast-ready",
                        "generate": "strong-ready",
                    },
                },
            )()

    monkeypatch.setattr(api_server, "PTPipelineClient", FakePipelineClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "tiered output"
    assert body["model_used"] == "strong-ready"
    assert "pipeline_models" not in body["metadata"]
    assert body["metadata"]["pipeline_replay"] is False
    assert calls["trace_id"] == "approved-trace"


@pytest.mark.integration
def test_nested_control_plane_call_requires_pipeline_approval_refs() -> None:
    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            headers={"X-Control-Plane-Depth": "1"},
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
            },
        )

    assert response.status_code == 409
    assert response.json()["error"] == "CONTROL_PLANE_LOOP"


@pytest.mark.integration
def test_control_plane_depth_at_ceiling_is_rejected_even_with_valid_pipeline_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reproduces CodeRabbit review 5234774766 (PR#363), Finding 1.

    MAX_CONTROL_PLANE_DEPTH declares a ceiling, but the only depth gate
    was "reject depth>=1 lacking pipeline refs" -- a caller that always
    supplies pipeline_trace_id/pipeline_idempotency_key (attacker-suppliable
    request fields, no depth check attached) sails past it. A request
    arriving at exactly the declared ceiling must be rejected before ever
    calling PTPipelineClient.run and forwarding control_plane_depth one
    past the ceiling.
    """
    calls = {}

    class FakePipelineClient:
        async def run(self, **kwargs: Any) -> Any:
            calls.update(kwargs)
            return type(
                "Result",
                (),
                {"output": "should not be reached", "models_used": {}, "replay": False},
            )()

    monkeypatch.setattr(api_server, "PTPipelineClient", FakePipelineClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            headers={"X-Control-Plane-Depth": str(api_server.MAX_CONTROL_PLANE_DEPTH)},
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 409
    assert response.json()["error"] == "CONTROL_PLANE_LOOP"
    assert calls == {}


@pytest.mark.integration
def test_control_plane_depth_one_below_ceiling_is_forwarded_at_the_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boundary companion to the ceiling-rejection test above: depth ==

    MAX_CONTROL_PLANE_DEPTH - 1 with valid pipeline refs must still be
    allowed through, forwarded as exactly MAX_CONTROL_PLANE_DEPTH -- proves
    the new check rejects only at/after the ceiling, not one below it.
    """
    calls = {}

    class FakePipelineClient:
        async def run(self, **kwargs: Any) -> Any:
            calls.update(kwargs)
            return type(
                "Result",
                (),
                {"output": "tiered output", "models_used": {"generate": "strong-ready"}, "replay": False},
            )()

    monkeypatch.setattr(api_server, "PTPipelineClient", FakePipelineClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            headers={"X-Control-Plane-Depth": str(api_server.MAX_CONTROL_PLANE_DEPTH - 1)},
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 200
    assert calls["control_plane_depth"] == api_server.MAX_CONTROL_PLANE_DEPTH


@pytest.mark.integration
def test_pipeline_approval_references_must_be_supplied_together() -> None:
    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
            },
        )

    assert response.status_code == 422


@pytest.mark.integration
def test_pipeline_idempotency_key_also_requires_trace_id() -> None:
    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 422


@pytest.mark.integration
def test_http_bridge_preserves_safe_pipeline_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePipelineClient:
        async def run(self, **kwargs: Any) -> Any:
            return type(
                "Result",
                (),
                {
                    "output": "",
                    "models_used": {},
                    "replay": True,
                },
            )()

    monkeypatch.setattr(api_server, "PTPipelineClient", FakePipelineClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 200
    assert response.json()["result"] == ""
    assert response.json()["metadata"]["pipeline_replay"] is True


@pytest.mark.integration
def test_http_bridge_reports_pt_pipeline_failure_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePipelineClient:
        async def run(self, **kwargs: Any) -> Any:
            raise api_server.PTPipelineError("PT pipeline request failed")

    monkeypatch.setattr(api_server, "PTPipelineClient", FakePipelineClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.post(
            "/oramasys",
            json={
                "task_description": "Design a resilient orchestration layer",
                "task_type": "planning",
                "pipeline_trace_id": "approved-trace",
                "pipeline_idempotency_key": "4ee06db8-8424-4a82-9654-d24c9597ac2e",
            },
        )

    assert response.status_code == 503
    assert response.json()["error"] == "PIPELINE_UNAVAILABLE"


def test_http_health_endpoint(monkeypatch):
    monkeypatch.setattr(api_server.httpx, "AsyncClient", _FakeAsyncClient)

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["bridge_mode"] == "http_primary"
    assert body["pt_runtime"]["available"] is False
    assert "gateway_ready" in body["pt_runtime"]
    assert "hardware_policy" in body


def test_runtime_state_reads_pt_payload(monkeypatch, tmp_path):
    runtime_path = tmp_path / "pt-runtime.json"
    runtime_path.write_text(
        json.dumps(
            {
                "gateway": {"gateway_ready": True},
                "routing": {"distributed": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PT_RUNTIME_STATE", str(runtime_path))

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.get("/runtime-state")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["runtime"]["gateway_ready"] is True
    assert body["runtime"]["distributed"] is True


def test_hardware_mismatch_mac_provider_with_windows_model(monkeypatch):
    """lmstudio-mac + Windows-only model → must return 400 HARDWARE_MISMATCH."""
    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "should not reach here", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    # Mock the resolver to raise HardwareAffinityError for NEVER_MAC models
    original_resolver = api_server._policy_resolver
    mock_resolver = type('MockResolver', (), {
        'initialize': lambda self: None,
        'check_affinity': lambda self, m, p: (
            None if p != "mac" or "qwen3.5-27b" not in m.lower()
            else (_ for _ in ()).throw(
                api_server.HardwareAffinityError(
                    f"[alphaclaw] Fatal: '{m}' is NEVER_MAC. Assign to lmstudio-win only."
                )
            )
        ),
        'expected_platform_for_model': lambda self, m: None,
        'source': 'mock',
        'pt_available': True,
    })()
    api_server._policy_resolver = mock_resolver

    try:
        with TestClient(api_server.app, raise_server_exceptions=True) as client:
            response = client.post(
                "/oramasys",
                json={
                    "task_description": "Write a sorting algorithm",
                    "task_type": "code",
                    "model_hint": "lmstudio-mac/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2",
                },
            )

        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "HARDWARE_MISMATCH"
        assert "NEVER_MAC" in body["detail"]
    finally:
        api_server._policy_resolver = original_resolver


def test_hardware_mismatch_win_provider_with_mac_model(monkeypatch):
    """lmstudio-win + Mac-only MLX model → must return 400 HARDWARE_MISMATCH."""
    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "should not reach here", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    # Mock the resolver to raise HardwareAffinityError for NEVER_WIN models
    original_resolver = api_server._policy_resolver
    mock_resolver = type('MockResolver', (), {
        'initialize': lambda self: None,
        'check_affinity': lambda self, m, p: (
            None if p != "win" or "qwen3.5-9b-mlx" not in m.lower()
            else (_ for _ in ()).throw(
                api_server.HardwareAffinityError(
                    f"[alphaclaw] Fatal: '{m}' is NEVER_WIN. Assign to lmstudio-mac only."
                )
            )
        ),
        'expected_platform_for_model': lambda self, m: None,
        'source': 'mock',
        'pt_available': True,
    })()
    api_server._policy_resolver = mock_resolver

    try:
        with TestClient(api_server.app, raise_server_exceptions=True) as client:
            response = client.post(
                "/oramasys",
                json={
                    "task_description": "Run MLX inference",
                    "task_type": "code",
                    "model_hint": "lmstudio-win/Qwen3.5-9B-MLX-4bit",
                },
            )

        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "HARDWARE_MISMATCH"
        assert "NEVER_WIN" in body["detail"]
    finally:
        api_server._policy_resolver = original_resolver


def test_fail_closed_when_perpetuatoolsroot_missing(monkeypatch):
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    original_resolver = api_server._policy_resolver
    mock_resolver = type("MockResolver", (), {
        "initialize": lambda self: None,
        "check_affinity": lambda self, m, p: None,
        "expected_platform_for_model": lambda self, m: None,
        "source": "disabled-no-cache",
        "pt_available": False,
    })()
    api_server._policy_resolver = mock_resolver

    try:
        with TestClient(api_server.app, raise_server_exceptions=True) as client:
            response = client.post(
                "/oramasys",
                json={
                    "task_description": "Run routed check",
                    "task_type": "code",
                    "model_hint": "lmstudio-mac/any-model",
                },
            )
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "POLICY_UNAVAILABLE"
    finally:
        api_server._policy_resolver = original_resolver


def test_fail_closed_when_platform_and_provider_hint_both_present(monkeypatch):
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    original_resolver = api_server._policy_resolver
    mock_resolver = type("MockResolver", (), {
        "initialize": lambda self: None,
        "check_affinity": lambda self, m, p: None,
        "expected_platform_for_model": lambda self, m: None,
        "source": "disabled-no-cache",
        "pt_available": False,
    })()
    api_server._policy_resolver = mock_resolver

    try:
        with TestClient(api_server.app, raise_server_exceptions=True) as client:
            response = client.post(
                "/oramasys",
                json={
                    "task_description": "Run routed check",
                    "task_type": "code",
                    "platform": "mac",
                    "model_hint": "lmstudio-mac/any-model",
                },
            )
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "POLICY_UNAVAILABLE"
    finally:
        api_server._policy_resolver = original_resolver


def test_fail_closed_when_only_legacy_path_env_is_set(monkeypatch):
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", "/tmp/not-a-real-pt-root")

    original_resolver = api_server._policy_resolver
    mock_resolver = type("MockResolver", (), {
        "initialize": lambda self: None,
        "check_affinity": lambda self, m, p: None,
        "expected_platform_for_model": lambda self, m: None,
        "source": "disabled-no-cache",
        "pt_available": False,
    })()
    api_server._policy_resolver = mock_resolver

    try:
        with TestClient(api_server.app, raise_server_exceptions=True) as client:
            response = client.post(
                "/oramasys",
                json={
                    "task_description": "Run routed check",
                    "task_type": "code",
                    "model_hint": "lmstudio-win/any-model",
                },
            )
        assert response.status_code == 400
        assert response.json()["error"] == "POLICY_UNAVAILABLE"
    finally:
        api_server._policy_resolver = original_resolver

