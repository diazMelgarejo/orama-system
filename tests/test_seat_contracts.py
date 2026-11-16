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
