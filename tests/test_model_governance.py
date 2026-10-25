"""Pins for harness-path model governance (Alexandria standard, local pin file)."""

from __future__ import annotations

import hashlib
import itertools
import json
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
    plan_launch,
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


def test_cursor_default_is_grok_47_medium_fast_off() -> None:
    spec = default_launch("cursor_grok_bot")
    assert spec.launch_id == "grok-4.7"
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


@pytest.mark.parametrize("launch_id", ["grok-4.5", "grok-4.6"])
def test_superseded_grok_launch_ids_are_banned(launch_id: str) -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot",
        launch_id=launch_id,
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


def test_gpt_5_6_terra_is_an_ungated_cursor_pick_at_medium_fast_off() -> None:
    """The official Terra id replaces the retired Codex example without needing a token."""
    ok = LaunchSpec(
        path="cursor_grok_bot", launch_id="gpt-5.6-terra", effort="medium", fast=False
    )
    assert_launch_allowed(ok)


@pytest.mark.parametrize(
    "effort,fast,match",
    [("medium", True, "fast"), ("medium", None, "fast"), ("high", False, "effort")],
)
def test_gpt_5_6_terra_refuses_fast_and_non_medium_effort_without_proof(
    effort: str, fast: bool | None, match: str
) -> None:
    """Terra keeps the Cursor controls: fast off, and medium effort unless a token covers it."""
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="gpt-5.6-terra", effort=effort, fast=fast
    )
    with pytest.raises(ModelGovernanceError, match=match):
        assert_launch_allowed(spec)


def test_gpt_5_6_terra_requires_its_configured_effort_to_be_set_explicitly() -> None:
    """An unset effort is not medium: the ungated row holds Terra to the effort it names."""
    spec = LaunchSpec(path="cursor_grok_bot", launch_id="gpt-5.6-terra", effort=None, fast=False)
    with pytest.raises(ModelGovernanceError, match="requires effort medium"):
        assert_launch_allowed(spec)


def test_reasoning_effort_is_checked_like_effort_on_the_cursor_path() -> None:
    """A non-medium reasoning_effort needs a token even when effort is unset."""
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="composer-2.5", effort=None,
        reasoning_effort="high", fast=False,
    )
    with pytest.raises(ModelGovernanceError, match="non-medium effort"):
        assert_launch_allowed(spec)


def test_assert_launch_allowed_rejects_conflicting_effort_fields() -> None:
    """The launch gate enforces the same single-effort invariant as plan_launch."""
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="composer-2.5", effort="medium",
        reasoning_effort="high", fast=False,
    )
    with pytest.raises(ModelGovernanceError, match="conflicting effort fields"):
        assert_launch_allowed(spec)
    with pytest.raises(ModelGovernanceError, match="conflicting effort fields"):
        plan_launch(spec)


def test_retired_codex_low_id_is_not_an_ungated_cursor_pick() -> None:
    """The superseded gpt-5.3-codex-low id stays default-deny on the Cursor path."""
    spec = LaunchSpec(path="cursor_grok_bot", launch_id="gpt-5.3-codex-low", fast=False)
    with pytest.raises(ModelGovernanceError, match="default-deny"):
        assert_launch_allowed(spec)


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


def test_banned_launch_ids_are_refused_before_path_dispatch() -> None:
    with pytest.raises(ModelGovernanceError, match="banned launch id: gpt-6-astra"):
        assert_launch_allowed(LaunchSpec(path="unknown", launch_id="gpt-6-astra"))


def test_duplicate_governance_yaml_keys_raise(tmp_path: Path) -> None:
    """Duplicate mapping keys must not silently overwrite bans (e.g. banned_launch_ids)."""
    path = tmp_path / "model-governance.yml"
    path.write_text(
        "banned_launch_ids:\n"
        "  - grok-4.5\n"
        "banned_launch_ids:\n"
        "  - grok-4.6\n",
        encoding="utf-8",
    )
    with pytest.raises(ModelGovernanceError, match="config unavailable"):
        load_model_governance(str(path))


@pytest.mark.unit
@pytest.mark.parametrize("effort", ["xhigh", "max"])
@pytest.mark.parametrize("field", ["effort", "reasoning_effort"])
def test_forbidden_effort_cannot_be_unlocked_by_approval(
    effort: str, field: str
) -> None:
    """Ruling 10 rejects top-tier effort even with matching approval metadata."""
    values = {field: effort}
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="composer-2.5", fast=False, **values
    )
    proof = _vec_proof("composer-2.5", effort, False)
    with pytest.raises(ModelGovernanceError, match="effort is forbidden"):
        assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)


