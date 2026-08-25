#!/usr/bin/env python3
"""
capture_lesson.py
=================
The OramaSys lesson-capture frontend.

V1 delegates development lessons to Perpetua-Tools' tracked Agentic-Stack
memory.  The CLI surface is intentionally stable while v2 runtime persistence
is deferred to the future Anamnesis backend.

Usage:
    python capture_lesson.py
    python capture_lesson.py --pattern "Premature Optimization" --quick
    python capture_lesson.py --quick --pattern "Verification Skipped"
    python capture_lesson.py --review --pt-root /path/to/Perpetua-Tools
    python capture_lesson.py --backend legacy  # Explicit standalone compatibility

See docs/v2/56-anamnesis-runtime-memory-migration.md for the controller
contract, backend resolution, and v2 migration boundaries.
"""

import os
import sys
import argparse
import re
from pathlib import Path
from collections import Counter
from typing import Optional

from lesson_controller import (
    DeferredAnamnesisBackend,
    LegacyMarkdownBackend,
    LessonBackend,
    LessonBackendUnavailable,
    LessonPayload,
    PTAgentBackend,
    resolve_backend,
)

# ─── Colour output ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# ─── Common mistake categories (for quick selection) ─────────────────────────
CATEGORIES = [
    "Premature Optimization",
    "Insufficient Error Handling",
    "Visual Verification (trusted appearance over code)",
    "Missing Edge Case",
    "Incorrect Assumption About Requirements",
    "Over-Engineering (added complexity without justification)",
    "Under-Engineering (too simple for the problem)",
    "Skipped Planning Phase",
    "Test Coverage Gap",
    "API Contract Misunderstanding",
    "Naming Clarity Issue",
    "Context Window Mismanagement",
    "Subagent Delegation Failure",
    "Verification Skipped",
    "Custom",
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def find_lessons_file(
    start_dir: Path,
    *,
    configured_path: Path | None = None,
    home_dir: Path | None = None,
) -> Path | None:
    """Return an initialized legacy log, migrating an old task log if necessary.

    The absence of an old task log is not a request to create one.  The caller
    invokes this only for the explicit legacy backend, so normal PT and runtime
    selection remains read-only with respect to historical task directories.
    """
    if configured_path is not None:
        if configured_path.is_file():
            return configured_path
        raise LessonBackendUnavailable(
            "ORAMASYS_LESSON_E_LEGACY_PATH_UNAVAILABLE",
            f"Configured legacy lesson log does not exist: {configured_path}",
        )

    destination = (home_dir or Path.home()) / "tasks" / "lessons.md"
    if destination.is_file():
        return destination
    current = start_dir
    while True:
        candidate = current / "tasks" / "lessons.md"
        if candidate.is_file():
            if destination.exists():
                raise LessonBackendUnavailable(
                    "ORAMASYS_LESSON_E_LEGACY_MIGRATION_CONFLICT",
                    "Cannot migrate legacy tasks/lessons.md because the home-level "
                    f"destination already exists: {destination}",
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            candidate.replace(destination)
            return destination
        if current.parent == current:
            break
        current = current.parent
    return None


def prompt(label: str, hint: str = "", required: bool = True) -> str:
    """Interactive prompt with optional hint."""
    if hint:
        print(f"  {CYAN}Hint{RESET}: {hint}")
    while True:
        value = input(f"  {BLUE}{label}{RESET}: ").strip()
        if value or not required:
            return value
        print(f"  {YELLOW}(required — please enter a value){RESET}")


def select_category() -> str:
    """Interactive category selection."""
    print(f"\n  {BOLD}Select mistake category:{RESET}")
    for i, cat in enumerate(CATEGORIES, 1):
        print(f"  {BLUE}{i:2d}{RESET}. {cat}")
    while True:
        choice = input(f"\n  Enter number (1–{len(CATEGORIES)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(CATEGORIES):
                selected = CATEGORIES[idx]
                if selected == "Custom":
                    return prompt("Custom category name")
                return selected
        except ValueError:
            pass
        print(f"  {YELLOW}Invalid choice{RESET}")


def get_lesson_stats(lessons_path: Path) -> dict:
    """Parse lessons file and return statistics."""
    if not lessons_path.exists():
        return {"total": 0, "categories": Counter()}

    content = lessons_path.read_text(encoding="utf-8")
    entries = re.findall(r"^## \d{4}-\d{2}-\d{2} — (.+)$", content, re.MULTILINE)

    # Extract categories (simplified)
    cats = Counter()
    for entry in entries:
        for cat in CATEGORIES[:-1]:  # exclude "Custom"
            if cat.lower() in entry.lower():
                cats[cat] += 1
                break
        else:
            cats["Other / Custom"] += 1

    return {"total": len(entries), "categories": cats}


# ─── Main logic ──────────────────────────────────────────────────────────────

def capture_interactive(
    pattern: Optional[str], backend: LessonBackend, quick: bool = False
) -> None:
    """Walk the user through creating a lesson entry interactively."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  OramaSys Self-Improvement Loop — Capture Lesson{RESET}")
    print("  Backend: forward-compatible lesson controller")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Pattern / category
    if pattern:
        print(f"  {GREEN}Pattern{RESET}: {pattern}")
    else:
        pattern = select_category()

    if quick:
        rule = prompt(
            "Prevention rule",
            hint="Actionable rule that would prevent the recurrence.",
        )
        backend.capture(LessonPayload(
            pattern=pattern,
            what_went_wrong="Quick capture; expand during weekly crystallization.",
            root_cause="Quick capture; root cause pending evidence review.",
            prevention_rule=rule,
            verification_trigger="Review the weekly candidate before promotion.",
            applied_to="All similar tasks",
            good_example="Apply the prevention rule before the next similar task.",
            bad_example="Repeat the pattern without recording a prevention rule.",
        ))
        print(f"\n  {GREEN}✓ Lesson captured:{RESET} {pattern}")
        return

    # Gather the full structured frontend payload.
    print()
    what = prompt(
        "What went wrong",
        hint="Specific description of the mistake — what exactly happened?"
    )
    cause = prompt(
        "Root cause",
        hint="WHY did this happen? What was misunderstood or skipped?"
    )
    rule = prompt(
        "Prevention rule",
        hint="How to avoid this in future? Write as an actionable rule."
    )
    trigger = prompt(
        "Verification trigger",
        hint="What question to ask yourself BEFORE making this mistake again?"
    )
    scope = prompt(
        "Applied to (scenarios)",
        hint="Future scenarios where this lesson applies (comma-separated)",
        required=False
    ) or "All similar tasks"
    good = prompt(
        "Good example (✅)",
        hint="What SHOULD be done instead? One sentence is fine.",
        required=False
    ) or "(add example later)"
    bad = prompt(
        "Bad example (❌)",
        hint="What was done wrong? Mirror of the good example.",
        required=False
    ) or "(add example later)"

    backend.capture(LessonPayload(
        pattern=pattern,
        what_went_wrong=what,
        root_cause=cause,
        prevention_rule=rule,
        verification_trigger=trigger,
        applied_to=scope,
        good_example=good,
        bad_example=bad,
    ))

    print(f"\n  {GREEN}✓ Lesson captured:{RESET} {pattern}")
    print(f"  {GREEN}✓ Stored through:{RESET}  {backend.__class__.__name__}")


def review_lessons(lessons_path: Path) -> None:
    """Print all lessons for review."""
    if not lessons_path.exists():
        print(f"  {YELLOW}No lessons file found at {lessons_path}{RESET}")
        return

    content = lessons_path.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=## \d{4}-\d{2}-\d{2})", content)

    print(f"\n{BOLD}📚 Lessons Learned — {lessons_path}{RESET}")
    print(f"   {len([e for e in entries if e.strip().startswith('##')])} lesson(s) on record\n")

    for entry in entries:
        if entry.strip().startswith("##"):
            print(f"{BLUE}{entry[:200]}...{RESET}\n" if len(entry) > 200 else f"{entry}\n")


def show_stats(lessons_path: Path) -> None:
    """Show lesson statistics and trends."""
    stats = get_lesson_stats(lessons_path)
    print(f"\n{BOLD}📊 Self-Improvement Stats{RESET}")
    print(f"   Total lessons: {stats['total']}")
    if stats["categories"]:
        print(f"\n   By category:")
        for cat, count in stats["categories"].most_common():
            bar = "█" * count
            print(f"   {count:3d} {bar} {cat}")
    print()


def pt_memory_path(pt_root: Path) -> Path:
    return pt_root / ".agent" / "memory" / "semantic" / "LESSONS.md"


def review_pt_memory(pt_root: Path) -> None:
    path = pt_memory_path(pt_root)
    if not path.exists():
        print(f"  {YELLOW}No PT semantic lesson view found at {path}{RESET}")
        return
    print(f"\n{BOLD}📚 PT Agentic-Stack development memory — {path}{RESET}\n")
    print(path.read_text(encoding="utf-8"))


def show_pt_stats(pt_root: Path) -> None:
    path = pt_memory_path(pt_root)
    if not path.exists():
        print(f"  {YELLOW}No PT semantic lesson view found at {path}{RESET}")
        return
    content = path.read_text(encoding="utf-8")
    print(f"\n{BOLD}📊 PT Agentic-Stack development memory{RESET}")
    print(f"   Accepted lessons: {content.count('status=accepted')}")
    print(f"   Provisional lessons: {content.count('status=provisional')}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OramaSys lesson capture — stable frontend, configurable backend"
    )
    parser.add_argument("--pattern", help="Mistake pattern name (skips category selection)")
    parser.add_argument("--quick",   action="store_true", help="Minimal prompts (pattern + rule only)")
    parser.add_argument("--review",  action="store_true", help="Review existing lessons")
    parser.add_argument("--stats",   action="store_true", help="Show lesson statistics")
    parser.add_argument("--dir",     default=".",         help="Project directory")
    parser.add_argument("--mode", choices=("development", "runtime"), default="development",
                        help="Runtime requires provisioned Anamnesis.")
    parser.add_argument("--backend", choices=("auto", "pt-agent", "legacy", "anamnesis"),
                        default="auto", help="Backend controller selection.")
    parser.add_argument("--pt-root", default=os.environ.get("PERPETUA_TOOLS_ROOT"),
                        help="Perpetua-Tools root for tracked development memory.")
    parser.add_argument(
        "--legacy-path",
        default=os.environ.get("ORAMASYS_LEGACY_LESSONS_PATH"),
        help="Existing explicit legacy lesson log; it is never created by v1.",
    )
    args = parser.parse_args()

    project_dir  = Path(args.dir).resolve()
    pt_root = Path(args.pt_root).resolve() if args.pt_root else None
    configured_legacy_path = (
        Path(args.legacy_path).expanduser().resolve() if args.legacy_path else None
    )
    try:
        needs_legacy_compatibility = args.backend == "legacy" or (
            args.mode == "runtime" and args.backend == "auto" and (args.review or args.stats)
        )
        legacy_path = (
            find_lessons_file(
                project_dir, configured_path=configured_legacy_path
            )
            if needs_legacy_compatibility
            else None
        )
        if legacy_path is not None and args.mode == "runtime" and args.backend == "auto":
            backend = LegacyMarkdownBackend(legacy_path)
        else:
            backend = resolve_backend(
                mode=args.mode,
                backend_name=args.backend,
                pt_root=pt_root,
                legacy_path=legacy_path,
            )
        lessons_path = legacy_path
        if args.review:
            if isinstance(backend, PTAgentBackend):
                review_pt_memory(backend.root)
            elif isinstance(backend, LegacyMarkdownBackend):
                review_lessons(lessons_path or backend.path)
            else:
                raise DeferredAnamnesisBackend.unavailable()
            return
        if args.stats:
            if isinstance(backend, PTAgentBackend):
                show_pt_stats(backend.root)
            elif isinstance(backend, LegacyMarkdownBackend):
                show_stats(lessons_path or backend.path)
            else:
                raise DeferredAnamnesisBackend.unavailable()
            return
        capture_interactive(pattern=args.pattern, backend=backend, quick=args.quick)
    except LessonBackendUnavailable as exc:
        print(f"ERROR [{exc.code}]: {exc}", file=sys.stderr)
        raise SystemExit(3)


if __name__ == "__main__":
    main()
