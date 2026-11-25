"""Seat contracts shared by Scout, the inner seat and Biafra (the outer seat).

The Python validator is the authority. The JSON Schema in docs is shape-only.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
import threading
from pathlib import Path
from types import MappingProxyType, ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "bin" / "agents" / "seat_contracts.py"
CYCLE = ROOT / "bin" / "agents" / "biafra_cycle.py"
DIGEST = "a" * 64


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(path: Path, name: str):
    """Import the module at `path` under `name` and return it."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sc():
    """Provide the freshly loaded seat_contracts module."""
    return _load(CONTRACTS, "seat_contracts")


def _entry(**over):
    """Return a valid trace entry, with any keyword overrides applied."""
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
    """Return a valid candidate mechanism card, with any keyword overrides applied."""
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
    """A valid trace entry yields no validation errors."""
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
    """Each malformed trace entry produces at least one error."""
    assert sc.validate_trace_entry(_entry(**bad))


def test_trace_entry_must_agree_with_its_metrics(sc) -> None:
    """A keep decision on a worse metric is reported as an error."""
    errors = sc.validate_trace_entry(_entry(metric_before=0.1, metric_after=0.2, decision="keep"))
    assert any("decision" in e for e in errors)


def test_missing_field_is_named(sc) -> None:
    """A trace entry missing a field gets an error that names it."""
    entry = _entry()
    del entry["hypothesis"]
    assert any("hypothesis" in e for e in sc.validate_trace_entry(entry))


def test_evaluator_digest_changes_when_a_verifier_file_changes(sc, tmp_path: Path) -> None:
    """Editing a verifier file changes its 64-character digest."""
    (tmp_path / "check.py").write_text("assert True\n")
    first = sc.evaluator_digest([tmp_path / "check.py"])
    (tmp_path / "check.py").write_text("assert False\n")
    assert sc.evaluator_digest([tmp_path / "check.py"]) != first
    assert len(first) == 64


def test_stall_report_names_a_repeat_revert_window(sc) -> None:
    """Three consecutive reverts are reported as a stall with their ids."""
    trace = [_entry(attempt_id=f"a-{i}", metric_before=0.2, metric_after=0.3, decision="revert") for i in range(3)]
    report = sc.stall_report(trace, window=3)
    assert report["stalled"] is True
    assert report["entry_ids"] == ["a-0", "a-1", "a-2"]


def test_stall_report_is_clear_after_a_keep(sc) -> None:
    """A keep in the window means no stall is reported."""
    trace = [_entry(attempt_id="a-0", metric_after=0.3, decision="revert"), _entry(attempt_id="a-1")]
    assert sc.stall_report(trace, window=2)["stalled"] is False


def test_stall_report_with_too_few_entries_is_not_a_stall(sc) -> None:
    """Fewer entries than the window never count as a stall."""
    assert sc.stall_report([_entry(decision="revert", metric_after=0.9)], window=3)["stalled"] is False


def test_stall_report_ignores_invalid_entries_and_says_so(sc) -> None:
    """Invalid entries are skipped and counted in the report."""
    report = sc.stall_report([_entry(decision="maybe")] * 3, window=3)
    assert report["stalled"] is False
    assert report["invalid"] == 3


def test_valid_mechanism_card_passes(sc) -> None:
    """A valid candidate card yields no validation errors."""
    assert sc.validate_mechanism_card(_card()) == []


@pytest.mark.parametrize("owner", ["phylax", "telos", "agate", "Phylax"])
def test_a_mechanism_touching_a_fixed_wall_is_refused_before_measurement(sc, owner: str) -> None:
    """An owner slice naming a fixed wall is refused with E_OWNER."""
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors)


def test_a_card_must_authorize_nothing(sc) -> None:
    """A card whose scope_record authorizes anything is refused."""
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
    """Each malformed card produces at least one error."""
    assert sc.validate_mechanism_card(_card(**bad))


def test_a_graduated_card_needs_a_dry_run_that_did_not_launch_or_retry(sc) -> None:
    """A graduated card with a retried dry run is refused."""
    receipt = {"ok": True, "retries": 1, "launched": False}
    errors = sc.validate_mechanism_card(_card(status="graduated", dry_run_receipt=receipt))
    assert any("dry_run_receipt" in e for e in errors)


def test_card_validation_does_not_mutate_its_input(sc) -> None:
    """Validating a card leaves the card unchanged."""
    card = _card()
    before = copy.deepcopy(card)
    sc.validate_mechanism_card(card)
    assert card == before


def test_checked_in_fixtures_match_the_validator(sc) -> None:
    """Valid fixture cards pass and invalid ones fail the validator."""
    root = ROOT / "tests" / "fixtures" / "mechanism_card"
    valid = sorted(root.glob("valid-*.json"))
    invalid = sorted(root.glob("invalid-*.json"))
    assert valid and invalid
    for path in valid:
        card = json.loads(path.read_text())
        pin = card["evaluator_digest"] if card["status"] == "graduated" else None  # graduated needs the run's pin
        assert sc.validate_mechanism_card(card, pinned_digest=pin) == [], path.name
    for path in invalid:
        card = json.loads(path.read_text())
        assert sc.validate_mechanism_card(card, pinned_digest=card.get("evaluator_digest")), path.name


def test_the_schema_is_shape_only_and_names_the_python_authority() -> None:
    """The JSON Schema is object-shaped and cites the Python validator."""
    schema = json.loads((ROOT / "docs/v2/references/biafra/mechanism-card.schema.json").read_text())
    assert schema["type"] == "object"
    assert "validate_mechanism_card" in schema["description"]
    assert set(schema["required"]) >= {"mechanism_id", "scope_record", "owner_slices", "status"}


