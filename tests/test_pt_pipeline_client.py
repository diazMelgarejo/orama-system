"""Tests for the orama-side PT Tier-5 pipeline client.

Design constraints verified here:
- Client calls /pipelines/{recipe}/run on PT — NEVER /orchestrate (loop risk)
- Authorization Bearer header is always injected from PT_PIPELINE_TOKEN
- Idempotency-Key is a UUIDv4 string sent on every request
- 402 / 403 / 4xx errors surface as specific exceptions, not silent failures
- No fallback to internal orama dispatch (would bypass PT approval + budget)
- Client is stateless: each call is independent
"""
from __future__ import annotations

import re
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orama_system.pt_pipeline_client import (
    PipelineAuthError,
    PipelineBudgetError,
    PipelineCallError,
    Tier5PipelineClient,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _mock_response(status: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    return resp


def _ok_body() -> dict:
    return {
        "status": "completed",
        "recipe": "classify_then_generate",
        "output": "final answer",
        "requested_tokens": 512,
        "cost_reservation_usd": 0.25,
        "settled_microusd": 100000,
        "run_id": "run-abc",
    }


# ── URL contract ───────────────────────────────────────────────────────────────

class TestUrlContract:
    """The client must hit /pipelines/{recipe}/run, not /orchestrate."""

    @pytest.mark.asyncio
    async def test_calls_pipelines_run_not_orchestrate(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-abc-123",
            )

        assert "/pipelines/classify_then_generate/run" in captured["url"]
        assert "/orchestrate" not in captured["url"], (
            "Client MUST NOT call /orchestrate — that endpoint calls back to orama and creates a loop"
        )

    @pytest.mark.asyncio
    async def test_url_does_not_contain_oramasys(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["url"] = url
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-abc-123",
            )

        assert "oramasys" not in captured["url"]
        assert "orchestrate" not in captured["url"]


# ── Auth header ────────────────────────────────────────────────────────────────

class TestAuthHeader:
    """Bearer token from PT_PIPELINE_TOKEN must appear on every call."""

    @pytest.mark.asyncio
    async def test_bearer_token_sent_from_env(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "secret-token-xyz")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-auth-00",
            )

        assert captured["headers"].get("Authorization") == "Bearer secret-token-xyz"

    @pytest.mark.asyncio
    async def test_explicit_token_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "env-token")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000", token="explicit-token")
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-explicit-00",
            )

        assert captured["headers"].get("Authorization") == "Bearer explicit-token"


# ── Idempotency-Key ────────────────────────────────────────────────────────────

