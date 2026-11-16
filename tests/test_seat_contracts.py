"""Seat contracts shared by Scout, the inner seat and Biafra (the outer seat).

The Python validator is the authority. The JSON Schema in docs is shape-only.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "bin" / "agents" / "seat_contracts.py"
CYCLE = ROOT / "bin" / "agents" / "biafra_cycle.py"
DIGEST = "a" * 64


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sc():
    return _load(CONTRACTS, "seat_contracts")


def _entry(**over):
    base = {
        "version": 1,
        "seat": "inner",
        "attempt_id": "a-001",
        "hypothesis": "Smaller batch lowers val_bpb.",
        "artifact": "train.py",
        "metric_name": "val_bpb",
        "metric_before": 0.20,
        "metric_after": 0.18,
        "decision": "keep",
        "evaluator_digest": DIGEST,
    }
    base.update(over)
    return base


def _card(**over):
    base = {
        "version": 1,
        "mechanism_id": "m-" + "b" * 12,
        "revision": 1,
        "parent": None,
        "hypothesis": "Repeat reverts on the same artifact mean the proposal rule is stale.",
        "evidence_ids": ["a-001", "a-002"],
        "inner_metric": "val_bpb",
        "held_out_metric": "val_bpb_heldout",
        "evaluator_digest": DIGEST,
        "dry_run_receipt": {"ok": True, "retries": 0, "launched": False},
        "delta": -0.01,
        "reverted": False,
        "scope_record": {"authorizes": "nothing"},
        "owner_slices": ["kungfu"],
        "status": "candidate",
    }
    base.update(over)
    return base


def test_valid_trace_entry_has_no_errors(sc) -> None:
    assert sc.validate_trace_entry(_entry()) == []


@pytest.mark.parametrize(
    "bad",
    [
        {"seat": "scout"},
        {"decision": "maybe"},
        {"metric_after": float("nan")},
        {"metric_before": math.inf},
        {"metric_after": True},
        {"evaluator_digest": "xyz"},
        {"attempt_id": ""},
    ],
)
def test_invalid_trace_entries_are_refused(sc, bad) -> None:
    assert sc.validate_trace_entry(_entry(**bad))


def test_trace_entry_must_agree_with_its_metrics(sc) -> None:
    errors = sc.validate_trace_entry(_entry(metric_before=0.1, metric_after=0.2, decision="keep"))
    assert any("decision" in e for e in errors)


def test_missing_field_is_named(sc) -> None:
    entry = _entry()
    del entry["hypothesis"]
    assert any("hypothesis" in e for e in sc.validate_trace_entry(entry))


def test_evaluator_digest_changes_when_a_verifier_file_changes(sc, tmp_path: Path) -> None:
    (tmp_path / "check.py").write_text("assert True\n")
    first = sc.evaluator_digest([tmp_path / "check.py"])
    (tmp_path / "check.py").write_text("assert False\n")
    assert sc.evaluator_digest([tmp_path / "check.py"]) != first
    assert len(first) == 64


def test_stall_report_names_a_repeat_revert_window(sc) -> None:
    trace = [_entry(attempt_id=f"a-{i}", metric_before=0.2, metric_after=0.3, decision="revert") for i in range(3)]
    report = sc.stall_report(trace, window=3)
    assert report["stalled"] is True
    assert report["entry_ids"] == ["a-0", "a-1", "a-2"]


def test_stall_report_is_clear_after_a_keep(sc) -> None:
    trace = [_entry(attempt_id="a-0", metric_after=0.3, decision="revert"), _entry(attempt_id="a-1")]
    assert sc.stall_report(trace, window=2)["stalled"] is False


def test_stall_report_with_too_few_entries_is_not_a_stall(sc) -> None:
    assert sc.stall_report([_entry(decision="revert", metric_after=0.9)], window=3)["stalled"] is False


def test_stall_report_ignores_invalid_entries_and_says_so(sc) -> None:
    report = sc.stall_report([_entry(decision="maybe")] * 3, window=3)
    assert report["stalled"] is False
    assert report["invalid"] == 3


def test_valid_mechanism_card_passes(sc) -> None:
    assert sc.validate_mechanism_card(_card()) == []


@pytest.mark.parametrize("owner", ["phylax", "telos", "agate", "Phylax"])
def test_a_mechanism_touching_a_fixed_wall_is_refused_before_measurement(sc, owner: str) -> None:
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors)


def test_a_card_must_authorize_nothing(sc) -> None:
    assert any("scope_record" in e for e in sc.validate_mechanism_card(_card(scope_record={"authorizes": "merge"})))


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "approved"},
        {"revision": 0},
        {"revision": True},
        {"delta": float("nan")},
        {"evaluator_digest": "short"},
        {"evidence_ids": []},
        {"owner_slices": []},
        {"mechanism_id": ""},
    ],
)
def test_malformed_cards_are_refused(sc, bad) -> None:
    assert sc.validate_mechanism_card(_card(**bad))


def test_a_graduated_card_needs_a_dry_run_that_did_not_launch_or_retry(sc) -> None:
    receipt = {"ok": True, "retries": 1, "launched": False}
    errors = sc.validate_mechanism_card(_card(status="graduated", dry_run_receipt=receipt))
    assert any("dry_run_receipt" in e for e in errors)


def test_card_validation_does_not_mutate_its_input(sc) -> None:
    card = _card()
    before = copy.deepcopy(card)
    sc.validate_mechanism_card(card)
    assert card == before


def test_checked_in_fixtures_match_the_validator(sc) -> None:
    root = ROOT / "tests" / "fixtures" / "mechanism_card"
    valid = sorted(root.glob("valid-*.json"))
    invalid = sorted(root.glob("invalid-*.json"))
    assert valid and invalid
    for path in valid:
        assert sc.validate_mechanism_card(json.loads(path.read_text())) == [], path.name
    for path in invalid:
        assert sc.validate_mechanism_card(json.loads(path.read_text())), path.name


def test_the_schema_is_shape_only_and_names_the_python_authority() -> None:
    schema = json.loads((ROOT / "docs/v2/references/biafra/mechanism-card.schema.json").read_text())
    assert schema["type"] == "object"
    assert "validate_mechanism_card" in schema["description"]
    assert set(schema["required"]) >= {"mechanism_id", "scope_record", "owner_slices", "status"}


def test_dry_cycle_emits_a_valid_trace_entry(tmp_path: Path, sc) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    result = cycle.dry_cycle("inner", "harden", 0.20, 0.10, tmp_path, evaluator_digest=DIGEST)
    assert sc.validate_trace_entry(result["trace"]) == []
    assert result["trace"]["decision"] == "keep"


def test_dry_cycle_refuses_a_non_finite_metric(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    result = cycle.dry_cycle("outer", "harden", 0.20, float("nan"), tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "non-finite-metric"
    assert result["launched"] is False


def test_biafra_is_canonical_additively() -> None:
    registry = yaml.safe_load((ROOT / "bin/agents/REGISTRY.yml").read_text())
    rows = {r["staging_folder"]: r for r in registry["roles"]}
    outer = rows["metaresearch-outer"]
    assert outer["display"] == "Biafra"
    assert outer["canonical_agent"] == "biafra"
    assert outer["seat"] == "outer"
    assert outer["openclaw_id"] == "metaresearch-outer"
    assert outer["soul_id"] == "perpetua.autoresearch.outer"
    assert rows["autoresearch-inner"]["seat"] == "inner"
    assert rows["autoresearcher"]["display"] == "Scout"
    assert rows["autoresearcher"]["seat"] == "inner-scout"


def test_biafra_persona_exists_and_keeps_the_hard_limits() -> None:
    persona = yaml.safe_load((ROOT / "bin/agents/personas/biafra.yaml").read_text())
    assert persona["name"] == "Biafra"
    assert persona["openclaw_id"] == "metaresearch-outer"
    rules = " ".join(persona["hard_rules"]).lower()
    for phrase in ("verifier", "operator gate", "evidence"):
        assert phrase in rules
    soul = (ROOT / "bin/agents/metaresearch-outer/SOUL.md").read_text()
    assert "Biafra" in soul
    assert "never starts" in soul


# --- model and effort policy (operator clarification 2026-11-17) ---------------------------


def test_default_effort_ladder_is_medium_then_high_then_low(sc) -> None:
    assert sc.EFFORT_LADDER == ("medium", "high", "low")
    assert sc.select_effort(("low", "high", "medium")) == "medium"
    assert sc.select_effort(("low", "high")) == "high"
    assert sc.select_effort(("low",)) == "low"


@pytest.mark.parametrize("supported", [(), ("xhigh", "max"), ("max",)])
def test_effort_never_selects_xhigh_or_max(sc, supported) -> None:
    assert sc.select_effort(supported) is None


def test_free_turn_runs_the_default_ladder_with_no_approval(sc) -> None:
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=False, supported=("high", "low"))
    assert plan == {
        "tier": "default", "model": None, "effort": "high", "human_gated": False, "auto_run": True,
    }


@pytest.mark.parametrize("approved", [None, 0, 1, "yes", "true"])
def test_only_a_literal_true_approves_a_paid_preference(sc, approved) -> None:
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=approved)
    assert plan["tier"] == "default" and plan["auto_run"] is True


@pytest.mark.parametrize(
    ("seat", "platform", "model", "effort"),
    [
        ("outer", "anthropic", "Claude Fable 5.2", "high"),
        ("inner", "anthropic", "Claude Opus 5.5", "medium"),
        ("outer", "openai", "GPT-6 Astra", "high"),
        ("inner", "openai", "GPT-6.1 Sol", "medium"),
    ],
)
def test_preferred_paid_models_need_explicit_approval(sc, seat, platform, model, effort) -> None:
    plan = sc.plan_turn(seat, platform=platform, paid_approved=True)
    assert plan == {
        "tier": "preferred", "model": model, "effort": effort, "human_gated": True, "auto_run": False,
    }
    assert sc.plan_turn(seat, platform=platform, paid_approved=False)["tier"] == "default"


def test_unknown_platform_falls_back_even_when_approved(sc) -> None:
    assert sc.plan_turn("outer", platform="other", paid_approved=True)["tier"] == "default"


def test_no_preferred_effort_is_xhigh_or_max(sc) -> None:
    assert all(effort in sc.EFFORT_LADDER for _model, effort in sc.PREFERRED_PAID.values())


def test_policy_text_is_in_the_plan_and_the_persona() -> None:
    plan = (ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md").read_text()
    assert "human-gated" in plan and "Fable 5.2" in plan and "free W&B" in plan
    persona = yaml.safe_load((ROOT / "bin/agents/personas/biafra.yaml").read_text())
    assert any("human-gated" in rule for rule in persona["hard_rules"])


# --- defects found by the live review pass (2026-11-17) -------------------------------------


@pytest.mark.parametrize(
    "owner",
    ["oramasys/phylax", "phylax.admission", "phylax-policy", "Ｐhylax", "ph​ylax", "TELOS_endpoint", "agate/fit"],
)
def test_fixed_wall_owner_cannot_be_hidden_in_a_longer_name(sc, owner: str) -> None:
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors), owner


@pytest.mark.parametrize("owner", ["kungfu", "anamnesis", "alexandria", "perpetua-core"])
def test_ordinary_owners_are_not_refused(sc, owner: str) -> None:
    assert sc.validate_mechanism_card(_card(owner_slices=[owner])) == []


@pytest.mark.parametrize("bad", [None, 5, 1.5, True])
def test_non_mapping_input_is_an_error_not_a_crash(sc, bad) -> None:
    assert sc.validate_trace_entry(bad) == ["entry must be an object"]
    assert sc.validate_mechanism_card(bad) == ["card must be an object"]


def test_a_bare_string_is_one_effort_not_a_set_of_letters(sc) -> None:
    assert sc.select_effort("medium") == "medium"
    assert sc.select_effort("xhigh") is None


# --- security review follow-up: normalize first, then substring, reject non-ASCII -----------


@pytest.mark.parametrize(
    "owner",
    ["Phýlax", "phylaxpolicy", "xtelosx", "my_agate_adapter", "Рhylax", "phуlax", "pḣylax"],
)
def test_owner_check_survives_accents_glued_names_and_lookalikes(sc, owner: str) -> None:
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors), owner


def test_over_refusal_is_deliberate_and_documented(sc) -> None:
    # "propagate" contains "agate"; fail-closed is the intent, so it is refused.
    assert any("E_OWNER" in e for e in sc.validate_mechanism_card(_card(owner_slices=["propagate"])))


def test_owner_names_are_checked_one_at_a_time(sc) -> None:
    # "pery" + "lax" must not combine across entries into a false match.
    assert sc.validate_mechanism_card(_card(owner_slices=["phy", "lax"])) == []


@pytest.mark.parametrize("owner", ["---", "___", "​​ "])
def test_an_owner_with_no_identity_is_refused(sc, owner: str) -> None:
    assert sc.validate_mechanism_card(_card(owner_slices=[owner]))


# --- correct W&B defaults and cited references (operator request 2026-11-17) ---------------

V1017 = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
V41 = "deepseek-ai/DeepSeek-V4.1-Flash"
V0731 = "deepseek-ai/DeepSeek-V4-Flash-0731"


def test_wandb_model_order_matches_the_launcher(sc) -> None:
    source = (ROOT / "bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py").read_text()
    assert f'DEFAULT_MODEL = "{sc.WANDB_MODEL_ORDER[0]}"' in source
    assert sc.WANDB_MODEL_ORDER == (V1017, V41, V0731)
    assert "never xhigh or max" in source


def test_v41_models_reject_medium_and_v4_flash_0731_accepts_it(sc) -> None:
    assert "medium" not in sc.WANDB_EFFORTS[V1017]
    assert "medium" not in sc.WANDB_EFFORTS[V41]
    assert sc.select_effort(sc.WANDB_EFFORTS[V0731]) == "medium"
    assert set(sc.WANDB_EFFORTS) == set(sc.WANDB_MODEL_ORDER)


def test_the_free_default_turn_is_v41_1017_at_high(sc) -> None:
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=False)
    assert plan == {
        "tier": "default", "provider": "wandb", "model": V1017, "effort": "high",
        "human_gated": False, "auto_run": True,
    }


def test_the_fallback_walks_the_model_order_then_the_effort_ladder(sc) -> None:
    assert sc.default_wandb_turn(unavailable=(V1017,))["model"] == V41
    third = sc.default_wandb_turn(unavailable=(V1017, V41))
    assert (third["model"], third["effort"]) == (V0731, "medium")


def test_no_available_wandb_model_is_reported_not_guessed(sc) -> None:
    plan = sc.default_wandb_turn(unavailable=sc.WANDB_MODEL_ORDER)
    assert plan["model"] is None and plan["effort"] is None
    assert plan["reason"] == "no-wandb-model-available"


def test_default_turns_never_select_xhigh_or_max(sc) -> None:
    for blocked in ((), (V1017,), (V1017, V41)):
        assert sc.default_wandb_turn(unavailable=blocked)["effort"] in sc.EFFORT_LADDER


def test_the_plan_cites_correct_references_and_defaults() -> None:
    plan = (ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md").read_text()
    for needle in (
        "https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py",
        "https://github.com/diazMelgarejo/orama-system/blob/main/docs/stale-reference-ledger-2026-11-12.md",
        "https://github.com/diazMelgarejo/orama-system/pull/496",
        "https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/LESSONS.md",
        "lesson_d4ff6f4278ad", "lesson_8e02c7fd391d", "lesson_8d873e4e2f73",
        "DeepSeek-V4.1-Flash-1017", "high",
    ):
        assert needle in plan, needle


# --- the eight verified review defects (loop round 1) -------------------------------------


def test_1_scout_is_a_legal_seat_and_distinct_from_the_inner_seat(sc) -> None:
    assert sc.validate_trace_entry(_entry(seat="inner-scout")) == []
    assert "inner-scout" in sc.SEATS and "inner" in sc.SEATS and "outer" in sc.SEATS
    registry = yaml.safe_load((ROOT / "bin/agents/REGISTRY.yml").read_text())
    seats = {r["seat"] for r in registry["roles"] if "seat" in r}
    assert seats <= set(sc.SEATS)


def test_2_attempt_ids_differ_between_attempts(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    a = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "a", evaluator_digest=DIGEST)
    b = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "b", evaluator_digest=DIGEST)
    c = cycle.dry_cycle("inner", "harden", 0.2, 0.3, tmp_path / "c", evaluator_digest=DIGEST)
    ids = {a["trace"]["attempt_id"], b["trace"]["attempt_id"], c["trace"]["attempt_id"]}
    assert len(ids) == 3
    assert "dry-1" not in a["trace"]["attempt_id"]


def test_2_metric_name_and_attempt_id_can_be_supplied(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle(
        "inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest=DIGEST,
        metric_name="val_bpb", attempt_id="run-7",
    )
    assert r["trace"]["metric_name"] == "val_bpb" and r["trace"]["attempt_id"] == "run-7"


def test_3_a_cycle_without_a_digest_says_it_recorded_nothing(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path)
    assert r["ok"] is True and r["trace"] is None
    assert r["recorded"] is False and r["warning"] == "no-evaluator-digest"
    r2 = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "x", evaluator_digest=DIGEST)
    assert r2["recorded"] is True and "warning" not in r2


def test_3_the_soul_cards_state_the_conditional_contract() -> None:
    for rel in ("bin/agents/autoresearch-inner/SOUL.md", "bin/agents/autoresearcher/README.md"):
        text = (ROOT / rel).read_text()
        assert "recorded: false" in text or "recorded:false" in text, rel


def test_4_a_bad_digest_does_not_consume_the_single_attempt(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    bad = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest="A" * 64)
    assert bad["ok"] is False and bad["reason"] == "invalid-trace"
    good = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest=DIGEST)
    assert good["ok"] is True, good


@pytest.mark.parametrize("bad", [None, "0.1", True, False, [1]])
def test_5_non_numeric_metrics_are_refused_not_raised(tmp_path: Path, bad) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    for args in ((bad, 0.5), (0.5, bad)):
        r = cycle.dry_cycle("inner", "harden", *args, tmp_path / str(id(args)))
        assert r["ok"] is False and r["reason"] == "non-finite-metric"
        assert r["launched"] is False


def test_6_a_digest_with_a_trailing_newline_is_refused(sc) -> None:
    assert sc.validate_trace_entry(_entry(evaluator_digest=DIGEST + "\n"))
    assert sc.validate_mechanism_card(_card(evaluator_digest=DIGEST + "\n"))


def test_6_an_empty_verifier_set_has_no_digest(sc, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        sc.evaluator_digest([])
    with pytest.raises(ValueError):
        sc.evaluator_digest([tmp_path])  # a directory is not a verifier file


def test_7_reverted_and_delta_must_agree(sc) -> None:
    assert any("reverted" in e for e in sc.validate_mechanism_card(_card(reverted=True, delta=-0.5)))
    assert any("reverted" in e for e in sc.validate_mechanism_card(_card(reverted=False, delta=0.5)))
    assert sc.validate_mechanism_card(_card(reverted=True, delta=0.5)) == []
    assert sc.validate_mechanism_card(_card(reverted=False, delta=-0.5)) == []


def test_7_graduated_cannot_be_a_reverted_card(sc) -> None:
    errors = sc.validate_mechanism_card(_card(status="graduated", reverted=True, delta=1.5))
    assert any("graduated" in e for e in errors)


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
def test_7_reviewed_and_graduated_need_a_real_dry_run(sc, status: str) -> None:
    assert any("dry_run_receipt" in e for e in sc.validate_mechanism_card(_card(status=status, dry_run_receipt={})))


def test_8_unknown_card_fields_are_refused(sc) -> None:
    errors = sc.validate_mechanism_card(_card(targets=["oramasys/phylax/admission.py"]))
    assert any("unknown" in e for e in errors)


def test_8_the_schema_matches_the_allowlist_and_the_soul_is_honest(sc) -> None:
    schema = json.loads((ROOT / "docs/v2/references/biafra/mechanism-card.schema.json").read_text())
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(sc.CARD_FIELDS)
    soul = (ROOT / "bin/agents/metaresearch-outer/SOUL.md").read_text()
    assert "owner_slices" in soul and "touches Phylax, Telos or Agate policy" not in soul


# --- CodeRabbit comment on seat_contracts.py line 30 (real review, PR 519): huge integers -----


@pytest.mark.parametrize("huge", [10**400, -10**400, 2**1024])
def test_huge_integers_are_refused_not_raised(sc, huge: int) -> None:
    assert sc.is_finite_number(huge) is False
    assert any("delta" in e for e in sc.validate_mechanism_card(_card(delta=huge)))
    assert any("metric_before" in e for e in sc.validate_trace_entry(_entry(metric_before=huge)))
    assert any("metric_after" in e for e in sc.validate_trace_entry(_entry(metric_after=huge)))


def test_stall_report_counts_a_huge_metric_as_invalid_not_a_crash(sc) -> None:
    report = sc.stall_report([_entry(metric_after=10**400)] * 3, window=3)
    assert report["invalid"] == 3 and report["stalled"] is False


def test_the_cycle_refuses_a_huge_metric(tmp_path: Path) -> None:
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle("inner", "harden", 10**400, 0.5, tmp_path)
    assert r["ok"] is False and r["reason"] == "non-finite-metric" and r["launched"] is False


def test_large_but_representable_numbers_are_still_measurements(sc) -> None:
    assert all(sc.is_finite_number(v) for v in (10**15, 10**308, 1.7976931348623157e308, -3, 0.25))


def test_the_representable_boundary_is_pinned(sc) -> None:
    import sys

    top = int(sys.float_info.max)
    assert sc.is_finite_number(top) is True
    assert sc.is_finite_number(-top) is True
    assert sc.is_finite_number(2 * top) is False
    assert sc.is_finite_number(-2 * top) is False
    assert sc.is_finite_number(2**1024 - 2**970) is False


def test_the_finite_helper_states_its_real_domain() -> None:
    text = (ROOT / "bin/agents/seat_contracts.py").read_text()
    assert "after conversion to float" in text


# --- defect observed in the first real live turn: the outer seat's card had a sentence as owner ---

REAL_SENTENCE = (
    "the repository that owns bin/agents/seat_contracts.py and "
    "bin/orama-system/skills/metaresearcher/SKILL.md"
)


@pytest.mark.parametrize(
    "owners",
    [
        [REAL_SENTENCE], ["orama system repo"], ["kungfu and anamnesis"], [" kungfu"], ["kungfu "],
        ["kungfu\n"], ["kun\tgfu"], ["a" * 65], ["kungfu,anamnesis"], ["kungfu", "the other repo"],
    ],
)
def test_owner_slices_must_be_repository_identifiers(sc, owners) -> None:
    errors = sc.validate_mechanism_card(_card(owner_slices=owners))
    assert any("owner_slices" in e for e in errors), owners


@pytest.mark.parametrize(
    "owners",
    [["kungfu"], ["orama-system"], ["perpetua-tools"], ["anamnesis", "alexandria"],
     ["diazMelgarejo/orama-system"], ["perpetua-core"], ["a.b_c-d"], ["a" * 64]],
)
def test_ordinary_repository_names_are_accepted(sc, owners) -> None:
    assert sc.validate_mechanism_card(_card(owner_slices=owners)) == []


def test_a_fixed_wall_name_reports_e_owner_even_when_it_is_not_identifier_shaped(sc) -> None:
    for name in ("Ｐhylax", "ph​ylax", "Рhylax", "Phýlax", "agate/fit", "xtelosx"):
        errors = sc.validate_mechanism_card(_card(owner_slices=[name]))
        assert any("E_OWNER" in e for e in errors), name


def test_owner_errors_never_raises(sc) -> None:
    for bad in (None, 5, "kungfu", [], [None], [5], [["x"]], {"a": 1}):
        assert isinstance(sc._owner_errors(bad), list)


# --- turn 3: degenerate identifiers and the blank-entry message (defects reported by the outer seat,
# --- reproduced by the reviewer) ------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["a.", "a/", "a//b", "a/../b", "a/./b", "a/.", "a/.hidden", "a/b/", "a/b."],
)
def test_degenerate_identifiers_are_refused(sc, name: str) -> None:
    errors = sc.validate_mechanism_card(_card(owner_slices=[name]))
    assert any("repository identifiers" in e for e in errors), name


@pytest.mark.parametrize("name", ["a", "1", "org/repo.name", "a.b.c", "x-y_z", "a/b/c"])
def test_short_and_dotted_but_valid_identifiers_are_accepted(sc, name: str) -> None:
    assert sc.validate_mechanism_card(_card(owner_slices=[name])) == []


@pytest.mark.parametrize("owners", [["", "orama-system"], ["   "], [" "]])
def test_a_blank_entry_is_not_blamed_on_the_list(sc, owners) -> None:
    msg = " ".join(sc._owner_errors(owners))
    assert msg and "non-empty list" not in msg and "entries" in msg


@pytest.mark.parametrize("owners", [[], "kungfu", None])
def test_an_empty_or_missing_list_is_still_blamed_on_the_list(sc, owners) -> None:
    assert "non-empty list" in " ".join(sc._owner_errors(owners))


def test_the_identifier_error_names_the_entry_but_stays_bounded(sc) -> None:
    assert "a//b" in " ".join(sc._owner_errors(["a//b"]))
    huge = "x/" * 3000
    msg = " ".join(sc._owner_errors([huge, huge]))
    assert len(msg) < 400, len(msg)


@pytest.mark.parametrize("bad", [[123], [None], [True], [b"kungfu"], [["kungfu"]]])
def test_non_string_entries_are_refused_without_raising(sc, bad) -> None:
    assert sc._owner_errors(bad)