@pytest.mark.unit
@pytest.mark.parametrize("effort", ["xhigh", "max"])
def test_forbidden_secondary_effort_is_not_hidden_by_medium(effort: str) -> None:
    """Both effort fields are checked before a path-specific early return."""
    spec = LaunchSpec(
        path="anthropic",
        launch_id="claude-sonnet-5-5",
        effort="medium",
        reasoning_effort=effort,
    )
    with pytest.raises(ModelGovernanceError, match="effort is forbidden"):
        assert_launch_allowed(spec)


def test_grok_47_default_is_ungated_and_requires_medium_fast_off() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot",
        launch_id="grok-4.7",
        effort="medium",
        fast=False,
    )
    assert_launch_allowed(spec)
    for effort in (None, "high"):
        with pytest.raises(ModelGovernanceError, match="requires effort medium"):
            assert_launch_allowed(
                LaunchSpec(
                    path="cursor_grok_bot",
                    launch_id="grok-4.7",
                    effort=effort,
                    fast=False,
                )
            )
    with pytest.raises(ModelGovernanceError, match="requires fast=False"):
        assert_launch_allowed(
            LaunchSpec(
                path="cursor_grok_bot",
                launch_id="grok-4.7",
                effort="medium",
                fast=True,
            )
        )


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
        assert "claude-haiku-4-5" not in text
        assert "gpt-5.3-codex" not in text
    cursor_skill = Path("bin/orama-system/skills/cursor-agent/SKILL.md").read_text(encoding="utf-8")
    assert "grok-4.7" in cursor_skill
    assert "| `grok-4.6` | Grok 4.6 | **Default for agents.**" not in cursor_skill
    workflow = Path("bin/orama-system/references/claude-code-workflow-canonical.md").read_text(encoding="utf-8")
    assert "claude-sonnet-5-5" in workflow
    assert "model: 'claude-sonnet-5'" not in workflow


def test_existing_routing_policy_is_supplemented_not_replaced() -> None:
    """The Alexandria pin adds fallback and alternate paths; the original tier policy stays."""
    route = Path(".cursor/commands/model-route.md").read_text(encoding="utf-8")
    assert "Recommend the best model tier for the current task by complexity and budget." in route
    for tier in ("- `haiku` (`claude-haiku-5-5`)", "- `sonnet` (`claude-sonnet-5-5`)", "- `opus` (`claude-opus-5-5`)"):
        assert tier in route
    assert "## Fallback (when the heuristic cannot decide)" in route

    perf = Path(".cursor/rules/common-performance.mdc").read_text(encoding="utf-8")
    for heading in ("**Haiku 5.5**", "**Sonnet 5.5**", "**Opus 5.5**", "### Fallback and alternate paths"):
        assert heading in perf

    workflow = Path("bin/orama-system/references/claude-code-workflow-canonical.md").read_text(encoding="utf-8")
    for tier in ("**Tier 1 — Dispatch/control: Haiku", "**Tier 2 — Evaluate/integrate:", "**Tier 3 — Escalation only:"):
        assert tier in workflow
    assert "### Fallback and alternate paths (supplement)" in workflow

    cursor_skill = Path("bin/orama-system/skills/cursor-agent/SKILL.md").read_text(encoding="utf-8")
    assert "| `composer-2.5` | Composer 2.5 | **Default for all light/parallel tasks** |" in cursor_skill
    assert "### Fallback and alternate paths (supplement)" in cursor_skill

    pin = Path("docs/standards/model-governance.md").read_text(encoding="utf-8")
    assert "## Relationship to existing orama routing policy" in pin
    assert "## Escalation approval regimes" in pin
    assert "| 1, interim |" in pin and "| 2, enforced |" in pin
    assert "**Required deployment.**" in pin
    skill = Path("bin/orama-system/skills/cursor-agent/SKILL.md").read_text(encoding="utf-8")
    assert "--model auto" not in skill.replace("Never `--model auto`", "")
    assert "fast on only if the operator asks" not in skill
    assert "gpt-5.6-terra --" not in skill


