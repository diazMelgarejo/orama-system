"""The AutoResearcher / Biafra pair run end to end, free: no model call, no gate, no network.

Scout and the inner seat produce trace entries. The outer seat (Biafra) reads them, detects a
stall, and proposes a Mechanism Card. The evaluator is a fixed file set the seats cannot edit.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_pair(workdir: Path) -> dict[str, Any]:
    """Run one full pair cycle in `workdir` and return a receipt. Reused by the test below."""
    sc = _load(ROOT / "bin/agents/seat_contracts.py", "seat_contracts")
    inner = _load(ROOT / "bin/agents/autoresearch-inner/program.py", "inner_program")
    outer = _load(ROOT / "bin/agents/metaresearch-outer/program.py", "outer_program")
    cycle = _load(ROOT / "bin/agents/biafra_cycle.py", "biafra_cycle")

    workdir.mkdir(parents=True, exist_ok=True)
    verifier = workdir / "verifier" / "check_metric.py"
    verifier.parent.mkdir()
    verifier.write_text("def score(x):\n    return x\n")
    digest = sc.evaluator_digest([verifier])

    # Inner seat: three attempts on one artifact, each worse than before (lower is better).
    inner_results = [
        inner.run(
            "harden", 0.20, after, workdir / f"inner-{n}", "train.py", digest,
            hypothesis=f"change {n}", metric_name="val_bpb",
        )
        for n, after in enumerate((0.24, 0.23, 0.26), start=1)
    ]
    # Scout reports one more attempt on its own seat.
    scout_trace = {
        "version": 1, "seat": "inner-scout", "attempt_id": "scout-1", "hypothesis": "plugin loop pass",
        "artifact": "train.py", "metric_name": "val_bpb", "metric_before": 0.20, "metric_after": 0.25,
        "decision": "revert", "evaluator_digest": digest,
    }
    ledger = [r["trace"] for r in inner_results] + [scout_trace]

    # Biafra: reads the ledger (read-only copy), detects the stall, proposes one search rule.
    ledger_file = workdir / "ledger.jsonl"
    ledger_file.write_text("\n".join(json.dumps(e) for e in ledger) + "\n")
    read_back = [json.loads(line) for line in ledger_file.read_text().splitlines()]
    stall = sc.stall_report(read_back, window=3)

    outer_result = outer.run(
        "harden", 0.26, 0.19, workdir / "outer", "search-rule", digest,
        hypothesis="repeat reverts mean the proposal rule is stale", metric_name="val_bpb",
    )
    card = {
        "version": 1,
        "mechanism_id": "m-" + digest[:12],
        "revision": 1,
        "parent": None,
        "hypothesis": "Three consecutive reverts on one artifact: change the proposal rule, not the artifact.",
        "evidence_ids": stall["entry_ids"],
        "inner_metric": "val_bpb",
        "held_out_metric": "val_bpb_heldout",
        "evaluator_digest": digest,
        "dry_run_receipt": {
            "ok": outer_result["ok"], "retries": outer_result["retries"], "launched": outer_result["launched"],
        },
        "delta": round(0.19 - 0.26, 10),
        "reverted": outer_result["decision"] == "revert",
        "scope_record": {"authorizes": "nothing"},
        "owner_slices": ["kungfu"],
        "status": "candidate",
    }
    # The outer seat may not touch a verifier path.
    protected = cycle.dry_cycle("outer", "harden", 0.3, 0.1, workdir / "protected", "tests/test_x.py", digest)
    return {
        "digest": digest,
        "digest_after": sc.evaluator_digest([verifier]),
        "inner_results": inner_results,
        "ledger": ledger,
        "stall": stall,
        "outer_result": outer_result,
        "card": card,
        "card_errors": sc.validate_mechanism_card(card),
        "protected": protected,
        "plan_free": sc.plan_turn("outer", platform="anthropic", paid_approved=False),
    }


@pytest.fixture()
def receipt(tmp_path: Path) -> dict[str, Any]:
    return run_pair(tmp_path)


def test_inner_seat_records_distinct_valid_attempts(receipt) -> None:
    sc = _load(ROOT / "bin/agents/seat_contracts.py", "seat_contracts")
    assert all(r["ok"] and r["recorded"] for r in receipt["inner_results"])
    assert all(sc.validate_trace_entry(e) == [] for e in receipt["ledger"])
    ids = [e["attempt_id"] for e in receipt["ledger"]]
    assert len(set(ids)) == len(ids) == 4
    assert {e["seat"] for e in receipt["ledger"]} == {"inner", "inner-scout"}


def test_biafra_detects_the_stall_from_the_ledger(receipt) -> None:
    assert receipt["stall"]["stalled"] is True
    assert receipt["stall"]["invalid"] == 0
    assert len(receipt["stall"]["entry_ids"]) == 3


def test_biafra_proposes_a_valid_card_citing_the_stall(receipt) -> None:
    assert receipt["card_errors"] == []
    assert receipt["card"]["evidence_ids"] == receipt["stall"]["entry_ids"]
    assert receipt["card"]["reverted"] is False and receipt["card"]["delta"] < 0
    assert receipt["card"]["status"] == "candidate"


def test_the_evaluator_is_untouched_and_the_seats_cannot_edit_it(receipt) -> None:
    assert receipt["digest"] == receipt["digest_after"]
    assert receipt["protected"]["ok"] is False and receipt["protected"]["reason"] == "verifier-protected"


def test_the_pair_run_is_free_and_gated(receipt) -> None:
    for result in (*receipt["inner_results"], receipt["outer_result"]):
        assert result["launched"] is False and result["called_launcher"] is False
        assert result["calls_plugin"] is False and result["dispatches_gpu"] is False
        assert result["retries"] == 0
        assert result["gate"] == "" and result["armed"] == ""
    assert receipt["plan_free"]["tier"] == "default" and receipt["plan_free"]["effort"] == "high"
    assert receipt["plan_free"]["human_gated"] is False


def test_a_second_pair_cycle_in_the_same_directories_does_not_retry(tmp_path: Path) -> None:
    first = run_pair(tmp_path / "one")
    assert first["outer_result"]["ok"] is True
    cycle = _load(ROOT / "bin/agents/biafra_cycle.py", "biafra_cycle")
    again = cycle.dry_cycle("outer", "harden", 0.26, 0.19, tmp_path / "one" / "outer", "search-rule", first["digest"])
    assert again["ok"] is False and again["reason"] == "already-ran" and again["retries"] == 0


def test_the_saved_live_cycle_artifacts_are_valid() -> None:
    sc = _load(ROOT / "bin/agents/seat_contracts.py", "seat_contracts")
    base = ROOT / "docs/v2/references/biafra/live-cycle-2026-11-17"
    rows = [json.loads(line) for line in (base / "ledger.jsonl").read_text().splitlines() if line.strip()]
    assert [r["seat"] for r in rows] == ["inner", "outer"]
    assert all(sc.validate_trace_entry(r) == [] for r in rows)
    card = json.loads((base / "mechanism-card-candidate.json").read_text())
    # The card is kept verbatim. Its owner_slices is a sentence, the defect turn 1 exposed and turn 2
    # fixed, so the repaired validator now refuses exactly that and nothing else.
    errors = sc.validate_mechanism_card(card)
    assert len(errors) == 1 and "owner_slices must be repository identifiers" in errors[0]
    assert card["evidence_ids"] == [rows[0]["attempt_id"]] and card["status"] == "candidate"


def test_every_saved_ledger_row_is_valid_and_the_reverted_turn_is_recorded() -> None:
    sc = _load(ROOT / "bin/agents/seat_contracts.py", "seat_contracts")
    base = ROOT / "docs/v2/references/biafra/live-cycle-2026-11-17"
    seen = {}
    for path in sorted(base.glob("ledger*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert rows and all(sc.validate_trace_entry(r) == [] for r in rows), path.name
        seen[path.name] = [r["decision"] for r in rows]
    assert seen["ledger-turn-3-reverted.jsonl"] == ["revert"]
    assert seen["ledger-turn-3b.jsonl"] == ["keep"]
    ids = [json.loads(line)["attempt_id"] for p in base.glob("ledger*.jsonl") for line in p.read_text().splitlines()]
    assert len(ids) == len(set(ids))


def test_the_runbook_states_the_billing_basis_and_the_stop_rule() -> None:
    text = (ROOT / "bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md").read_text()
    assert "https://docs.coreweave.com/products/inference/serverless/usage-limits" in text
    assert "https://docs.coreweave.com/support/inference/articles/api-error-code-402-you-exceeded-your-cur" in text
    for needle in ("pay-as-you-go", "402", "429", "Billing page", "attest", "two causes", "max_retries"):
        assert needle in text, needle
    assert "free-tier W&B" not in text
    assert "a `402` means it was reached" not in text


def test_the_runbook_points_at_the_shared_guard_and_not_a_private_ledger() -> None:
    text = (ROOT / "bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md").read_text()
    for needle in (
        "90 dollars", "spend_guard", "PERPETUA_TOOLS_ROOT", "provider_limits verify", "attestation-required",
        "budget-exhausted", "the Billing page is the truth", "orchestrator/cost_guard.py",
    ):
        assert needle in text, needle
    for gone in ("spend_ledger", "budget_usd"):
        assert gone not in text, gone


def test_the_plan_states_both_402_causes_and_the_attestation_requirement() -> None:
    text = (ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md").read_text()
    assert "a `402` means the cap was reached" not in text
    for needle in ("two causes", "attest", "pay-as-you-go is inactive", "Perpetua-Tools", "provider_limits"):
        assert needle in text, needle


def test_the_evidence_ledgers_exist_and_are_not_gitignored() -> None:
    """The ledgers are versioned evidence. `*.jsonl` is ignored repo-wide, so they need an explicit allowlist."""
    base = ROOT / "docs/v2/references/biafra/live-cycle-2026-11-17"
    names = ["ledger.jsonl", "ledger-turn-2.jsonl", "ledger-turn-3-reverted.jsonl", "ledger-turn-3b.jsonl"]
    for name in names:
        assert (base / name).is_file(), f"missing evidence file {name}"
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(base / name)], cwd=ROOT, capture_output=True, check=False
        )
        assert ignored.returncode == 1, f"{name} is gitignored, so a clean checkout will not have it"