def test_dry_cycle_emits_a_valid_trace_entry(tmp_path: Path, sc) -> None:
    """A dry cycle with a digest returns a valid keep trace entry."""
    cycle = _load(CYCLE, "biafra_cycle")
    result = cycle.dry_cycle("inner", "harden", 0.20, 0.10, tmp_path, evaluator_digest=DIGEST)
    assert sc.validate_trace_entry(result["trace"]) == []
    assert result["trace"]["decision"] == "keep"


def test_dry_cycle_refuses_a_non_finite_metric(tmp_path: Path) -> None:
    """A NaN metric is refused without launching."""
    cycle = _load(CYCLE, "biafra_cycle")
    result = cycle.dry_cycle("outer", "harden", 0.20, float("nan"), tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "non-finite-metric"
    assert result["launched"] is False


def test_biafra_is_canonical_additively() -> None:
    """The registry lists Biafra and Scout with the expected seats and ids."""
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
    """The Biafra persona and soul card keep the hard limits."""
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
    """The effort ladder is medium, high, low and picks in that order."""
    assert sc.EFFORT_LADDER == ("medium", "high", "low")
    assert sc.select_effort(("low", "high", "medium")) == "medium"
    assert sc.select_effort(("low", "high")) == "high"
    assert sc.select_effort(("low",)) == "low"


@pytest.mark.parametrize("supported", [(), ("xhigh", "max"), ("max",)])
def test_effort_never_selects_xhigh_or_max(sc, supported) -> None:
    """Effort selection returns None when only xhigh or max are supported."""
    assert sc.select_effort(supported) is None


def test_free_turn_runs_the_default_ladder_with_no_approval(sc) -> None:
    """An unapproved turn uses the default tier, auto-run and ungated."""
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=False, supported=("high", "low"))
    assert plan == {
        "tier": "default", "model": None, "effort": "high", "human_gated": False, "auto_run": True,
    }


@pytest.mark.parametrize("approved", [None, 0, 1, "yes", "true"])
def test_only_a_literal_true_approves_a_paid_preference(sc, approved) -> None:
    """Only a literal True for paid_approved leaves the default tier."""
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=approved)
    assert plan["tier"] == "default" and plan["auto_run"] is True


@pytest.mark.parametrize(
    ("seat", "platform", "model", "effort"),
    [
        ("outer", "anthropic", "Claude Fable 5.2", "high"),
        ("inner", "anthropic", "Claude Opus 5.5", "medium"),
        ("outer", "openai", "GPT-6.2 Astra", "high"),
        ("inner", "openai", "GPT-6.2 Sol", "medium"),
    ],
)
def test_preferred_paid_models_need_explicit_approval(sc, seat, platform, model, effort) -> None:
    """Approved paid turns get the preferred model, human-gated and not auto-run."""
    plan = sc.plan_turn(seat, platform=platform, paid_approved=True)
    assert plan == {
        "tier": "preferred", "model": model, "effort": effort, "human_gated": True, "auto_run": False,
    }
    assert sc.plan_turn(seat, platform=platform, paid_approved=False)["tier"] == "default"


def test_unknown_platform_falls_back_even_when_approved(sc) -> None:
    """An unknown platform stays on the default tier even if approved."""
    assert sc.plan_turn("outer", platform="other", paid_approved=True)["tier"] == "default"


def test_no_preferred_effort_is_xhigh_or_max(sc) -> None:
    """Every preferred paid effort belongs to the effort ladder."""
    assert all(effort in sc.EFFORT_LADDER for _model, effort in sc.PREFERRED_PAID.values())


def test_policy_text_is_in_the_plan_and_the_persona() -> None:
    """The plan and persona both state the human-gated policy."""
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
    """Fixed-wall names embedded in longer or disguised owners are refused."""
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors), owner


@pytest.mark.parametrize("owner", ["kungfu", "anamnesis", "alexandria", "perpetua-core"])
def test_ordinary_owners_are_not_refused(sc, owner: str) -> None:
    """Ordinary repository owners pass the owner check."""
    assert sc.validate_mechanism_card(_card(owner_slices=[owner])) == []


@pytest.mark.parametrize("bad", [None, 5, 1.5, True])
def test_non_mapping_input_is_an_error_not_a_crash(sc, bad) -> None:
    """Non-object input gives an error message instead of raising."""
    assert sc.validate_trace_entry(bad) == ["entry must be an object"]
    assert sc.validate_mechanism_card(bad) == ["card must be an object"]


def test_a_bare_string_is_one_effort_not_a_set_of_letters(sc) -> None:
    """A bare string is treated as one effort value, not iterated."""
    assert sc.select_effort("medium") == "medium"
    assert sc.select_effort("xhigh") is None


# --- security review follow-up: normalize first, then substring, reject non-ASCII -----------


@pytest.mark.parametrize(
    "owner",
    ["Phýlax", "phylaxpolicy", "xtelosx", "my_agate_adapter", "Рhylax", "phуlax", "pḣylax"],
)
def test_owner_check_survives_accents_glued_names_and_lookalikes(sc, owner: str) -> None:
    """Accented, glued and lookalike fixed-wall names are still refused."""
    errors = sc.validate_mechanism_card(_card(owner_slices=["kungfu", owner]))
    assert any("E_OWNER" in e for e in errors), owner