class TestIdempotencyKey:
    """Every call must carry a UUIDv4 Idempotency-Key header."""

    @pytest.mark.asyncio
    async def test_idempotency_key_is_uuid4(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-idem-00",
            )

        key = captured["headers"].get("Idempotency-Key", "")
        assert _UUID4_RE.match(key), f"Expected UUIDv4, got: {key!r}"

    @pytest.mark.asyncio
    async def test_explicit_idempotency_key_is_passed_through(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        fixed_key = str(uuid.uuid4())
        captured: dict[str, Any] = {}

        async def fake_post(url, **kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            await client.run(
                recipe="classify_then_generate",
                prompt="test",
                trace_id="trace-idem-01",
                idempotency_key=fixed_key,
            )

        assert captured["headers"].get("Idempotency-Key") == fixed_key


# ── Error mapping ──────────────────────────────────────────────────────────────

class TestErrorMapping:
    """HTTP error codes must map to typed exceptions, never swallowed."""

    @pytest.mark.asyncio
    async def test_401_raises_pipeline_auth_error(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "bad-token")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")

        async def fake_post(url, **kwargs):
            return _mock_response(401, {"detail": "Unauthorized"})

        with patch.object(client._http, "post", side_effect=fake_post):
            with pytest.raises(PipelineAuthError):
                await client.run(
                    recipe="classify_then_generate",
                    prompt="test",
                    trace_id="trace-err-401",
                )

    @pytest.mark.asyncio
    async def test_403_raises_pipeline_auth_error(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")

        async def fake_post(url, **kwargs):
            return _mock_response(403, {"detail": "Approval invalid"})

        with patch.object(client._http, "post", side_effect=fake_post):
            with pytest.raises(PipelineAuthError):
                await client.run(
                    recipe="classify_then_generate",
                    prompt="test",
                    trace_id="trace-err-403",
                )

    @pytest.mark.asyncio
    async def test_402_raises_pipeline_budget_error(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")

        async def fake_post(url, **kwargs):
            return _mock_response(402, {"detail": "Daily budget cannot cover reservation"})

        with patch.object(client._http, "post", side_effect=fake_post):
            with pytest.raises(PipelineBudgetError):
                await client.run(
                    recipe="classify_then_generate",
                    prompt="test",
                    trace_id="trace-err-402",
                )

    @pytest.mark.asyncio
    async def test_5xx_raises_pipeline_call_error(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")

        async def fake_post(url, **kwargs):
            return _mock_response(503, {"detail": "Service unavailable"})

        with patch.object(client._http, "post", side_effect=fake_post):
            with pytest.raises(PipelineCallError):
                await client.run(
                    recipe="classify_then_generate",
                    prompt="test",
                    trace_id="trace-err-503",
                )


# ── Success contract ───────────────────────────────────────────────────────────

class TestSuccessContract:
    """Successful calls return the expected output fields."""

    @pytest.mark.asyncio
    async def test_returns_output_and_cost(self, monkeypatch):
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")

        async def fake_post(url, **kwargs):
            return _mock_response(200, _ok_body())

        with patch.object(client._http, "post", side_effect=fake_post):
            result = await client.run(
                recipe="classify_then_generate",
                prompt="hello world",
                trace_id="trace-ok-00",
            )

        assert result["output"] == "final answer"
        assert result["status"] == "completed"
        assert result["recipe"] == "classify_then_generate"

    @pytest.mark.asyncio
    async def test_stage_outputs_are_not_in_result(self, monkeypatch):
        """Intermediate stage outputs must never be forwarded to the caller —
        they can contain internal classification context that orama should not
        re-use to drive further inference without a new approval."""
        monkeypatch.setenv("PT_PIPELINE_TOKEN", "tok")
        client = Tier5PipelineClient(pt_base_url="http://localhost:8000")
        body = _ok_body()
        body["stage_outputs"] = {"classify": "internal routing hint", "generate": "final answer"}

        async def fake_post(url, **kwargs):
            return _mock_response(200, body)

        with patch.object(client._http, "post", side_effect=fake_post):
            result = await client.run(
                recipe="classify_then_generate",
                prompt="hello world",
                trace_id="trace-ok-01",
            )

        assert "stage_outputs" not in result, (
            "stage_outputs MUST NOT be forwarded to callers — intermediate "
            "context could be used to bypass approval checks"
        )


# ── No-loop invariant (static analysis) ────────────────────────────────────────

def test_client_module_does_not_import_orama_bridge():
    """Verify at import time that pt_pipeline_client.py contains no `import`
    statement that pulls in orama_bridge or any other module that calls back
    to orama.  A future edit adding 'import orchestrator.orama_bridge' would
    create the exact PT→orama→PT loop this client was designed to prevent."""
    import importlib
    import sys

    mod_name = "orama_system.pt_pipeline_client"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = importlib.import_module(mod_name)
    source = mod.__spec__.origin if mod.__spec__ else None

    if source:
        with open(source) as f:
            lines = f.readlines()

        import_lines = [ln.strip() for ln in lines if ln.strip().startswith(("import ", "from "))]
        import_text = "\n".join(import_lines)

        assert "orama_bridge" not in import_text, (
            "pt_pipeline_client.py must not import orama_bridge — "
            "that would allow orama-side dispatch back to orama via PT"
        )
        assert "call_oramasys" not in import_text, (
            "pt_pipeline_client.py must not import orama dispatch functions"
        )
