"""Each Perpetua-Tools Biafra lesson is stated, in so many words, in the canonical orama seat files.

A keyword search shows that words appear somewhere, not that a file states the rule. This table holds,
per lesson, the file that must carry the rule and the exact phrase that states it, found by opening the
file and reading the line. A rule that moves, is reworded or disappears fails here by lesson id.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = "bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md"
SKILL = "bin/orama-system/skills/metaresearcher/SKILL.md"
SOUL_OUTER = "bin/agents/metaresearch-outer/SOUL.md"
README = "bin/agents/autoresearcher/README.md"
PERSONA = "bin/agents/personas/biafra.yaml"
PLAN = "docs/v2/76-biafra-outer-seat-canonical-plan.md"

COVERAGE: tuple[tuple[str, str, str], ...] = (
    ("lesson_07034e53fd23", README, "Qu and Lu, arXiv:2603.23420"),
    ("lesson_07034e53fd23", README, "organizational meta-learning in Visser's sense"),
    ("lesson_07034e53fd23", SOUL_OUTER, "not deutero-learning and not gradient"),
    ("lesson_07034e53fd23", SOUL_OUTER, "revert when the metric rises"),
    ("lesson_d25737d43531", README, "bi-level stays the default and tri-level stays optional"),
    ("lesson_d25737d43531", PERSONA, "tri-level is optional and never self-starting"),
    ("lesson_e33b845660ca", README, "adds no bilevel runner, no tri-level runner, and no serving grant"),
    ("lesson_a3239545e594", SOUL_OUTER, "refuses a card whose `owner_slices` name Phylax, Telos or Agate"),
    ("lesson_a3239545e594", SKILL, "the operator names provider, budget, request limit and deadline first"),
    ("lesson_a3239545e594", README, "`metaresearcher=adopted-not-started`"),
    ("lesson_8846ef3fbb9a", "bin/agents/seat_contracts.py", "literal `paid_approved is True`"),
    ("lesson_8846ef3fbb9a", PLAN, "Aliases that break the effort rule and must not be used: `claude-ultra`"),
    ("lesson_1fa650cb3860", PLAN, "It does not prove that a model proposes a good search rule"),
    ("lesson_7a1b41995876", RUNBOOK, "Reproduce every claim against the code"),
    ("lesson_7a1b41995876", RUNBOOK, "Claims about code the seat was not shown are suspect"),
    ("lesson_e748c558ab73", RUNBOOK, "a reference answer scores 0"),
    ("lesson_e748c558ab73", RUNBOOK, "Compute every number in a prompt from the evaluator instead of typing it"),
    ("lesson_710b39a9542c", "bin/agents/spend_guard.py", "orama keeps no"),
    ("lesson_9bcf2ac7d3ce", PLAN, "launcher-output-bound-unsupported"),
)


def _flat(text: str) -> str:
    """Collapse whitespace so a wrapped sentence can be matched."""
    return " ".join(text.split())


@pytest.mark.parametrize(("lesson", "path", "phrase"), COVERAGE, ids=[f"{c[0]}:{c[2][:34]}" for c in COVERAGE])
def test_lesson_rule_is_stated_in_the_canonical_file(lesson: str, path: str, phrase: str) -> None:
    """The file that must carry the rule states it, so the lesson is covered and not merely mentioned."""
    text = _flat((ROOT / path).read_text(encoding="utf-8"))
    assert phrase in text, f"{lesson}: {path} no longer states: {phrase!r}"