def test_over_refusal_is_deliberate_and_documented(sc) -> None:
    # "propagate" contains "agate"; fail-closed is the intent, so it is refused.
    """An owner containing a wall name as a substring is refused on purpose."""
    assert any("E_OWNER" in e for e in sc.validate_mechanism_card(_card(owner_slices=["propagate"])))


def test_owner_names_are_checked_one_at_a_time(sc) -> None:
    # "pery" + "lax" must not combine across entries into a false match.
    """Owner entries are checked separately, never joined into a match."""
    assert sc.validate_mechanism_card(_card(owner_slices=["phy", "lax"])) == []


@pytest.mark.parametrize("owner", ["---", "___", "​​ "])
def test_an_owner_with_no_identity_is_refused(sc, owner: str) -> None:
    """Owners made only of punctuation or invisible characters are refused."""
    assert sc.validate_mechanism_card(_card(owner_slices=[owner]))


# --- correct W&B defaults and cited references (operator request 2026-11-17) ---------------

V1017 = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
V41 = "deepseek-ai/DeepSeek-V4.1-Flash"
V0731 = "deepseek-ai/DeepSeek-V4-Flash-0731"


def test_wandb_model_order_matches_the_launcher(sc) -> None:
    """The W&B model order matches the launcher default and effort wording."""
    source = (ROOT / "bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py").read_text()
    assert f'DEFAULT_MODEL = "{sc.WANDB_MODEL_ORDER[0]}"' in source
    assert sc.WANDB_MODEL_ORDER == (V1017, V41, V0731)
    assert "never xhigh or max" in source


def test_v41_models_reject_medium_and_v4_flash_0731_accepts_it(sc) -> None:
    """Only the V4-Flash-0731 model accepts the medium effort."""
    assert "medium" not in sc.WANDB_EFFORTS[V1017]
    assert "medium" not in sc.WANDB_EFFORTS[V41]
    assert sc.select_effort(sc.WANDB_EFFORTS[V0731]) == "medium"
    assert set(sc.WANDB_EFFORTS) == set(sc.WANDB_MODEL_ORDER)


def test_the_free_default_turn_is_v41_1017_at_high(sc) -> None:
    """The free default turn is the 1017 model at high effort."""
    plan = sc.plan_turn("outer", platform="anthropic", paid_approved=False)
    assert plan == {
        "tier": "default", "provider": "wandb", "model": V1017, "effort": "high",
        "human_gated": False, "auto_run": True,
    }


def test_the_fallback_walks_the_model_order_then_the_effort_ladder(sc) -> None:
    """Unavailable models fall back along the order with their efforts."""
    assert sc.default_wandb_turn(unavailable=(V1017,))["model"] == V41
    third = sc.default_wandb_turn(unavailable=(V1017, V41))
    assert (third["model"], third["effort"]) == (V0731, "medium")


def test_no_available_wandb_model_is_reported_not_guessed(sc) -> None:
    """With every model unavailable the plan reports no model."""
    plan = sc.default_wandb_turn(unavailable=sc.WANDB_MODEL_ORDER)
    assert plan["model"] is None and plan["effort"] is None
    assert plan["reason"] == "no-wandb-model-available"


def test_default_turns_never_select_xhigh_or_max(sc) -> None:
    """Default W&B turns always use an effort from the ladder."""
    for blocked in ((), (V1017,), (V1017, V41)):
        assert sc.default_wandb_turn(unavailable=blocked)["effort"] in sc.EFFORT_LADDER


def test_the_plan_cites_correct_references_and_defaults() -> None:
    """The canonical plan cites the expected references and defaults."""
    plan = (ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md").read_text()
    for needle in (
        "../../bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py",
        "../stale-reference-ledger-2026-11-12.md",
        "https://github.com/diazMelgarejo/orama-system/pull/496",
        "https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/LESSONS.md",
        "lesson_d4ff6f4278ad", "lesson_8e02c7fd391d", "lesson_8d873e4e2f73",
        "DeepSeek-V4.1-Flash-1017", "high",
    ):
        assert needle in plan, needle


# --- the eight verified review defects (loop round 1) -------------------------------------


def test_1_scout_is_a_legal_seat_and_distinct_from_the_inner_seat(sc) -> None:
    """inner-scout is a legal seat and every registry seat is known."""
    assert sc.validate_trace_entry(_entry(seat="inner-scout")) == []
    assert "inner-scout" in sc.SEATS and "inner" in sc.SEATS and "outer" in sc.SEATS
    registry = yaml.safe_load((ROOT / "bin/agents/REGISTRY.yml").read_text())
    seats = {r["seat"] for r in registry["roles"] if "seat" in r}
    assert seats <= set(sc.SEATS)


def test_2_attempt_ids_differ_between_attempts(tmp_path: Path) -> None:
    """Separate dry cycles produce distinct, non-constant attempt ids."""
    cycle = _load(CYCLE, "biafra_cycle")
    a = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "a", evaluator_digest=DIGEST)
    b = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "b", evaluator_digest=DIGEST)
    c = cycle.dry_cycle("inner", "harden", 0.2, 0.3, tmp_path / "c", evaluator_digest=DIGEST)
    ids = {a["trace"]["attempt_id"], b["trace"]["attempt_id"], c["trace"]["attempt_id"]}
    assert len(ids) == 3
    assert "dry-1" not in a["trace"]["attempt_id"]


def test_2_metric_name_and_attempt_id_can_be_supplied(tmp_path: Path) -> None:
    """A dry cycle records a supplied metric name and attempt id."""
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle(
        "inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest=DIGEST,
        metric_name="val_bpb", attempt_id="run-7",
    )
    assert r["trace"]["metric_name"] == "val_bpb" and r["trace"]["attempt_id"] == "run-7"


