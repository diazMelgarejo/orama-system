from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOTHER = ROOT / "bin" / "orama-system" / "SKILL.md"
METHOD = ROOT / "bin" / "orama-system" / "skills" / "oramasys-method" / "SKILL.md"
CIDF = ROOT / "bin" / "orama-system" / "cidf" / "SKILL.md"
M3 = ROOT / "bin" / "orama-system" / "references" / "collaborative-reasoning-safety.md"
M6 = ROOT / "bin" / "orama-system" / "references" / "communication-guidelines.md"
MASTERY = ROOT / "docs" / "v2" / "references" / "ORAMASYS-MASTERY-v3.md"
WRAPPER = ROOT / ".claude" / "skills" / "agent-methodology" / "SKILL.md"
CANONICAL_METHOD = ROOT / "bin" / "orama-system" / "skills" / "agent-methodology" / "SKILL.md"
LESSONS = ROOT / "docs" / "LESSONS.md"

STAGES = (
    "Context Immersion",
    "Visionary Architecture",
    "Ruthless Refinement",
    "Masterful Execution",
    "Crystallize",
)


def _text(path: Path) -> str:
    assert path.exists(), f"missing canonical mastery artifact: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_p0_agent_methodology_is_thin_wrapper_to_real_canonical_skill():
    wrapper = _text(WRAPPER)
    assert "THIN-WRAPPER" in wrapper
    assert "canonical" in wrapper.lower()
    assert CANONICAL_METHOD.exists()
    # The discovery wrapper must not carry a second active five-stage implementation.
    assert sum(stage in wrapper for stage in STAGES) <= 1


def test_mother_skill_materializes_m1_m2_m4_and_points_to_m3_m6_mastery():
    mother = _text(MOTHER)
    assert "## Pre-Flight: Spec Contract" in mother
    assert "## Amplifier Objective Tree" in mother
    assert "**Output shape**" in mother
    for section in (
        "ASSUMPTIONS",
        "ARCHITECTURE / PLAN",
        "ARTIFACT",
        "TEST & VERIFICATION",
        "RISKS + MITIGATIONS",
        "NEXT ACTIONS",
    ):
        assert section in mother
    assert "references/collaborative-reasoning-safety.md" in mother
    assert "references/communication-guidelines.md" in mother
    assert "docs/v2/references/ORAMASYS-MASTERY-v3.md" in mother


def test_m3_is_single_runtime_safety_reference_with_human_execution_boundary():
    m3 = _text(M3)
    for marker in (
        "Builder",
        "Critic",
        "Adversary",
        "Judge",
        "strongest argument against this conclusion",
        "Confidence",
        "Uncertainty",
        "Consensus",
        "Disagreement",
        "Anti-Groupthink Rule",
        "Human Approval Boundary",
        "Advisory vs. Execution Boundary",
    ):
        assert marker in m3


def test_m6_preserves_forward_runtime_writing_contract():
    m6 = _text(M6)
    for marker in (
        "Tell it straight",
        "Language to Avoid",
        "Document Type Guidance",
        "Em dashes",
        "Semicolons",
        "Emojis",
        "Runtime guidelines going forward",
        "Not retroactive",
    ):
        assert marker in m6


def test_m5_uses_existing_lessons_architecture_instead_of_copying_it():
    mother = _text(MOTHER)
    assert LESSONS.exists()
    assert "scripts/capture_lesson.py" in mother
    assert "templates/lessons-log.md" in mother


def test_oramasys_method_and_cidf_extend_without_redefining_the_spine():
    method = _text(METHOD)
    cidf = _text(CIDF)
    canonical = _text(CANONICAL_METHOD)
    for stage in STAGES:
        assert stage in method
        assert stage in canonical
    assert "mother skill" in method.lower()
    assert "Integrative Editing Doctrine" in cidf
    assert "Target Verification" in cidf
    assert "synthesize; never amputate" in cidf


def test_human_mastery_reference_remains_present_as_unified_reference():
    mastery = _text(MASTERY)
    assert "# ORAMASYS — Unified Methodology" in mastery
    for marker in ("M1: Spec Contract", "M2: The Amplifier Objective Tree", "M3: Collaborative Reasoning Safety", "M4: Output Discipline", "M5: Lessons Architecture", "M6: Communication Guidelines"):
        assert marker in mastery