# ---------------------------------------------------------------------------
# R1-R4 shared behavioral vectors. Identical block in orama-system and
# Perpetua-Tools tests; no shared runtime import. Proof fixtures are synthetic
# and unauthenticated: they exercise policy metadata only, not signatures.
# Provider model availability is unverified here.
# ---------------------------------------------------------------------------
_VEC_NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def _vec_proof(
    model: str,
    effort: str | None,
    fast: bool | None,
    budget: str | None = None,
    hours: int = 1,
    **extra: str | None,
) -> EscalationProof:
    return EscalationProof(
        kind="offline_gpg",
        reference="synthetic-policy-fixture",
        model_id=model,
        effort=effort,
        fast=fast,
        budget_cap=budget,
        expires_at=_VEC_NOW + timedelta(hours=hours),
        **extra,
    )


@pytest.mark.parametrize("path", ["anthropic", "cursor_grok_bot"])
@pytest.mark.parametrize(
    "model",
    ["claude-sonnet-5-5", "claude-sonnet-5", "claude-opus-5-5", "claude-fable-5-1"],
)
@pytest.mark.parametrize("effort", [None, "medium", "high"])
@pytest.mark.parametrize("fast", [None, False, True])
@pytest.mark.parametrize("approval", ["absent", "fresh", "expired"])
@pytest.mark.parametrize("budget", [None, "max_tokens=8192"])
def test_vector_family_matrix(
    path: str,
    model: str,
    effort: str | None,
    fast: bool | None,
    approval: str,
    budget: str | None,
) -> None:
    spec = LaunchSpec(path=path, launch_id=model, effort=effort, fast=fast)
    proof = None
    if approval != "absent":
        proof = _vec_proof(
            model, effort, fast, budget, hours=1 if approval == "fresh" else -1
        )
    allowed = fast is not True
    if model.startswith("claude-sonnet"):
        allowed = allowed and effort == "medium"
    elif model == "claude-opus-5-5":
        allowed = allowed and effort in ("medium", "high") and fast is False
        allowed = allowed and approval == "fresh"
    else:
        allowed = allowed and effort == "medium"
        allowed = allowed and approval == "fresh" and budget is not None
    if approval == "expired":
        allowed = False
    if allowed:
        assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)
    else:
        with pytest.raises(ModelGovernanceError):
            assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)


@pytest.mark.parametrize(
    "approved_model,approved_effort,approved_fast,hours,allowed",
    [
        ("composer-2.5", "high", True, 1, True),
        ("other-model", "high", True, 1, False),
        ("composer-2.5", "medium", True, 1, False),
        ("composer-2.5", "high", False, 1, False),
        ("composer-2.5", "high", None, 1, False),
        ("composer-2.5", "high", True, -1, False),
    ],
)
def test_vector_approval_binds_launch_tuple(
    approved_model: str,
    approved_effort: str,
    approved_fast: bool | None,
    hours: int,
    allowed: bool,
) -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="composer-2.5", effort="high", fast=True
    )
    proof = _vec_proof(approved_model, approved_effort, approved_fast, hours=hours)
    if allowed:
        assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)
    else:
        with pytest.raises(ModelGovernanceError):
            assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)


def test_vector_stray_mismatched_proof_refused_on_ungated_launch() -> None:
    spec = LaunchSpec(path="anthropic", launch_id="claude-sonnet-5-5", effort="medium")
    stale = _vec_proof("claude-sonnet-5-5", "medium", None, hours=-1)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=stale, now=_VEC_NOW)
    wrong_effort = _vec_proof("claude-sonnet-5-5", "high", None)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=wrong_effort, now=_VEC_NOW)


@pytest.mark.parametrize("fast,approved_fast", [(None, False), (False, None)])
@pytest.mark.parametrize("reasoning_field", [False, True])
def test_vector_nonfast_and_effort_fields_normalize(
    fast: bool | None,
    approved_fast: bool | None,
    reasoning_field: bool,
) -> None:
    spec = LaunchSpec(
        path="anthropic",
        launch_id="claude-fable-5-1",
        fast=fast,
        effort=None if reasoning_field else "medium",
        reasoning_effort="medium" if reasoning_field else None,
    )
    proof = _vec_proof(spec.launch_id, "medium", approved_fast, "max_tokens=8192")
    assert_launch_allowed(spec, proof=proof, now=_VEC_NOW)