def test_3_a_cycle_without_a_digest_says_it_recorded_nothing(tmp_path: Path) -> None:
    """Without a digest a cycle returns no trace and warns it recorded nothing."""
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path)
    assert r["ok"] is True and r["trace"] is None
    assert r["recorded"] is False and r["warning"] == "no-evaluator-digest"
    r2 = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path / "x", evaluator_digest=DIGEST)
    assert r2["recorded"] is True and "warning" not in r2


def test_3_the_soul_cards_state_the_conditional_contract() -> None:
    """The inner soul and Scout README state the recorded:false rule."""
    for rel in ("bin/agents/autoresearch-inner/SOUL.md", "bin/agents/autoresearcher/README.md"):
        text = (ROOT / rel).read_text()
        assert "recorded: false" in text or "recorded:false" in text, rel


def test_4_a_bad_digest_does_not_consume_the_single_attempt(tmp_path: Path) -> None:
    """An invalid digest is refused without using up the single attempt."""
    cycle = _load(CYCLE, "biafra_cycle")
    bad = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest="A" * 64)
    assert bad["ok"] is False and bad["reason"] == "invalid-trace"
    good = cycle.dry_cycle("inner", "harden", 0.2, 0.1, tmp_path, evaluator_digest=DIGEST)
    assert good["ok"] is True, good


@pytest.mark.parametrize("bad", [None, "0.1", True, False, [1]])
def test_5_non_numeric_metrics_are_refused_not_raised(tmp_path: Path, bad) -> None:
    """Non-numeric metrics are refused as non-finite without raising."""
    cycle = _load(CYCLE, "biafra_cycle")
    for args in ((bad, 0.5), (0.5, bad)):
        r = cycle.dry_cycle("inner", "harden", *args, tmp_path / str(id(args)))
        assert r["ok"] is False and r["reason"] == "non-finite-metric"
        assert r["launched"] is False


def test_6_a_digest_with_a_trailing_newline_is_refused(sc) -> None:
    """A digest with a trailing newline fails trace and card validation."""
    assert sc.validate_trace_entry(_entry(evaluator_digest=DIGEST + "\n"))
    assert sc.validate_mechanism_card(_card(evaluator_digest=DIGEST + "\n"))


def test_6_an_empty_verifier_set_has_no_digest(sc, tmp_path: Path) -> None:
    """An empty verifier set or a directory raises ValueError."""
    with pytest.raises(ValueError):
        sc.evaluator_digest([])
    with pytest.raises(ValueError):
        sc.evaluator_digest([tmp_path])  # a directory is not a verifier file


def test_7_reverted_and_delta_must_agree(sc) -> None:
    """A card's reverted flag must match the sign of its delta."""
    assert any("reverted" in e for e in sc.validate_mechanism_card(_card(reverted=True, delta=-0.5)))
    assert any("reverted" in e for e in sc.validate_mechanism_card(_card(reverted=False, delta=0.5)))
    assert sc.validate_mechanism_card(_card(reverted=True, delta=0.5)) == []
    assert sc.validate_mechanism_card(_card(reverted=False, delta=-0.5)) == []


def test_7_graduated_cannot_be_a_reverted_card(sc) -> None:
    """A graduated card that is marked reverted is refused."""
    errors = sc.validate_mechanism_card(_card(status="graduated", reverted=True, delta=1.5))
    assert any("graduated" in e for e in errors)


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
def test_7_reviewed_and_graduated_need_a_real_dry_run(sc, status: str) -> None:
    """Reviewed and graduated cards with an empty receipt are refused."""
    assert any("dry_run_receipt" in e for e in sc.validate_mechanism_card(_card(status=status, dry_run_receipt={})))


def test_8_unknown_card_fields_are_refused(sc) -> None:
    """A card with an unlisted field is refused as unknown."""
    errors = sc.validate_mechanism_card(_card(targets=["oramasys/phylax/admission.py"]))
    assert any("unknown" in e for e in errors)


def test_8_the_schema_matches_the_allowlist_and_the_soul_is_honest(sc) -> None:
    """The schema fields match CARD_FIELDS and the soul text is accurate."""
    schema = json.loads((ROOT / "docs/v2/references/biafra/mechanism-card.schema.json").read_text())
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(sc.CARD_FIELDS)
    soul = (ROOT / "bin/agents/metaresearch-outer/SOUL.md").read_text()
    assert "owner_slices" in soul and "touches Phylax, Telos or Agate policy" not in soul


# --- CodeRabbit comment on seat_contracts.py line 30 (real review, PR 519): huge integers -----


@pytest.mark.parametrize("huge", [10**400, -10**400, 2**1024])
def test_huge_integers_are_refused_not_raised(sc, huge: int) -> None:
    """Integers too large for a float are refused as metrics without raising."""
    assert sc.is_finite_number(huge) is False
    assert any("delta" in e for e in sc.validate_mechanism_card(_card(delta=huge)))
    assert any("metric_before" in e for e in sc.validate_trace_entry(_entry(metric_before=huge)))
    assert any("metric_after" in e for e in sc.validate_trace_entry(_entry(metric_after=huge)))


def test_stall_report_counts_a_huge_metric_as_invalid_not_a_crash(sc) -> None:
    """A huge metric counts as invalid in the stall report."""
    report = sc.stall_report([_entry(metric_after=10**400)] * 3, window=3)
    assert report["invalid"] == 3 and report["stalled"] is False


