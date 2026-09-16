from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from orama_system.pt_pipeline_client import PTPipelineClient, PTPipelineError


@pytest.fixture
def client_config(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline-routing.yml"
    path.write_text(
        """version: 1
enabled: true
pt_base_url: http://127.0.0.1:8000
recipes:
  analysis: classify_then_generate
  planning: classify_then_generate
""",
        encoding="utf-8",
    )
    return path


@pytest.mark.asyncio
async def test_client_calls_only_guarded_pt_pipeline_with_auth_and_idempotency(
    client_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PT_CONTROL_PLANE_TOKEN", "pt-test-token")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "output": "final",
                "models_used": {
                    "classify": "fast-ready",
                    "generate": "strong-ready",
                },
            },
        )

    result = await PTPipelineClient(
        config_path=client_config,
        transport=httpx.MockTransport(handler),
    ).run(
        task_type="analysis",
        prompt="do the work",
        trace_id="approved-trace",
        idempotency_key="4ee06db8-8424-4a82-9654-d24c9597ac2e",
    )

    request = requests[0]
    assert request.headers["authorization"] == "Bearer pt-test-token"
    assert request.headers["idempotency-key"] == "4ee06db8-8424-4a82-9654-d24c9597ac2e"
    assert request.url.path == "/pipelines/classify_then_generate/run"
    assert result.output == "final"
    assert result.models_used["generate"] == "strong-ready"


def test_client_has_no_orchestrate_route_fallback(client_config: Path) -> None:
    client = PTPipelineClient(config_path=client_config)

    assert "/orchestrate" not in client.pipeline_url("analysis")


@pytest.mark.asyncio
async def test_client_accepts_idempotent_replay_without_redispatching(
    client_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PT_CONTROL_PLANE_TOKEN", "pt-test-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": "",
                "models_used": {},
                "replay": True,
            },
        )

    result = await PTPipelineClient(
        config_path=client_config,
        transport=httpx.MockTransport(handler),
    ).run(
        task_type="analysis",
        prompt="do the work",
        trace_id="approved-trace",
        idempotency_key="4ee06db8-8424-4a82-9654-d24c9597ac2e",
    )

    assert result.output == ""
    assert result.models_used == {}
    assert result.replay is True


def test_client_pipeline_url_stays_private_when_public_model_endpoints_are_allowed(
    client_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALLOW_PUBLIC_MODEL_ENDPOINTS", "1")
    monkeypatch.setenv("ORAMASYS_PT_PIPELINE_BASE_URL", "https://example.com")

    with pytest.raises(PTPipelineError, match="trusted PT pipeline endpoint"):
        PTPipelineClient(config_path=client_config).pipeline_url("analysis")