def test_vector_scope_and_path_binding() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="medium", fast=False
    )
    scoped = _vec_proof("grok-4.7", "medium", False, scope="task-a")
    assert_launch_allowed(spec, proof=scoped, approval_scope="task-a", now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=scoped, approval_scope="task-b", now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=scoped, now=_VEC_NOW)
    unscoped = _vec_proof("grok-4.7", "medium", False)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=unscoped, approval_scope="task-a", now=_VEC_NOW)
    other_path = _vec_proof("grok-4.7", "medium", False, path="anthropic")
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=other_path, now=_VEC_NOW)


def test_vector_sonnet_fast_refused_without_proof() -> None:
    bad = LaunchSpec(
        path="anthropic", launch_id="claude-sonnet-5-5", effort="medium", fast=True
    )
    with pytest.raises(ModelGovernanceError, match="fast"):
        assert_launch_allowed(bad)
    for fast in (None, False):
        ok = LaunchSpec(
            path="anthropic", launch_id="claude-sonnet-5-5", effort="medium", fast=fast
        )
        assert_launch_allowed(ok)


def test_vector_cursor_family_controls() -> None:
    fable = LaunchSpec(
        path="cursor_grok_bot", launch_id="claude-fable-5-1", effort="medium"
    )
    with pytest.raises(ModelGovernanceError, match="budget cap"):
        assert_launch_allowed(
            fable, proof=_vec_proof("claude-fable-5-1", "medium", None), now=_VEC_NOW
        )
    assert_launch_allowed(
        fable,
        proof=_vec_proof("claude-fable-5-1", "medium", None, "max_tokens=8192"),
        now=_VEC_NOW,
    )
    opus_medium = LaunchSpec(
        path="cursor_grok_bot", launch_id="claude-opus-5-5", effort="medium", fast=False
    )
    assert_launch_allowed(
        opus_medium,
        proof=_vec_proof("claude-opus-5-5", "medium", False),
        now=_VEC_NOW,
    )
    opus_fast = LaunchSpec(
        path="cursor_grok_bot", launch_id="claude-opus-5-5", effort="high", fast=True
    )
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(
            opus_fast, proof=_vec_proof("claude-opus-5-5", "high", True), now=_VEC_NOW
        )
    sonnet = LaunchSpec(
        path="cursor_grok_bot", launch_id="claude-sonnet-5-5", effort="medium"
    )
    assert_launch_allowed(sonnet)
    grok_high = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="high", fast=False
    )
    with pytest.raises(ModelGovernanceError, match="effort"):
        assert_launch_allowed(
            grok_high, proof=_vec_proof("grok-4.7", "high", False), now=_VEC_NOW
        )


@pytest.mark.parametrize("effort", [None, "high", "low", "medium"])
def test_vector_direct_xai_requires_medium_effort(effort: str | None) -> None:
    spec = LaunchSpec(path="direct_xai", launch_id="grok-4.7", reasoning_effort=effort)
    if effort == "medium":
        assert_launch_allowed(spec)
    else:
        with pytest.raises(ModelGovernanceError, match="reasoning_effort"):
            assert_launch_allowed(spec)


def test_direct_xai_accepts_effort_alias_without_reasoning_effort() -> None:
    """The accepted effort alias satisfies the direct-xAI policy row."""
    spec = LaunchSpec(path="direct_xai", launch_id="grok-4.7", effort="medium")

    plan_launch(spec)
    assert_launch_allowed(spec)


def test_vector_direct_xai_refuses_fast_mode() -> None:
    fast = LaunchSpec(
        path="direct_xai", launch_id="grok-4.7", reasoning_effort="medium", fast=True
    )
    with pytest.raises(ModelGovernanceError, match="fast mode is refused"):
        assert_launch_allowed(fast)
    assert_launch_allowed(
        LaunchSpec(path="direct_xai", launch_id="grok-4.7", reasoning_effort="medium", fast=False)
    )


def test_vector_approval_optionally_binds_path_and_scope() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="medium", fast=False
    )
    bound = _vec_proof(
        "grok-4.7", "medium", False, path="cursor_grok_bot", scope="task-a"
    )
    assert_launch_allowed(spec, proof=bound, approval_scope="task-a", now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=bound, approval_scope="task-b", now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=bound, now=_VEC_NOW)
    wrong_path = _vec_proof("grok-4.7", "medium", False, path="anthropic")
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=wrong_path, now=_VEC_NOW)