def test_the_cycle_refuses_a_huge_metric(tmp_path: Path) -> None:
    """A dry cycle refuses a huge metric as non-finite without launching."""
    cycle = _load(CYCLE, "biafra_cycle")
    r = cycle.dry_cycle("inner", "harden", 10**400, 0.5, tmp_path)
    assert r["ok"] is False and r["reason"] == "non-finite-metric" and r["launched"] is False


def test_integer_measurements_preserve_double_precision(sc: ModuleType) -> None:
    """Integers outside the exact double range are refused without rejecting finite floats."""
    for value in (2**53, -(2**53), 10**15, -3, 0.25, 1.7976931348623157e308):
        assert sc.is_finite_number(value)
    for value in (2**53 + 1, -(2**53 + 1), 10**308, 10**400, True, float("nan"), float("inf")):
        assert not sc.is_finite_number(value)
    assert any("delta" in e for e in sc.validate_mechanism_card(_card(delta=2**53 + 1)))
    assert any("metric_before" in e for e in sc.validate_trace_entry(_entry(metric_before=2**53 + 1)))


def test_default_stall_window_uses_three_valid_reverts(sc: ModuleType) -> None:
    """The default stall threshold retains three consecutive valid reverts."""
    assert sc.STALL_WINDOW == 3
    reverts = [_entry(attempt_id=str(i), decision="revert", metric_after=0.9) for i in range(3)]
    assert not sc.stall_report(reverts[:2])["stalled"]
    assert sc.stall_report(reverts)["stalled"]
    assert sc.stall_report(reverts)["window"] == sc.STALL_WINDOW


@pytest.mark.parametrize("field", ["inner_metric", "held_out_metric"])
def test_card_metrics_must_be_declared(sc: ModuleType, field: str) -> None:
    """Both card metric fields reject undeclared names with a field-specific error."""
    assert not sc.validate_mechanism_card(_card())
    assert any(field in e for e in sc.validate_mechanism_card(_card(**{field: "invented_metric"})))


def test_trace_metrics_must_be_declared(sc: ModuleType) -> None:
    """Trace validation accepts declared names and rejects unknown or non-string values."""
    assert not sc.validate_trace_entry(_entry())
    for value in ("invented_metric", [], None):
        assert not sc.is_declared_metric_name(value)
        assert any("metric_name" in e for e in sc.validate_trace_entry(_entry(metric_name=value)))
    for value in ("metric", "val_bpb", "val_bpb_heldout", "held_out_class_bc_comment_cases",
                  "card_validity_and_grounding_failures", "failed_observed_defect_cases",
                  "failed_prelaunch_cases", "failed_reviewer_cases", "failed_verified_defect_cases",
                  "review_format_violations"):
        assert sc.is_declared_metric_name(value)
        assert not sc.validate_trace_entry(_entry(metric_name=value))


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
    """Sentences and malformed strings in owner_slices are refused."""
    errors = sc.validate_mechanism_card(_card(owner_slices=owners))
    assert any("owner_slices" in e for e in errors), owners


@pytest.mark.parametrize(
    "owners",
    [["kungfu"], ["orama-system"], ["perpetua-tools"], ["anamnesis", "alexandria"],
     ["diazMelgarejo/orama-system"], ["perpetua-core"], ["a.b_c-d"], ["a" * 64]],
)
def test_ordinary_repository_names_are_accepted(sc, owners) -> None:
    """Ordinary repository identifiers pass the owner check."""
    assert sc.validate_mechanism_card(_card(owner_slices=owners)) == []


def test_a_fixed_wall_name_reports_e_owner_even_when_it_is_not_identifier_shaped(sc) -> None:
    """Disguised fixed-wall names still report E_OWNER."""
    for name in ("Ｐhylax", "ph​ylax", "Рhylax", "Phýlax", "agate/fit", "xtelosx"):
        errors = sc.validate_mechanism_card(_card(owner_slices=[name]))
        assert any("E_OWNER" in e for e in errors), name


def test_owner_errors_never_raises(sc) -> None:
    """The owner check returns a list for every kind of bad input."""
    for bad in (None, 5, "kungfu", [], [None], [5], [["x"]], {"a": 1}):
        assert isinstance(sc._owner_errors(bad), list)


# --- turn 3: degenerate identifiers and the blank-entry message (defects reported by the outer seat,
# --- reproduced by the reviewer) ------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["a.", "a/", "a//b", "a/../b", "a/./b", "a/.", "a/.hidden", "a/b/", "a/b."],
)
def test_degenerate_identifiers_are_refused(sc, name: str) -> None:
    """Identifiers with empty, dot or trailing-separator parts are refused."""
    errors = sc.validate_mechanism_card(_card(owner_slices=[name]))
    assert any("repository identifiers" in e for e in errors), name


@pytest.mark.parametrize("name", ["a", "1", "org/repo.name", "a.b.c", "x-y_z", "a/b/c"])
def test_short_and_dotted_but_valid_identifiers_are_accepted(sc, name: str) -> None:
    """Short and dotted identifiers that are well formed are accepted."""
    assert sc.validate_mechanism_card(_card(owner_slices=[name])) == []


@pytest.mark.parametrize("owners", [["", "orama-system"], ["   "], [" "]])
def test_a_blank_entry_is_not_blamed_on_the_list(sc, owners) -> None:
    """A blank entry gets an entries message, not a non-empty-list message."""
    msg = " ".join(sc._owner_errors(owners))
    assert msg and "non-empty list" not in msg and "entries" in msg


