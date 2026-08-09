from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
MOTHER = ROOT / "bin/orama-system/SKILL.md"
M3 = ROOT / "bin/orama-system/references/collaborative-reasoning-safety.md"
M6 = ROOT / "bin/orama-system/references/communication-guidelines.md"
WRAPPER = ROOT / ".claude/skills/agent-methodology/SKILL.md"
MASTERY = ROOT / "docs/v2/references/ORAMASYS-MASTERY-v3.md"


def _text(path: Path) -> str:
    assert path.is_file(), f"missing canonical mastery artifact: {path}"
    return path.read_text(encoding="utf-8")


def test_p0_agent_methodology_is_thin_wrapper() -> None:
    text = _text(WRAPPER)
    assert "THIN-WRAPPER" in text
    assert "bin/orama-system/skills/agent-methodology/" in text
    assert "Stage 1" not in text and "Stage 5" not in text
    assert (ROOT / "bin/orama-system/skills/agent-methodology/SKILL.md").is_file()


def test_mother_skill_owns_compact_m1_m2_m4_and_points_to_m3_m6() -> None:
    text = _text(MOTHER)
    for marker in (
        "## Pre-Flight: Spec Contract",
        "## Amplifier Objective Tree",
        "**Output shape** -- every substantial deliverable contains six sections:",
        "references/collaborative-reasoning-safety.md",
        "communication-guidelines.md",
    ):
        assert marker in text, f"missing mastery ownership marker: {marker}"


def test_m3_semantic_safety_contract() -> None:
    text = _text(M3)
    for marker in (
        "Builder", "Critic", "Adversary", "Judge",
        "strongest argument against this conclusion",
        "Confidence", "Uncertainty", "Consensus", "Disagreement",
        "Anti-Groupthink Rule", "Adversarial Review", "Human Authority Boundary",
        "cannot self-approve", "Treat consensus as authorization",
    ):
        assert marker.lower() in text.lower(), f"M3 missing: {marker}"


def test_m6_semantic_communication_contract() -> None:
    text = _text(M6)
    for marker in (
        "Tell it straight", "Language to Avoid", "Em dashes", "Semicolons",
        "Emojis", "Document Type Guidance", "not retroactive",
    ):
        assert marker.lower() in text.lower(), f"M6 missing: {marker}"


def test_human_mastery_reference_remains_present() -> None:
    assert MASTERY.is_file()


def test_p3_scaffold_not_materialized() -> None:
    # P3 is explicitly excluded from this convergence pass. These are the
    # v2-only scaffold surfaces named by the implementation plan.
    forbidden = [
        ROOT / "core/frugality_router.py",
        ROOT / "skills/prompt-engineering/SKILL.md",
        ROOT / "skills/spec-contract/SKILL.md",
        ROOT / ".github/workflows/mastery-eval.yml",
    ]
    assert not any(path.exists() for path in forbidden)
