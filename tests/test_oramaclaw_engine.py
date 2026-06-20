"""Tests for oramaclaw.engine.ControlEngine.apply_manifest().

These use a fake transport (no real ``openclaw`` CLI) and a fake
``plan_resource`` (monkeypatched onto ``oramaclaw.engine``) so the engine's
state machine can be exercised without touching the merge implementation,
which is written in parallel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from oramaclaw.engine import ControlEngine
from oramaclaw.types import (
    ConfigTarget,
    ControlManifest,
    GatewayApplyResult,
    GatewayConfig,
    GatewayUnavailable,
    MergePolicy,
    Resource,
    ResourceKind,
    StaleConfiguration,
)


# ── Fake merge plan structures ───────────────────────────────────────────────

@dataclass
class FakeFieldAction:
    managed_path: str
    kind: str
    desired_value: object = None
    fingerprint: str = "fp"


@dataclass
class FakeMergePlan:
    resource_key: str
    actions: tuple = ()
    conflicts: tuple = ()
    auto_woven: tuple = ()


def _plan_factory(kind: str):
    """Return a ``plan_resource`` replacement that yields actions of ``kind``."""

    def _plan(resource, live_config, store):
        key = f"{resource.kind.value}:{resource.identifier}"
        action = FakeFieldAction(
            managed_path="/effort",
            kind=kind,
            desired_value="high",
            fingerprint="fp-desired",
        )
        return FakeMergePlan(resource_key=key, actions=(action,))

    return _plan


# ── Fake transport ───────────────────────────────────────────────────────────

class FakeTransport:
    def __init__(self, config=None, apply_result=None, raise_on_get=None, raise_on_apply=None):
        self.config = config or {}
        self.apply_result = apply_result
        self.raise_on_get = raise_on_get
        self.raise_on_apply = raise_on_apply
        self.apply_calls = []
        self.get_calls = 0

    def gateway_config_get(self, target):
        self.get_calls += 1
        if self.raise_on_get:
            raise self.raise_on_get
        return GatewayConfig(configuration=self.config, base_hash="hash-abc")

    def gateway_config_apply(self, target, configuration, base_hash):
        self.apply_calls.append((dict(configuration), base_hash))
        if self.raise_on_apply:
            exc = self.raise_on_apply
            self.raise_on_apply = None  # clear after first raise for retry test
            raise exc
        return self.apply_result or GatewayApplyResult(
            transaction_id="tx-fake", base_hash="hash-new"
        )

    def create_agent(self, target, spec):
        pass

    def update_agent(self, target, agent_id, patch):
        pass

    def offline_apply_provider(self, target, resource):
        pass

    def offline_create_agent(self, target, resource):
        pass


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _target(tmp_path: Path) -> ConfigTarget:
    return ConfigTarget(
        workspace_root=tmp_path / "ws",
        config_path=tmp_path / "ws" / "openclaw.json",
        state_dir=tmp_path / "state",
    )


def _resource(identifier: str = "example-provider") -> Resource:
    return Resource(
        kind=ResourceKind.PROVIDER,
        identifier=identifier,
        manager="example-manager",
        spec={"effort": "high"},
        managed_paths=("/effort",),
        policy=MergePolicy.COOPERATIVE,
    )


def _manifest(target: ConfigTarget) -> ControlManifest:
    return ControlManifest(
        version=1,
        target=target,
        resources=(_resource(),),
        source_path=Path("tests/fixtures/oramaclaw-engine.json"),
        source_fingerprint="deadbeef",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_committed_path(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("apply"))
    target = _target(tmp_path)
    transport = FakeTransport()
    engine = ControlEngine(transport=transport)

    result = engine.apply_manifest(_manifest(target), target)

    assert result.state == "committed"
    assert result.applied  # non-empty
    assert "provider:example-provider" in result.applied
    assert not result.conflicts
    assert transport.apply_calls  # an apply happened


def test_auto_woven_path(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("auto_weave"))
    target = _target(tmp_path)
    engine = ControlEngine(transport=FakeTransport())

    result = engine.apply_manifest(_manifest(target), target)

    assert result.state == "auto_woven"
    assert result.auto_woven  # non-empty
    assert not result.conflicts


def test_conflict_needs_input(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("conflict"))
    target = _target(tmp_path)
    transport = FakeTransport()
    engine = ControlEngine(transport=transport)

    result = engine.apply_manifest(_manifest(target), target)

    assert result.state == "needs_input"
    assert result.conflicts  # non-empty
    assert not result.applied
    # No apply should be attempted when there are no apply/auto-weave actions.
    assert not transport.apply_calls

    # PendingResolution durably stored.
    from oramaclaw.store import ControlStore

    with ControlStore.open(target) as store:
        pending = store.load_pending()
    assert pending
    assert pending[0]["resolution_id"] == result.conflicts[0].resolution_id


def test_gateway_unavailable_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("skip"))
    target = _target(tmp_path)
    transport = FakeTransport(raise_on_get=GatewayUnavailable("no gateway"))
    engine = ControlEngine(transport=transport)

    # Must not raise; engine falls back to OfflineTransport and returns a result.
    result = engine.apply_manifest(_manifest(target), target)

    assert result.state in {"gateway_unavailable", "committed"}
    assert result is not None
    assert any("offline" in w for w in result.warnings)


def test_stale_retried_once(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("apply"))
    target = _target(tmp_path)
    transport = FakeTransport(raise_on_apply=StaleConfiguration("hash-abc"))
    engine = ControlEngine(transport=transport)

    result = engine.apply_manifest(_manifest(target), target)

    assert result.state == "committed"
    # First apply raised stale, second succeeded → two apply calls.
    assert len(transport.apply_calls) == 2
    # The retry re-fetched a fresh config (get called twice: initial + refresh).
    assert transport.get_calls == 2


def test_journal_written(tmp_path, monkeypatch):
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("apply"))
    target = _target(tmp_path)
    engine = ControlEngine(transport=FakeTransport())

    result = engine.apply_manifest(_manifest(target), target)

    from oramaclaw.store import ControlStore

    with ControlStore.open(target) as store:
        last = store.last_transaction()
    assert last is not None
    assert last["transaction_id"] == result.transaction_id
    assert last["state"] == "committed"


def test_cooperative_timeout_downgrades_auto_weave(tmp_path, monkeypatch):
    """Past the 90s budget, auto-weave actions downgrade to conflicts (P2-2)."""
    monkeypatch.setattr("oramaclaw.engine.plan_resource", _plan_factory("auto_weave"))
    target = _target(tmp_path)

    # Clock jumps past the 90s budget on the second read (start vs. per-action).
    ticks = iter([0.0, 1000.0, 1000.0, 1000.0])

    def _clock():
        try:
            return next(ticks)
        except StopIteration:
            return 1000.0

    engine = ControlEngine(transport=FakeTransport(), clock=_clock)
    result = engine.apply_manifest(_manifest(target), target)

    assert result.conflicts  # downgraded
    assert not result.auto_woven
    assert result.state == "needs_input"