@pytest.mark.parametrize("owners", [[], "kungfu", None])
def test_an_empty_or_missing_list_is_still_blamed_on_the_list(sc, owners) -> None:
    """An empty, string or missing list is blamed as a non-empty-list failure."""
    assert "non-empty list" in " ".join(sc._owner_errors(owners))


def test_the_identifier_error_names_the_entry_but_stays_bounded(sc) -> None:
    """The identifier error names the entry yet stays under 400 characters."""
    assert "a//b" in " ".join(sc._owner_errors(["a//b"]))
    huge = "x/" * 3000
    msg = " ".join(sc._owner_errors([huge, huge]))
    assert len(msg) < 400, len(msg)


@pytest.mark.parametrize("bad", [[123], [None], [True], [b"kungfu"], [["kungfu"]]])
def test_non_string_entries_are_refused_without_raising(sc, bad) -> None:
    """Non-string owner entries produce errors without raising."""
    assert sc._owner_errors(bad)


# --- G3: evaluator pin and receipt binding (doc 76 section 4) ---


def _promoted(status: str = "reviewed", **over):
    """A card for `status` whose receipt is a real dry-cycle result for that very card."""
    card = _card(status=status)
    trace = _entry(attempt_id="o-1", seat="outer", metric_before=0.26, metric_after=0.19)
    card["delta"] = round(0.19 - 0.26, 10)  # the card reports the same change its receipt measured
    card["dry_run_receipt"] = {
        "ok": True, "retries": 0, "launched": False, "trace": trace,
        "card_checked": True, "card_id": f"{card['mechanism_id']}@{card['revision']}",
    }
    card["dry_run_receipt"]["card_fingerprint"] = _load(CONTRACTS, "seat_contracts").card_fingerprint(card)
    card.update(over)
    return card


def test_g3_a_receipt_bound_to_its_card_and_pin_is_accepted(sc) -> None:
    """A receipt bound to its card, with a matching pin, validates cleanly."""
    assert sc.validate_mechanism_card(_promoted("reviewed")) == []
    assert sc.validate_mechanism_card(_promoted("graduated"), pinned_digest=DIGEST) == []


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
def test_g3_case1_a_receipt_without_a_trace_is_refused(sc, status: str) -> None:
    """A promoted card whose receipt lacks a trace is refused."""
    card = _promoted(status)
    del card["dry_run_receipt"]["trace"]
    errors = sc.validate_mechanism_card(card, pinned_digest=DIGEST)
    assert any("trace" in e for e in errors)


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
def test_g3_case1b_a_receipt_with_an_invalid_trace_is_refused(sc, status: str) -> None:
    """A promoted card whose receipt trace is invalid is refused."""
    card = _promoted(status)
    card["dry_run_receipt"]["trace"]["decision"] = "revert"  # disagrees with the metrics
    assert any("trace" in e for e in sc.validate_mechanism_card(card, pinned_digest=DIGEST))


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
def test_g3_case2_a_receipt_trace_digest_that_differs_is_refused(sc, status: str) -> None:
    """A receipt trace digest that differs from the card's is refused."""
    card = _promoted(status)
    card["dry_run_receipt"]["trace"]["evaluator_digest"] = "c" * 64
    errors = sc.validate_mechanism_card(card, pinned_digest=DIGEST)
    assert any("evaluator_digest" in e and "trace" in e for e in errors)


def test_g3_case3_a_graduated_card_that_was_never_pinned_is_refused(sc) -> None:
    """A graduated card validated without a pinned digest is refused."""
    errors = sc.validate_mechanism_card(_promoted("graduated"))
    assert any("pinned_digest" in e for e in errors)


def test_g3_a_reviewed_card_does_not_need_a_pin_but_a_given_pin_must_match(sc) -> None:
    """A reviewed card needs no pin, but a supplied pin must match."""
    assert sc.validate_mechanism_card(_promoted("reviewed")) == []
    errors = sc.validate_mechanism_card(_promoted("reviewed"), pinned_digest="c" * 64)
    assert any("pinned_digest" in e for e in errors)
    assert any("pinned_digest" in e for e in sc.validate_mechanism_card(_card(), pinned_digest="c" * 64))
    assert sc.validate_mechanism_card(_card(), pinned_digest=DIGEST) == []


def test_g3_a_candidate_needs_no_trace(sc) -> None:
    """A candidate card validates without any receipt trace."""
    assert sc.validate_mechanism_card(_card()) == []


@pytest.fixture()
def verifier(tmp_path: Path) -> Path:
    """Write a small verifier file under tmp_path and return its path."""
    path = tmp_path / "verifier.py"
    path.write_text("print('fixed evaluator')\n")
    return path


def test_g3_pin_evaluator_writes_the_digest_and_what_it_covers(sc, tmp_path: Path, verifier: Path) -> None:
    """pin_evaluator writes the digest and covered file names, and read_pin returns it."""
    pin = tmp_path / "run" / "evaluator.pin.json"
    digest = sc.pin_evaluator(pin, [verifier])
    assert digest == sc.evaluator_digest([verifier])
    assert json.loads(pin.read_text()) == {"version": 1, "evaluator_digest": digest, "covers": ["verifier.py"]}
    assert sc.read_pin(pin) == digest


def test_g3_pin_evaluator_is_idempotent_and_refuses_a_changed_evaluator(sc, tmp_path: Path, verifier: Path) -> None:
    """Re-pinning an unchanged evaluator is a no-op; an edited one raises."""
    pin = tmp_path / "evaluator.pin.json"
    first = sc.pin_evaluator(pin, [verifier])
    assert sc.pin_evaluator(pin, [verifier]) == first
    verifier.write_text("print('edited')\n")
    with pytest.raises(ValueError, match="evaluator changed"):
        sc.pin_evaluator(pin, [verifier])
    assert sc.read_pin(pin) == first  # the pin is never rewritten