def test_vector_expiry_equal_to_now_is_refused() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="medium", fast=False
    )
    at_now = _vec_proof("grok-4.7", "medium", False, hours=0)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=at_now, now=_VEC_NOW)
    one_second_left = EscalationProof(
        kind="offline_gpg",
        reference="synthetic-policy-fixture",
        model_id="grok-4.7",
        effort="medium",
        fast=False,
        expires_at=_VEC_NOW + timedelta(seconds=1),
    )
    assert_launch_allowed(spec, proof=one_second_left, now=_VEC_NOW)


def test_vector_empty_string_scope_is_strict_equality() -> None:
    spec = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="medium", fast=False
    )
    empty = _vec_proof("grok-4.7", "medium", False, scope="")
    assert_launch_allowed(spec, proof=empty, approval_scope="", now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=empty, now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=empty, approval_scope="task-a", now=_VEC_NOW)
    unscoped = _vec_proof("grok-4.7", "medium", False)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec, proof=unscoped, approval_scope="", now=_VEC_NOW)


def test_vector_unknown_proof_kind_is_not_a_token() -> None:
    gated = LaunchSpec(
        path="cursor_grok_bot", launch_id="grok-4.7", effort="medium", fast=False
    )
    unknown = EscalationProof(
        kind="vibes_based_approval",
        reference="synthetic-policy-fixture",
        model_id="grok-4.7",
        effort="medium",
        fast=False,
        expires_at=_VEC_NOW + timedelta(hours=1),
    )
    assert not proof_is_token(unknown, now=_VEC_NOW)
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(gated, proof=unknown, now=_VEC_NOW)
    ungated = LaunchSpec(
        path="anthropic", launch_id="claude-sonnet-5-5", effort="medium"
    )
    stray = EscalationProof(
        kind="vibes_based_approval",
        reference="synthetic-policy-fixture",
        model_id="claude-sonnet-5-5",
        effort="medium",
        fast=None,
        expires_at=_VEC_NOW + timedelta(hours=1),
    )
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(ungated, proof=stray, now=_VEC_NOW)


@pytest.mark.parametrize("path", ["anthropic", "cursor_grok_bot"])
@pytest.mark.parametrize("launch_id", ["grok-4.5", "grok-4.6"])
def test_vector_banned_launch_id_refused_even_with_matching_proof(
    path: str, launch_id: str
) -> None:
    spec = LaunchSpec(path=path, launch_id=launch_id, effort="medium", fast=False)
    with pytest.raises(ModelGovernanceError, match="banned"):
        assert_launch_allowed(spec)
    with pytest.raises(ModelGovernanceError, match="banned"):
        assert_launch_allowed(
            spec, proof=_vec_proof(launch_id, "medium", False), now=_VEC_NOW
        )


@pytest.mark.parametrize("path", ["anthropic", "cursor_grok_bot"])
def test_vector_fable_requires_budget_cap_on_every_path(path: str) -> None:
    spec = LaunchSpec(path=path, launch_id="claude-fable-5-1", effort="medium")
    with pytest.raises(ModelGovernanceError, match="budget cap"):
        assert_launch_allowed(
            spec, proof=_vec_proof("claude-fable-5-1", "medium", None), now=_VEC_NOW
        )
    with pytest.raises(ModelGovernanceError):
        assert_launch_allowed(spec)
    assert_launch_allowed(
        spec,
        proof=_vec_proof("claude-fable-5-1", "medium", None, "max_tokens=8192"),
        now=_VEC_NOW,
    )


# --- Cross-repo parity vectors (F1/F2): keep byte-identical in both v1 repositories. ---

_PARITY_NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)


@pytest.mark.parametrize("entry", ["plan", "assert"])
@pytest.mark.parametrize(
    "effort,reasoning",
    [("medium", "high"), ("high", "medium"), ("low", "medium"), ("", "medium")],
)
def test_parity_conflicting_effort_aliases_refuse_at_both_entry_points(
    entry: str, effort: str, reasoning: str
) -> None:
    """Contradictory effort aliases refuse before any model-family branch."""
    for path, launch_id in (
        ("direct_xai", "grok-4.7"),
        ("cursor_grok_bot", "grok-4.7"),
        ("anthropic", "claude-sonnet-5-5"),
    ):
        spec = LaunchSpec(
            path=path, launch_id=launch_id, effort=effort, reasoning_effort=reasoning, fast=False
        )
        with pytest.raises(ModelGovernanceError, match="conflicting effort"):
            if entry == "plan":
                plan_launch(spec)
            else:
                assert_launch_allowed(spec)


