"""Pins for harness-path model governance (Alexandria standard, local pin file)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orama_system.model_governance import (
    EscalationProof,
    LaunchSpec,
    ModelGovernanceError,
    assert_launch_allowed,
    default_launch,
    evaluate_cost_gate,
    load_model_governance,
    proof_is_token,
)

LIVE_GUIDANCE = (
    Path(".cursor/rules/common-performance.mdc"),
    Path(".cursor/commands/model-route.md"),
    Path("bin/orama-system/references/claude-code-workflow-canonical.md"),
    Path("bin/orama-system/skills/cursor-agent/SKILL.md"),
    Path("skills/cursor-agent/SKILL.md"),
    Path("docs/standards/model-governance.md"),
)


@pytest.fixture
def cfg() -> dict:
    return load_model_governance()


def test_cost_gate_and_cloud_escalation_invariants(cfg: dict) -> None:
    assert cfg["invariants"]["cost_gate"] == "fail_closed"
    assert cfg["invariants"]["cloud_escalation"] == "default_deny"


def test_cursor_default_is_grok_46_medium_fast_off() -> None:
    spec = default_launch("cursor_grok_bot")
    assert spec.launch_id == "grok-4.6"
    assert spec.effort == "medium"
    assert spec.fast is False
    assert_launch_allowed(spec)


def test_anthropic_default_is_sonnet_55_medium() -> None:
    spec = default_launch("anthropic")
    assert spec.launch_id == "claude-sonnet-5-5"
    assert spec.effort == "medium"
    assert_launch_allowed(spec)


def test_legacy_sonnet_5_pin_allowed(cfg: dict) -> None:
    spec = LaunchSpec(path="anthropic", launch_id="claude-sonnet-5", effort="medium")
    assert_launch_allowed(spec, config=cfg)


def test_grok_45_banned() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot",
        launch_id="grok-4.5",
        effort="medium",
        fast=False,
    )
    with pytest.raises(ModelGovernanceError, match="banned"):
        assert_launch_allowed(spec)


def test_auto_never_for_agents() -> None:
    spec = LaunchSpec(path="cursor_grok_bot", launch_id="auto", agent=True)
    with pytest.raises(ModelGovernanceError, match="editor-only"):
        assert_launch_allowed(spec)


def test_composer_requires_fast_off() -> None:
    ok = LaunchSpec(path="cursor_grok_bot", launch_id="composer-2.5", fast=False)
    assert_launch_allowed(ok)
    bad = LaunchSpec(path="cursor_grok_bot", launch_id="composer-2.5", fast=True)
    with pytest.raises(ModelGovernanceError, match="fast"):
        assert_launch_allowed(bad)


def test_env_and_config_flags_are_not_escalation_tokens() -> None:
    env_shaped = EscalationProof(
        kind="env_var",
        reference="HUMAN_APPROVED=true",
        model_id="grok-4.7",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    flag_shaped = EscalationProof(
        kind="config_flag",
        reference="human_approved: true",
        model_id="grok-4.7",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    cached = EscalationProof(
        kind="cached_approval",
        reference="yesterday.sig",
        model_id="grok-4.7",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert proof_is_token(env_shaped) is False
    assert proof_is_token(flag_shaped) is False
    assert proof_is_token(cached) is False
    spec = LaunchSpec(
        path="cursor_grok_bot",
        launch_id="grok-4.7",
        effort="medium",
        fast=False,
    )
    with pytest.raises(ModelGovernanceError, match="default-deny"):
        assert_launch_allowed(spec, proof=env_shaped)
    with pytest.raises(ModelGovernanceError, match="default-deny"):
        assert_launch_allowed(spec, proof=flag_shaped)


def test_grok_47_allowed_only_with_real_proof() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot",
        launch_id="grok-4.7",
        effort="medium",
        fast=False,
    )
    with pytest.raises(ModelGovernanceError, match="default-deny"):
        assert_launch_allowed(spec)
    proof = EscalationProof(
        kind="github_verified_signoff",
        reference="abc123verified",
        model_id="grok-4.7",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        effort="medium",
        fast=False,
    )
    assert_launch_allowed(spec, proof=proof)


def test_opus_and_fable_require_token_fable_needs_cap() -> None:
    opus = LaunchSpec(path="anthropic", launch_id="claude-opus-5-5", effort="high", fast=False)
    with pytest.raises(ModelGovernanceError, match="default-deny"):
        assert_launch_allowed(opus)
    opus_proof = EscalationProof(
        kind="offline_gpg",
        reference="fpr:operator",
        model_id="claude-opus-5-5",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        effort="high",
        fast=False,
    )
    assert_launch_allowed(opus, proof=opus_proof)

    fable = LaunchSpec(path="anthropic", launch_id="claude-fable-5-1", effort="medium")
    no_cap = EscalationProof(
        kind="offline_gpg",
        reference="fpr:operator",
        model_id="claude-fable-5-1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        effort="medium",
    )
    with pytest.raises(ModelGovernanceError, match="budget cap"):
        assert_launch_allowed(fable, proof=no_cap)
    with_cap = EscalationProof(
        kind="offline_gpg",
        reference="fpr:operator",
        model_id="claude-fable-5-1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        effort="medium",
        budget_cap="max_tokens=8192",
    )
    assert_launch_allowed(fable, proof=with_cap)


def test_cost_gate_fail_closed() -> None:
    with pytest.raises(ModelGovernanceError, match="cannot be evaluated"):
        evaluate_cost_gate(cap_evaluable=False, remaining=100)
    with pytest.raises(ModelGovernanceError, match="cannot be evaluated"):
        evaluate_cost_gate(cap_evaluable=True, remaining=None)
    with pytest.raises(ModelGovernanceError, match="cap hit"):
        evaluate_cost_gate(cap_evaluable=True, remaining=0)
    evaluate_cost_gate(cap_evaluable=True, remaining=10)


def test_live_guidance_has_no_stale_defaults() -> None:
    for path in LIVE_GUIDANCE:
        text = path.read_text(encoding="utf-8")
        assert "Haiku 4.5" not in text
        assert "Sonnet 4.6" not in text
        assert "Opus 4.6" not in text
        assert "claude-opus-4-8" not in text
        assert "claude-4.6-sonnet" not in text
    cursor_skill = Path("bin/orama-system/skills/cursor-agent/SKILL.md").read_text(encoding="utf-8")
    assert "grok-4.6" in cursor_skill
    assert "**Default for agents.**" in cursor_skill
    workflow = Path("bin/orama-system/references/claude-code-workflow-canonical.md").read_text(encoding="utf-8")
    assert "claude-sonnet-5-5" in workflow
    assert "model: 'claude-sonnet-5'" not in workflow
