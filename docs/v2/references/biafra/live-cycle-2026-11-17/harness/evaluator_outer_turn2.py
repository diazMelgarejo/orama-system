"""Fixed evaluator for the outer seat's live turn: is her Mechanism Card valid and grounded?

metric = card validator errors + grounding failures          (lower is better)
Grounding: evidence_ids must be exactly the real ledger ids, the card digest must equal the inner
run's pinned digest, and a reviewed or graduated status is not allowed on a first candidate.
Neither seat may edit this file.
"""
from __future__ import annotations

import importlib.util
import os
import json
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("ORAMA_REPO", Path.cwd()))
SB = Path(__file__).resolve().parents[1]


def _sc():
    spec = importlib.util.spec_from_file_location("seat_contracts", REPO / "bin/agents/seat_contracts.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seat_contracts"] = mod
    spec.loader.exec_module(mod)
    return mod


def real_ledger_ids():
    path = SB / "turn2-ledger.jsonl"
    return [json.loads(line)["attempt_id"] for line in path.read_text().splitlines() if line.strip()]


def real_digest():
    return json.loads((SB / "turn2-ledger.jsonl").read_text().splitlines()[0])["evaluator_digest"]


def extract_card(answer: str):
    blocks = re.findall(r"```json\s*\n(.*?)```", answer, flags=re.S)
    if not blocks:
        return None
    try:
        return json.loads(blocks[0])
    except json.JSONDecodeError:
        return None


def score_card(card):
    sc = _sc()
    if card is None:
        return {"metric_after": float(len(sc.validate_mechanism_card({})) + 3), "detail": {"no_card": True}}
    errors = sc.validate_mechanism_card(card)
    grounding = []
    if card.get("evidence_ids") != real_ledger_ids():
        grounding.append("evidence_ids are not exactly the real ledger ids")
    if card.get("evaluator_digest") != real_digest():
        grounding.append("evaluator_digest is not the pinned digest of the inner run")
    if card.get("held_out_metric") != "none":
        grounding.append("held_out_metric must be 'none': no held-out metric exists yet")
    if card.get("inner_metric") != "failed_observed_defect_cases":
        grounding.append("inner_metric must be the metric the inner run actually used")
    if card.get("status") != "candidate":
        grounding.append("a first card must have status candidate")
    return {
        "metric_after": float(len(errors) + len(grounding)),
        "detail": {"validator_errors": errors, "grounding_failures": grounding, "card": card},
    }


def evaluate_answer(answer: str):
    return score_card(extract_card(answer))


def baseline():
    return score_card(None)["metric_after"]