def test_g3_pin_evaluator_refuses_a_different_covered_file_set(sc, tmp_path: Path, verifier: Path) -> None:
    """Pinning a different set of covered files raises ValueError."""
    pin = tmp_path / "evaluator.pin.json"
    sc.pin_evaluator(pin, [verifier])
    other = tmp_path / "other.py"
    other.write_text("x = 1\n")
    with pytest.raises(ValueError, match="evaluator changed"):
        sc.pin_evaluator(pin, [verifier, other])


def test_g3_pin_evaluator_refuses_a_malformed_existing_pin(sc, tmp_path: Path, verifier: Path) -> None:
    """An existing pin file that is not valid JSON makes pin_evaluator raise."""
    pin = tmp_path / "evaluator.pin.json"
    pin.write_text("not json")
    with pytest.raises(ValueError):
        sc.pin_evaluator(pin, [verifier])


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "[]",
        '{"version": 2, "evaluator_digest": "%s", "covers": ["a.py"]}' % DIGEST,
        '{"version": 1, "evaluator_digest": "%s", "covers": []}' % DIGEST,
        '{"version": 1, "evaluator_digest": "%s", "covers": [""]}' % DIGEST,
        '{"version": 1, "evaluator_digest": "short", "covers": ["a.py"]}',
        '{"version": 1, "evaluator_digest": "%s\\n", "covers": ["a.py"]}' % DIGEST,
        '{"version": 1, "evaluator_digest": "%s", "covers": ["a.py"], "extra": 1}' % DIGEST,
    ],
)
def test_g3_read_pin_refuses_any_defect(sc, tmp_path: Path, body: str) -> None:
    """read_pin raises ValueError for each malformed pin body."""
    pin = tmp_path / "evaluator.pin.json"
    pin.write_text(body)
    with pytest.raises(ValueError):
        sc.read_pin(pin)


def test_g3_read_pin_refuses_a_missing_file(sc, tmp_path: Path) -> None:
    """read_pin raises ValueError when the pin file is absent."""
    with pytest.raises(ValueError):
        sc.read_pin(tmp_path / "absent.json")


# --- G9: no card, no promotion ---


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
@pytest.mark.parametrize("flag", [False, None, "yes", 1])
def test_g9_a_receipt_that_did_not_check_the_card_is_refused(sc, status: str, flag) -> None:
    """A receipt without card_checked set to True is refused."""
    card = _promoted(status)
    card["dry_run_receipt"]["card_checked"] = flag
    assert any("card_checked" in e for e in sc.validate_mechanism_card(card, pinned_digest=DIGEST))
    del card["dry_run_receipt"]["card_checked"]
    assert any("card_checked" in e for e in sc.validate_mechanism_card(card, pinned_digest=DIGEST))


@pytest.mark.parametrize("status", ["reviewed", "graduated"])
@pytest.mark.parametrize("card_id", [None, "", "m-other@1", "m-bbbbbbbbbbbb@2", 7])
def test_g9_a_receipt_for_another_card_is_refused(sc, status: str, card_id) -> None:
    """A receipt whose card_id is not this card's id is refused."""
    card = _promoted(status)
    card["dry_run_receipt"]["card_id"] = card_id
    assert any("card_id" in e for e in sc.validate_mechanism_card(card, pinned_digest=DIGEST))


def test_g9_card_id_is_mechanism_id_at_revision(sc) -> None:
    """card_id returns the mechanism id joined to the revision with an at sign."""
    assert sc.card_id(_card(mechanism_id="m-x", revision=3)) == "m-x@3"


def test_g9_a_candidate_needs_no_checked_receipt(sc) -> None:
    """A candidate card validates with an empty receipt."""
    assert sc.validate_mechanism_card(_card(dry_run_receipt={})) == []