@pytest.mark.parametrize("entry", ["plan", "assert"])
def test_parity_identical_effort_aliases_behave_consistently(entry: str) -> None:
    """Equal aliases are one effort; the intended default launch stays allowed."""
    spec = LaunchSpec(
        path="direct_xai", launch_id="grok-4.7", effort="medium", reasoning_effort="medium",
        fast=False,
    )
    if entry == "plan":
        plan_launch(spec)
    else:
        assert_launch_allowed(spec)


@pytest.mark.parametrize("fast", [False, None])
def test_parity_direct_xai_fast_false_or_absent_stays_allowed(fast: bool | None) -> None:
    """Absent or false fast is the default direct-xAI launch."""
    spec = LaunchSpec(path="direct_xai", launch_id="grok-4.7", reasoning_effort="medium", fast=fast)
    plan_launch(spec)
    assert_launch_allowed(spec)


@pytest.mark.parametrize("with_metadata_proof", [False, True])
def test_parity_direct_xai_fast_true_refuses_at_both_entry_points(
    with_metadata_proof: bool,
) -> None:
    """Fast mode needs a trusted one-use P5 approval; no metadata helper can grant it."""
    spec = LaunchSpec(path="direct_xai", launch_id="grok-4.7", reasoning_effort="medium", fast=True)
    proof = None
    if with_metadata_proof:
        proof = EscalationProof(
            kind="offline_gpg",
            reference="synthetic-operator-reference",
            model_id="grok-4.7",
            effort="medium",
            fast=True,
            expires_at=_PARITY_NOW + timedelta(minutes=5),
        )
    with pytest.raises(ModelGovernanceError, match="fast mode"):
        plan_launch(spec)
    with pytest.raises(ModelGovernanceError, match="fast mode"):
        assert_launch_allowed(spec, proof=proof, now=_PARITY_NOW)


# --- Cross-repo differential (F1/F2): keep byte-identical in both v1 repositories. ---
_DIFF_PATHS = (
    ("direct_xai", "grok-4.7"),
    ("direct_xai", "grok-4.6"),
    ("cursor_grok_bot", "grok-4.7"),
    ("cursor_grok_bot", "composer-2.5"),
    ("anthropic", "claude-sonnet-5-5"),
    ("anthropic", "claude-opus-5-5"),
)
_DIFF_EFFORTS = (None, "", "low", "medium", "high", "xhigh", "max")
_DIFF_FASTS = (None, False, True)
# SHA-256 of the sorted-key JSON outcome table below; identical in PT and orama-system.
_DIFF_DIGEST = "295b8ab1496bf4e8ee63a2cf49e77bf1d444478b93ab302cb14cdac4358a072d"


def _diff_outcomes() -> dict[str, str]:
    """Run both entry points over every path/alias/fast combination (1,764 cases)."""
    outcomes: dict[str, str] = {}
    for (path, model), effort, reasoning, fast in itertools.product(
        _DIFF_PATHS, _DIFF_EFFORTS, _DIFF_EFFORTS, _DIFF_FASTS
    ):
        key = f"{path}|{model}|e={effort!r}|r={reasoning!r}|f={fast}"
        for name, entry in (("plan", plan_launch), ("assert", assert_launch_allowed)):
            spec = LaunchSpec(
                path=path,
                launch_id=model,
                effort=effort,
                reasoning_effort=reasoning,
                fast=fast,
            )
            try:
                entry(spec)
                outcomes[f"{key}|{name}"] = "ALLOW"
            except ModelGovernanceError:
                outcomes[f"{key}|{name}"] = "REFUSE"
    return outcomes


def test_differential_policy_outcomes_match_across_repositories() -> None:
    """Every case is a clean allow or refusal and the whole table matches the pinned digest."""
    outcomes = _diff_outcomes()
    assert len(outcomes) == 1764
    blob = json.dumps(outcomes, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(blob).hexdigest() == _DIFF_DIGEST
