#!/usr/bin/env python3
"""
test_v2_shape.py
================
TDD backport: wire orama-system v0.9.9.9 API models to match the v2 external
shape defined in orama-system/docs/v2/01-kernel-spec.md.

RED tests written first â€” each will fail until api_server.py is updated.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

import api_server
from api_server import OramasysRequest, OramasysResponse


# â”€â”€ session_id on request â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_ultrathink_request_accepts_session_id():
    req = OramasysRequest(task_description="hello", session_id="abc-123")
    assert req.session_id == "abc-123"


def test_ultrathink_request_session_id_defaults_to_none():
    req = OramasysRequest(task_description="hello")
    assert req.session_id is None


# â”€â”€ session_id on response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_ultrathink_response_accepts_session_id():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
        session_id="abc-123",
    )
    assert resp.session_id == "abc-123"


def test_ultrathink_response_session_id_defaults_to_none():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
    )
    assert resp.session_id is None


# â”€â”€ nodes_visited on response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_ultrathink_response_accepts_nodes_visited():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
        nodes_visited=["route_node", "dispatch_node"],
    )
    assert resp.nodes_visited == ["route_node", "dispatch_node"]


def test_ultrathink_response_nodes_visited_defaults_to_empty_list():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
    )
    assert resp.nodes_visited == []


# â”€â”€ retry_count on response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_ultrathink_response_accepts_retry_count():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
        retry_count=2,
    )
    assert resp.retry_count == 2


def test_ultrathink_response_retry_count_defaults_to_zero():
    resp = OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=42,
        reasoning_depth="deep",
        metadata={},
    )
    assert resp.retry_count == 0


# â”€â”€ no pydantic protected-namespace warning for model_hint / model_used â”€â”€â”€â”€â”€â”€â”€

def test_ultrathink_request_no_model_hint_namespace_warning(recwarn):
    OramasysRequest(task_description="test")
    pydantic_warns = [w for w in recwarn.list if "model_hint" in str(w.message)]
    assert pydantic_warns == [], "model_hint triggers Pydantic protected-namespace warning"


def test_ultrathink_response_no_model_used_namespace_warning(recwarn):
    OramasysResponse(
        status="success",
        result="ok",
        model_used="some-model",
        execution_time_ms=1,
        reasoning_depth="standard",
        metadata={},
    )
    pydantic_warns = [w for w in recwarn.list if "model_used" in str(w.message)]
    assert pydantic_warns == [], "model_used triggers Pydantic protected-namespace warning"


# â”€â”€ /oramasys endpoint includes session_id and nodes_visited in JSON output â”€

def test_http_endpoint_returns_session_id_and_nodes_visited(monkeypatch):
    """End-to-end: POST /oramasys with session_id â†’ response JSON has both fields."""
    from fastapi.testclient import TestClient

    async def fake_call(prompt, model, max_tokens, temperature):
        return "v2 output", "http://localhost:1234"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call)

    client = TestClient(api_server.app)
    resp = client.post("/oramasys", json={
        "task_description": "test v2 shape",
        "session_id": "sess-xyz",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-xyz"
    assert "nodes_visited" in body
    assert isinstance(body["nodes_visited"], list)
    assert "retry_count" in body
    assert isinstance(body["retry_count"], int)


# â”€â”€ qwen3.5-9b-mlx thinking-model response extraction contract â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Documents the expected behavior for the future real LM Studio HTTP client.
# The stub _call_with_fallback is mocked here; the real implementation must
# extract `content` not `reasoning_content` from thinking model responses.

def _extract_content_from_lm_studio_response(response_json: dict) -> str:
    """Reference extractor: ignores reasoning_content, returns final content."""
    msg = response_json["choices"][0]["message"]
    return msg.get("content", "") or ""


def test_extract_content_ignores_reasoning_content():
    thinking_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "\n\nOK",
                "reasoning_content": "Thinking Process:\n1. The user wants OK\n2. I reply OK",
            },
            "finish_reason": "stop",
        }]
    }
    assert _extract_content_from_lm_studio_response(thinking_response) == "\n\nOK"


def test_extract_content_returns_empty_on_truncated_thinking():
    """When max_tokens is too low, content is empty (thinking didn't finish)."""
    truncated_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "reasoning_content": "Thinking Process:\n1. An",
            },
            "finish_reason": "length",
        }]
    }
    assert _extract_content_from_lm_studio_response(truncated_response) == ""


def test_extract_content_handles_non_thinking_model():
    """Standard (non-thinking) model: content is present, no reasoning_content."""
    standard_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Hello!",
            },
            "finish_reason": "stop",
        }]
    }
    assert _extract_content_from_lm_studio_response(standard_response) == "Hello!"

