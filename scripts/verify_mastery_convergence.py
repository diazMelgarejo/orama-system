#!/usr/bin/env python3
"""Verify ORAMASYS-MASTERY v3 is materialized in v1 through P2 only.

This is an ownership/semantic gate, not a phrase-count duplication test.
It deliberately leaves the v2/P3 scaffold out of scope.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOTHER = ROOT / "bin/orama-system/SKILL.md"
ROOT_SKILL = ROOT / "SKILL.md"
WRAPPER = ROOT / ".claude/skills/agent-methodology/SKILL.md"
M3 = ROOT / "bin/orama-system/references/collaborative-reasoning-safety.md"
M6 = ROOT / "bin/orama-system/references/communication-guidelines.md"
MAP = ROOT / "bin/orama-system/references/mastery-runtime-map.md"
MASTERY = ROOT / "docs/v2/references/ORAMASYS-MASTERY-v3.md"
LESSONS = ROOT / "docs/LESSONS.md"

P3_SENTINELS = (
    ROOT / "skills/prompt-engineering/SKILL.md",
    ROOT / "skills/spec-contract/SKILL.md",
    ROOT / "core/frugality_router.py",
    ROOT / ".github/workflows/mastery-eval.yml",
)


class ConvergenceError(RuntimeError):
    pass


def _read(path: Path) -> str:
    if not path.is_file():
        raise ConvergenceError(f"missing canonical file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8-sig")


def _require(text: str, needles: tuple[str, ...], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise ConvergenceError(f"{label} missing required contract(s): {missing}")


def verify() -> None:
    mother = _read(MOTHER)
    root_skill = _read(ROOT_SKILL)
    wrapper = _read(WRAPPER)
    m3 = _read(M3)
    m6 = _read(M6)
    runtime_map = _read(MAP)
    _read(MASTERY)
    _read(LESSONS)

    # P0 — discovery card stays a pointer, never a second methodology.
    _require(wrapper, ("THIN-WRAPPER", "bin/orama-system/skills/agent-methodology"), "P0 wrapper")
    if "### Stage 1" in wrapper or "### Stage 5" in wrapper:
        raise ConvergenceError("P0 wrapper contains a divergent staged methodology")

    # P1 — verify current semantic contracts rather than replaying historical prose.
    _require(
        mother,
        ("## Pre-Flight: Spec Contract", "ORAMASYS-MASTERY-v3.md § M1"),
        "M1 Spec Contract",
    )
    _require(
        mother,
        ("## Amplifier Objective Tree", "references/amplifier-principle.md"),
        "M2 Amplifier Objective Tree",
    )
    _require(
        mother,
        ("references/collaborative-reasoning-safety.md", "**Output shape**"),
        "M3/M4 mother pointers",
    )
    _require(
        mother,
        (
            "ASSUMPTIONS:",
            "ARCHITECTURE / PLAN:",
            "ARTIFACT:",
            "TEST & VERIFICATION:",
            "RISKS + MITIGATIONS:",
            "NEXT ACTIONS:",
        ),
        "M4 Output Discipline",
    )

    # M5 is an architecture, not copied lesson prose: the repo entrypoint owns
    # the session ledger, while the mother skill invokes the capture loop.
    _require(root_skill, ("docs/LESSONS.md",), "M5 root lesson ownership")
    _require(mother, ("scripts/capture_lesson.py", "templates/lessons-log.md"), "M5 mother lesson loop")

    # P2 — dedicated references remain the semantic source of truth.
    _require(
        m3,
        (
            "Builder",
            "Critic",
            "Adversary",
            "Judge",
            "strongest argument against",
            "Confidence:",
            "Uncertainty:",
            "Consensus:",
            "Disagreement:",
            "Anti-Groupthink",
        ),
        "M3 Collaborative Reasoning Safety",
    )
    _require(
        m6,
        (
            "Tell it straight",
            "Language to Avoid",
            "Em dashes",
            "Semicolons",
            "Emojis",
            "Not retroactive",
        ),
        "M6 Communication Guidelines",
    )

    _require(
        runtime_map,
        ("M1 Spec Contract", "M2 Amplifier", "M3 Collaborative", "M4 Output", "M5 Lessons", "M6 Communication"),
        "runtime ownership map",
    )

    created_p3 = [path.relative_to(ROOT) for path in P3_SENTINELS if path.exists()]
    if created_p3:
        raise ConvergenceError(f"P3 no-touch boundary violated: {created_p3}")


def main() -> int:
    try:
        verify()
    except ConvergenceError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("OK: ORAMASYS mastery v3 is materialized in v1 through P2; P3 untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