def test_g3_g9_the_schema_types_the_receipt_fields_and_stays_shape_only() -> None:
    """The schema types the receipt fields and accepts shape-only fixtures."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "docs/v2/references/biafra/mechanism-card.schema.json").read_text())
    receipt = schema["properties"]["dry_run_receipt"]["properties"]
    assert {"ok", "retries", "launched", "trace", "card_checked", "card_id"} <= set(receipt)
    root = ROOT / "tests" / "fixtures" / "mechanism_card"
    validator = jsonschema.Draft202012Validator(schema)
    shape_only = [
        "valid-reviewed.json", "valid-graduated.json",
        # Semantic refusals the Python validator owns: the schema alone accepts their shape.
        "invalid-graduated-receipt-without-trace.json", "invalid-receipt-trace-digest-differs.json",
        "invalid-reviewed-receipt-did-not-check-the-card.json", "invalid-reviewed-receipt-names-another-card.json",
    ]
    for name in shape_only:
        assert not list(validator.iter_errors(json.loads((root / name).read_text()))), name
    bad = json.loads((root / "valid-reviewed.json").read_text())
    bad["dry_run_receipt"]["card_checked"] = "yes"
    assert list(validator.iter_errors(bad))


def test_g3_g9_each_new_invalid_fixture_is_refused_for_its_own_reason(sc) -> None:
    """Each new invalid fixture fails with an error naming its own cause."""
    root = ROOT / "tests" / "fixtures" / "mechanism_card"
    expect = {
        "invalid-graduated-receipt-without-trace.json": "trace",
        "invalid-receipt-trace-digest-differs.json": "trace.evaluator_digest",
        "invalid-reviewed-receipt-did-not-check-the-card.json": "card_checked",
        "invalid-reviewed-receipt-names-another-card.json": "card_id",
    }
    for name, needle in expect.items():
        card = json.loads((root / name).read_text())
        errors = sc.validate_mechanism_card(card, pinned_digest=card["evaluator_digest"])
        assert errors and all(needle in e for e in errors), (name, errors)


def test_g3_a_receipt_for_the_same_id_cannot_promote_a_card_with_another_delta(sc) -> None:
    """A receipt for X@1 attached to another card that reuses X@1 with a different delta is refused."""
    card = _promoted("reviewed")
    assert sc.validate_mechanism_card(card) == []
    other = {**card, "delta": -0.02}  # same id and revision, so card_id still matches
    assert any("delta" in e for e in sc.validate_mechanism_card(other))
    assert any("fingerprint" in e for e in sc.validate_mechanism_card({**card, "delta": card["delta"] + 1e-12}))


def test_g3_concurrent_pins_of_one_path_never_hit_a_missing_temp_file(sc, tmp_path: Path, verifier: Path) -> None:
    """Threads pinning one path, with different verifier sets, end with one winner and no stray error."""
    extra = tmp_path / "extra.py"
    extra.write_text("x = 1\n")
    for round_number in range(40):
        pin = tmp_path / f"round{round_number}" / "evaluator.pin.json"
        barrier = threading.Barrier(4)
        outcomes: list = []

        def pin_it(paths) -> None:
            """Pin once, recording the digest or the exception."""
            barrier.wait()
            try:
                outcomes.append(sc.pin_evaluator(pin, paths))
            except BaseException as exc:  # recorded and asserted on below
                outcomes.append(exc)

        sets = [[verifier], [verifier, extra], [verifier], [verifier, extra]]
        threads = [threading.Thread(target=pin_it, args=(paths,)) for paths in sets]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        errors = [o for o in outcomes if isinstance(o, BaseException)]
        assert all(isinstance(e, ValueError) and "evaluator changed" in str(e) for e in errors), errors
        winner = sc.read_pin(pin)
        assert all(o == winner for o in outcomes if not isinstance(o, BaseException))
        assert len(outcomes) == 4
        assert [f.name for f in pin.parent.iterdir()] == [pin.name]  # no temp file is left behind

@pytest.mark.parametrize("field,value", [
    ("hypothesis", "changed"), ("owner_slices", ["other"]),
    ("inner_metric", "metric"), ("held_out_metric", "metric"),
    ("evidence_ids", ["different"]), ("delta", -0.069999999999),
])
def test_receipt_fingerprint_rejects_changed_content(sc, field, value) -> None:
    """Every checked content change invalidates a previously issued receipt."""
    card = _promoted()
    card[field] = value
    assert any("fingerprint" in error for error in sc.validate_mechanism_card(card))


def test_old_receipt_fails_closed_and_lifecycle_transition_preserves_binding(sc) -> None:
    """Unbound receipts must be rerun; changing status alone preserves a bound receipt."""
    card = _promoted()
    assert sc.validate_mechanism_card({**card, "status": "graduated"}, DIGEST) == []
    del card["dry_run_receipt"]["card_fingerprint"]
    assert any("fingerprint" in error for error in sc.validate_mechanism_card(card))


def test_receipt_decision_must_agree_despite_delta_tolerance(sc) -> None:
    """A zero-change revert cannot promote a tiny negative delta as an improvement."""
    card = _promoted()
    card["delta"] = -5e-10
    card["dry_run_receipt"]["trace"].update(metric_before=0.2, metric_after=0.2, decision="revert")
    card["dry_run_receipt"]["card_fingerprint"] = sc.card_fingerprint(card)
    assert any("decision" in error for error in sc.validate_mechanism_card(card))


@pytest.mark.parametrize("wrap", [dict, MappingProxyType])
def test_dry_cycle_requires_run_digest_and_independent_graduation_pin(tmp_path: Path, wrap) -> None:
    """A run digest cannot itself stand in for a graduation pin."""
    cycle = _load(CYCLE, "biafra_cycle")
    candidate = wrap(_card())
    bad = cycle.dry_cycle("outer", "harden", .26, .19, tmp_path, evaluator_digest="c" * 64, mechanism_card=candidate)
    assert bad["reason"] == "invalid-card"
    graduated = wrap(_promoted("graduated"))
    bad = cycle.dry_cycle("outer", "harden", .26, .19, tmp_path, evaluator_digest=DIGEST, mechanism_card=graduated)
    assert bad["reason"] == "invalid-card"
    good = cycle.dry_cycle("outer", "harden", .26, .19, tmp_path, evaluator_digest=DIGEST, mechanism_card=graduated, pinned_digest=DIGEST)
    assert good["ok"] and good["card_fingerprint"]

@pytest.mark.parametrize("value", [object(), float("nan"), ("coerced",), {1: "coerced"}])
def test_dry_cycle_refuses_non_json_card_content_before_attempt(tmp_path: Path, sc, value) -> None:
    """Candidate content must serialize without dropping or coercing nested values."""
    card = _card(scope_record={"authorizes": "nothing", "extra": value})
    assert any("canonicalizable" in error for error in sc.validate_mechanism_card(card))
    cycle = _load(CYCLE, "biafra_cycle")
    result = cycle.dry_cycle("outer", "harden", .26, .19, tmp_path, evaluator_digest=DIGEST, mechanism_card=card)
    assert result["reason"] == "invalid-card"
    assert not list(tmp_path.glob("*.once"))
