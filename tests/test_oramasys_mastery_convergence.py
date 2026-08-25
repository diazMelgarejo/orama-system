from pathlib import Path

ROOT = Path(__file__).parents[1]
MOTHER = ROOT / "bin/orama-system/SKILL.md"
MASTERY = ROOT / "docs/v2/references/ORAMASYS-MASTERY-v3.md"
M3 = ROOT / "bin/orama-system/references/collaborative-reasoning-safety.md"
M6 = ROOT / "bin/orama-system/references/communication-guidelines.md"
METHOD = ROOT / "bin/orama-system/skills/oramasys-method/SKILL.md"
CIDF = ROOT / "bin/orama-system/cidf/SKILL.md"
P0_WRAPPER = ROOT / ".claude/skills/agent-methodology/SKILL.md"
LESSONS = ROOT / "docs/LESSONS.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing canonical mastery artifact: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8-sig")


def test_p0_agent_methodology_is_thin_wrapper() -> None:
    text = _read(P0_WRAPPER)
    assert "THIN-WRAPPER" in text
    assert "../../../bin/orama-system/skills/agent-methodology/" in text
    assert len(text.splitlines()) <= 30


def test_m1_m2_m4_are_materialized_in_mother_skill() -> None:
    text = _read(MOTHER)
    assert "## Pre-Flight: Spec Contract" in text
    assert "## Amplifier Objective Tree" in text
    for label in (
        "ASSUMPTIONS",
        "ARCHITECTURE / PLAN",
        "ARTIFACT",
        "TEST & VERIFICATION",
        "RISKS + MITIGATIONS",
        "NEXT ACTIONS",
    ):
        assert label in text


def test_m3_has_one_canonical_reference_and_human_authority_boundary() -> None:
    mother = _read(MOTHER)
    text = _read(M3)
    assert "references/collaborative-reasoning-safety.md" in mother
    for contract in (
        "Builder",
        "Critic",
        "Adversary",
        "Judge",
        "strongest argument against",
        "Confidence",
        "Uncertainty",
        "Consensus",
        "Disagreement",
        "Anti-Groupthink",
        "Human Authority Boundary",
        "Advisory vs. Execution Boundary",
        "epistemic roles, not authorization principals",
        "Treat consensus as authorization",
        "HUMAN-IN-LOOP-ACCOUNTABILITY.md",
    ):
        assert contract.lower() in text.lower()


def test_m5_points_to_canonical_lessons_architecture() -> None:
    mother = _read(MOTHER)
    assert LESSONS.exists()
    assert "scripts/capture_lesson.py" in mother
    assert "PERPETUA_TOOLS_ROOT" in mother
    assert "templates/lessons-log.md" in mother


def test_m6_has_one_canonical_runtime_reference_and_pointer() -> None:
    mother = _read(MOTHER)
    text = _read(M6)
    assert "references/communication-guidelines.md" in mother
    for contract in (
        "Tell it straight",
        "AI tells",
        "Em dashes",
        "Semicolons",
        "Emojis",
        "Runtime guidelines going forward",
    ):
        assert contract.lower() in text.lower()


def test_oramasys_method_and_cidf_extend_the_spine() -> None:
    method = _read(METHOD)
    cidf = _read(CIDF)
    assert "mother skill" in method.lower()
    assert "Integrative Editing Doctrine" in cidf
    assert "Target Verification" in cidf
    assert "synthesize; never amputate" in cidf


def test_human_mastery_reference_remains_present() -> None:
    assert MASTERY.exists()
    assert "docs/v2/references/ORAMASYS-MASTERY-v3.md" in _read(MOTHER)


def test_p3_scaffold_remains_unmaterialized() -> None:
    forbidden = (
        ROOT / "core/frugality_router.py",
        ROOT / "skills/prompt-engineering/SKILL.md",
        ROOT / "skills/spec-contract/SKILL.md",
        ROOT / ".github/workflows/mastery-eval.yml",
    )
    assert not any(path.exists() for path in forbidden)
