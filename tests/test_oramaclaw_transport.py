from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pytest

from oramaclaw.transport import (
    GatewayTransport,
    OfflineTransport,
    RunResult,
    make_transport,
)
from oramaclaw.types import (
    ConfigTarget,
    GatewayUnavailable,
    MergePolicy,
    OfflineOperationNotAllowed,
    Resource,
    ResourceKind,
    StaleConfiguration,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _target(tmp_path: Path) -> ConfigTarget:
    cfg = tmp_path / "openclaw.json"
    cfg.write_text("{}")
    return ConfigTarget(
        workspace_root=tmp_path,
        config_path=cfg,
        state_dir=tmp_path / "state",
    )


def _resource(
    kind: ResourceKind = ResourceKind.PROVIDER,
    identifier: str = "test-provider",
    spec: dict | None = None,
) -> Resource:
    return Resource(
        kind=kind,
        identifier=identifier,
        manager="oramaclaw",
        spec=spec or {"baseUrl": "http://localhost:1234/v1"},
        managed_paths=("/models/providers/test-provider",),
        policy=MergePolicy.STRICT,
    )


class FakeRunner:
    """Configurable fake command runner for transport tests."""

    def __init__(self, responses: dict[str, RunResult] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[list[str]] = []

    def set(self, key: str, result: RunResult) -> None:
        self._responses[key] = result

    def run(self, argv: Sequence[str], *, capture_output: bool = True, timeout: float = 15.0) -> RunResult:
        self.calls.append(list(argv))
        key = " ".join(argv[:3])
        if key in self._responses:
            return self._responses[key]
        # Default: success with empty JSON body
        return RunResult(0, "{}", "")


def _ok(stdout: str = "{}") -> RunResult:
    return RunResult(0, stdout, "")

def _err(rc: int, stderr: str = "error") -> RunResult:
    return RunResult(rc, "", stderr)


# ── GatewayTransport.gateway_config_get ──────────────────────────────────────

def test_gateway_config_get_success(tmp_path):
    runner = FakeRunner({"openclaw config get": _ok(
        json.dumps({"configuration": {"agents": {}}, "baseHash": "abc123"})
    )})
    t = _target(tmp_path)
    result = GatewayTransport(runner).gateway_config_get(t)
    assert result.base_hash == "abc123"
    assert result.configuration == {"agents": {}}


def test_gateway_config_get_failure_raises_unavailable(tmp_path):
    runner = FakeRunner({"openclaw config get": _err(1, "connection refused")})
    with pytest.raises(GatewayUnavailable, match="connection refused"):
        GatewayTransport(runner).gateway_config_get(_target(tmp_path))


def test_gateway_config_get_non_json_raises_unavailable(tmp_path):
    runner = FakeRunner({"openclaw config get": _ok("not json at all")})
    with pytest.raises(GatewayUnavailable, match="non-JSON"):
        GatewayTransport(runner).gateway_config_get(_target(tmp_path))


# ── GatewayTransport.gateway_config_apply ────────────────────────────────────

def test_gateway_config_apply_success(tmp_path):
    runner = FakeRunner({"openclaw config set": _ok(
        json.dumps({"transactionId": "tx-xyz", "baseHash": "new-hash"})
    )})
    t = _target(tmp_path)
    result = GatewayTransport(runner).gateway_config_apply(t, {"k": "v"}, "old-hash")
    assert result.transaction_id == "tx-xyz"
    assert result.base_hash == "new-hash"


def test_gateway_config_apply_stale_raises(tmp_path):
    runner = FakeRunner({"openclaw config set": _err(409, "stale base hash")})
    with pytest.raises(StaleConfiguration):
        GatewayTransport(runner).gateway_config_apply(_target(tmp_path), {}, "stale")


def test_gateway_config_apply_rejected_raises(tmp_path):
    from oramaclaw.types import GatewayRejected
    runner = FakeRunner({"openclaw config set": _err(403, "forbidden")})
    with pytest.raises(GatewayRejected):
        GatewayTransport(runner).gateway_config_apply(_target(tmp_path), {}, "h")


def test_gateway_config_apply_generic_failure_raises_unavailable(tmp_path):
    runner = FakeRunner({"openclaw config set": _err(1, "unknown error")})
    with pytest.raises(GatewayUnavailable):
        GatewayTransport(runner).gateway_config_apply(_target(tmp_path), {}, "h")


# ── OfflineTransport ──────────────────────────────────────────────────────────

def test_offline_apply_provider_writes_to_config(tmp_path):
    t = _target(tmp_path)
    r = _resource(ResourceKind.PROVIDER, "lmstudio-mac", {"baseUrl": "http://localhost:1234/v1"})
    OfflineTransport().offline_apply_provider(t, r)
    cfg = json.loads(t.config_path.read_text())
    assert cfg["models"]["providers"]["lmstudio-mac"]["baseUrl"] == "http://localhost:1234/v1"


def test_offline_apply_provider_merges_existing(tmp_path):
    t = _target(tmp_path)
    t.config_path.write_text(json.dumps({
        "models": {"providers": {"other": {"baseUrl": "http://other/v1"}}}
    }))
    r = _resource(ResourceKind.PROVIDER, "new-one", {"baseUrl": "http://new/v1"})
    OfflineTransport().offline_apply_provider(t, r)
    cfg = json.loads(t.config_path.read_text())
    assert "other" in cfg["models"]["providers"]
    assert "new-one" in cfg["models"]["providers"]


def test_offline_create_agent_writes_definition(tmp_path):
    t = _target(tmp_path)
    r = _resource(ResourceKind.AGENT, "my-agent", {"model": "ollama/qwen3.5:9b"})
    OfflineTransport().offline_create_agent(t, r)
    cfg = json.loads(t.config_path.read_text())
    assert cfg["agents"]["definitions"]["my-agent"]["model"] == "ollama/qwen3.5:9b"


def test_offline_create_agent_existing_raises(tmp_path):
    t = _target(tmp_path)
    t.config_path.write_text(json.dumps({"agents": {"definitions": {"my-agent": {}}}}))
    r = _resource(ResourceKind.AGENT, "my-agent", {})
    with pytest.raises(OfflineOperationNotAllowed, match="my-agent"):
        OfflineTransport().offline_create_agent(t, r)


def test_offline_rejects_non_provider_non_agent(tmp_path):
    t = _target(tmp_path)
    r = _resource(ResourceKind.BINDING, "x", {})
    with pytest.raises(OfflineOperationNotAllowed):
        OfflineTransport().offline_apply_provider(t, r)


# ── make_transport ────────────────────────────────────────────────────────────

def test_make_transport_force_offline(tmp_path):
    t = _target(tmp_path)
    transport = make_transport(t, force_offline=True)
    assert isinstance(transport, OfflineTransport)


def test_make_transport_gateway_reachable(tmp_path):
    runner = FakeRunner({"openclaw status --json": _ok('{"ok":true}')})
    t = _target(tmp_path)
    transport = make_transport(t, runner=runner)
    assert isinstance(transport, GatewayTransport)


def test_make_transport_gateway_unreachable_falls_back(tmp_path):
    runner = FakeRunner({"openclaw status --json": _err(1, "not running")})
    t = _target(tmp_path)
    transport = make_transport(t, runner=runner)
    assert isinstance(transport, OfflineTransport)
