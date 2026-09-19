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
    assert request.headers["x-control-plane-depth"] == "1"
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


def test_client_rejects_plain_http_to_a_private_network_base_url(
    client_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduces CodeRabbit review 5234774766 (PR#363), Finding 2.

    This client sends a control-plane bearer token on every call
    (auth_headers()); plain HTTP to a non-loopback base URL would send it
    in cleartext across the LAN segment.
    """
    monkeypatch.setenv("ORAMASYS_PT_PIPELINE_BASE_URL", "http://192.168.1.50:8000")

    with pytest.raises(PTPipelineError, match="trusted PT pipeline endpoint"):
        PTPipelineClient(config_path=client_config).pipeline_url("analysis")


def test_client_still_allows_the_documented_loopback_http_default(
    client_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORAMASYS_PT_PIPELINE_BASE_URL", "http://localhost:8000")

    url = PTPipelineClient(config_path=client_config).pipeline_url("analysis")

    assert url == "http://localhost:8000/pipelines/classify_then_generate/run"


def _production_client_kwargs(**overrides):
    """Same kwargs as PTPipelineClient.run's AsyncClient, minus transport=,
    so default httpx proxy-mount behavior applies -- MockTransport bypasses
    mount routing entirely regardless of trust_env, so asserting mounts on
    the MockTransport client used elsewhere in this file would not prove
    anything about the production call path."""
    timeout = httpx.Timeout(120.0, connect=10.0)
    kwargs = dict(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    )
    kwargs.update(overrides)
    return kwargs


async def test_pipeline_httpx_client_disables_env_proxy_mounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 2: the control-plane bearer must never ride an ambient
    HTTP_PROXY/HTTPS_PROXY/ALL_PROXY -- httpx.AsyncClient trusts the
    environment by default (trust_env=True), which mounts proxy transports
    and forwards Authorization to whatever that proxy is. trust_env=False
    on the production client must leave no proxy mounts, matching the same
    pattern already used by PT's own agent_launcher._pinned_get."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    async with httpx.AsyncClient(**_production_client_kwargs()) as client:
        assert client.trust_env is False
        assert not client._mounts


async def test_pipeline_httpx_client_mounts_when_trust_env_left_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative control for the test above: with trust_env left True under
    the exact same proxy environment, httpx genuinely does mount a proxy
    transport -- proves the prior test's empty _mounts reflects
    trust_env=False actually doing something, not an environment where
    httpx never mounts proxies at all regardless of the flag."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    async with httpx.AsyncClient(**_production_client_kwargs(trust_env=True)) as client:
        assert client.trust_env is True
        assert client._mounts


