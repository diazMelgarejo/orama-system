"""The paired offline review reference stays tied to the registry, the seat contracts and its pointers.

The reference names two registry seats and says what `PREFERRED_PAID` still lists. Each of those is
checked against the real file, so a renamed seat or a changed model table fails here and the
reference is updated with it, instead of going stale.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "bin/orama-system/skills/metaresearcher/references/paired-offline-review.md"
SKILL = ROOT / "bin/orama-system/skills/metaresearcher/SKILL.md"
README = ROOT / "bin/agents/autoresearcher/README.md"
REGISTRY = ROOT / "bin/agents/REGISTRY.yml"


def _flat(text: str) -> str:
    """Collapse whitespace so a wrapped sentence can be matched."""
    return " ".join(text.split())


def _seat_contracts():
    spec = importlib.util.spec_from_file_location("seat_contracts_paired_review_doc", ROOT / "bin/agents/seat_contracts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reference_names_registry_seats_that_exist() -> None:
    """The outer and inner seat ids in the reference are real registry staging folders and seats."""
    rows = {r["staging_folder"]: r for r in yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["roles"]}
    text = REFERENCE.read_text(encoding="utf-8")
    for folder, seat in (("metaresearch-outer", "outer"), ("autoresearch-inner", "inner")):
        assert f"`{folder}` (`seat: {seat}`)" in text, folder
        assert rows[folder]["seat"] == seat
    assert rows["autoresearcher"]["seat"] == "inner-scout" and "`inner-scout`" in text, "Scout stays distinct"


def test_reference_states_the_durable_openai_pair_from_preferred_paid() -> None:
    """The durable pair in the reference equals PREFERRED_PAID, so a changed table forces a doc update."""
    paid = _seat_contracts().PREFERRED_PAID
    outer_model, outer_effort = paid[("outer", "openai")]
    inner_model, inner_effort = paid[("inner", "openai")]
    text = _flat(REFERENCE.read_text(encoding="utf-8"))
    assert f"**{outer_model} at {outer_effort}**" in text and f"**{inner_model} at {inner_effort}**" in text
    assert "subject to change whenever OpenAI updates its frontier models" in text


def test_reference_records_the_adoption_dates_and_api_ids() -> None:
    """The adoption record keeps both models' first public date and API ids."""
    text = REFERENCE.read_text(encoding="utf-8")
    for model, api_id in (("GPT-6.2 Astra", "gpt-6.2-astra"), ("GPT-6.2 Sol", "gpt-6.2-sol")):
        row = next(line for line in text.splitlines() if line.startswith(f"| {model} |"))
        assert f"`{api_id}`" in row and "2026-11-17" in row


def test_every_card_names_the_same_openai_models_as_preferred_paid() -> None:
    """The outer and inner model names in the seat cards, persona, skill and doc 76 match the table."""
    paid = _seat_contracts().PREFERRED_PAID
    outer, inner = paid[("outer", "openai")][0], paid[("inner", "openai")][0]
    places = {
        "bin/agents/metaresearch-outer/SOUL.md": outer,
        "bin/agents/personas/biafra.yaml": outer,
        "bin/orama-system/skills/metaresearcher/SKILL.md": outer,
        "bin/agents/autoresearcher/README.md": inner,
    }
    for rel, model in places.items():
        assert model in _flat((ROOT / rel).read_text(encoding="utf-8")), rel
    row = _flat((ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md").read_text(encoding="utf-8"))
    assert outer in row and inner in row


def test_pointers_to_the_reference_resolve() -> None:
    """The metaresearcher skill and the AutoResearcher README both point at the reference."""
    assert REFERENCE.is_file()
    assert "references/paired-offline-review.md" in SKILL.read_text(encoding="utf-8")
    assert "references/paired-offline-review.md" in _flat(README.read_text(encoding="utf-8"))


def test_reference_keeps_the_live_cycle_a_separate_decision() -> None:
    """The pattern must not arm anything: it names the gate and the arm as a separate decision."""
    text = _flat(REFERENCE.read_text(encoding="utf-8"))
    assert "separate decision" in text and "operator gate and the explicit arm" in text
