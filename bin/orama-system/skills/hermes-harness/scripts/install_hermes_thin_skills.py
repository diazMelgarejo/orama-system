#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", LOCALAPPDATA / "hermes"))
HERMES_SKILLS = HERMES_HOME / "skills" / "pt-orama"


@dataclass(frozen=True)
class HermesWrapper:
    slug: str
    description: str
    canonical: str
    purpose: str


WRAPPERS = [
    HermesWrapper(
        slug="pt-orama-council",
        description="Thin Hermes command for PT-orama council coordination.",
        canonical="bin/orama-system/skills/hermes-harness/commands/pt-orama-council/SKILL.md",
        purpose="Coordinate PT-orama council work using canonical Hermes harness rules.",
    ),
    HermesWrapper(
        slug="pt-orama-review",
        description="Thin Hermes command for PT-orama findings-first review.",
        canonical="bin/orama-system/skills/hermes-harness/commands/pt-orama-review/SKILL.md",
        purpose="Review PT-orama plans or deliveries with findings-first discipline.",
    ),
    HermesWrapper(
        slug="pt-orama-delegate",
        description="Thin Hermes command for bounded PT-orama specialist delegation.",
        canonical="bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate/SKILL.md",
        purpose="Handle narrow delegated subtasks without committing or leaking private state.",
    ),
]


def wrapper_text(spec: HermesWrapper) -> str:
    return f"""---
name: {spec.slug}
description: "{spec.description}"
version: 1.0.0
author: Codex + orama-system
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [pt-orama, hermes, thin-wrapper, windows]
created_by: agent
---

# {spec.slug}

This is a thin local Hermes slash-command wrapper.

Purpose: {spec.purpose}

Canonical source of truth:

- Repo: `diazMelgarejo/orama-system`
- Branch/PR at install time: `codex/hermes-ecc-harness-skills` / PR #96
- Canonical path: `{spec.canonical}`

## Before Use

1. Treat this file as an adapter only; do not copy canonical skill bodies here.
2. Read the canonical path from the current orama-system checkout before acting.
3. If the checkout is dirty or behind remote, report drift instead of overwriting.
4. Never copy raw `%LOCALAPPDATA%\\hermes`, secrets, OAuth tokens, or personal
   memory into tracked files.
5. Do not commit, delete, deploy, force-push, or change account/provider
   settings unless the user explicitly instructs that exact action.

## Windows Readiness

- Hermes one-shot: `hermes chat --query \"Reply with exactly: HERMES_READY\" --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1`
- AGY install: `irm https://antigravity.google/cli/install.ps1 | iex`
- AGY readiness: `agy --print \"Reply with exactly: AGY_READY\"` must print visible stdout.
- LM Studio readiness: `/v1/models` is not enough; require a fast chat-completions canary.

## Response Shape

```text
ASSUMPTIONS:
FINDINGS:
PROPOSED ACTIONS:
TESTS / VERIFICATION:
RISKS:
HANDOFF NOTES:
```
"""


def is_managed_wrapper(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---\n", 4)
    if end == -1:
        return False
    frontmatter = text[4:end]
    return "created_by: agent" in frontmatter


def install(dry_run: bool = False) -> list[Path]:
    written: list[Path] = []
    missing = [spec.canonical for spec in WRAPPERS if not (REPO_ROOT / spec.canonical).is_file()]
    if missing:
        raise FileNotFoundError(f"missing canonical command cards: {', '.join(missing)}")
    if not dry_run:
        HERMES_SKILLS.mkdir(parents=True, exist_ok=True)
        (HERMES_SKILLS / "DESCRIPTION.md").write_text(
            "# PT-orama Local Commands\n\n"
            "Thin local Hermes slash-skill wrappers for PT-orama. "
            "Canonical behavior lives in the orama-system repo.\n",
            encoding="utf-8",
        )
    for spec in WRAPPERS:
        target = HERMES_SKILLS / spec.slug.removeprefix("pt-orama-") / "SKILL.md"
        if dry_run:
            if target.is_file() and not is_managed_wrapper(target):
                print(f"would skip unmanaged wrapper: {target}")
            else:
                print(target)
            continue

        if target.is_file() and not is_managed_wrapper(target):
            print(f"skipped unmanaged wrapper: {target}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(wrapper_text(spec), encoding="utf-8")
        written.append(target)
    return written


def verify() -> list[str]:
    errors: list[str] = []
    for spec in WRAPPERS:
        target = HERMES_SKILLS / spec.slug.removeprefix("pt-orama-") / "SKILL.md"
        if not target.is_file():
            errors.append(f"missing wrapper: {target}")
            continue
        if not is_managed_wrapper(target):
            errors.append(f"unmanaged wrapper preserved: {target}")
            continue
        text = target.read_text(encoding="utf-8")
        for required in ("thin local Hermes", spec.canonical, "AGY_READY", "HERMES_READY"):
            if required not in text:
                errors.append(f"missing {required!r}: {target}")
    return errors


def run_tests() -> int:
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Mock HERMES_SKILLS
        global HERMES_SKILLS
        original_skills = HERMES_SKILLS
        HERMES_SKILLS = tmp_path / "skills"

        try:
            # 1. Fresh install
            install()
            council_path = HERMES_SKILLS / "council" / "SKILL.md"
            if not council_path.is_file():
                print("FAIL: council wrapper not created")
                return 1

            # 2. Check syntax update
            text = council_path.read_text(encoding="utf-8")
            if "hermes chat --query" not in text:
                print("FAIL: legacy syntax found in wrapper")
                return 1
            if "--max-turns 1" not in text:
                print("FAIL: turn bound missing in wrapper")
                return 1

            # 3. Non-clobber: overwrite agent-owned
            council_path.write_text(text.replace("version: 1.0.0", "version: 1.0.1"), encoding="utf-8")
            install()
            if "version: 1.0.0" not in council_path.read_text(encoding="utf-8"):
                print("FAIL: agent-owned wrapper not updated")
                return 1

            # 4. Non-clobber: protect user-owned
            user_text = text.replace("created_by: agent", "created_by: user")
            council_path.write_text(user_text, encoding="utf-8")
            install()
            if "created_by: user" not in council_path.read_text(encoding="utf-8"):
                print("FAIL: user-owned wrapper was clobbered")
                return 1

            print("non-clobber and syntax tests passed")
            return 0
        finally:
            HERMES_SKILLS = original_skills


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.install and not args.verify and not args.test:
        parser.error("choose --install, --verify, and/or --test")
    if args.test:
        return run_tests()
    if args.install:
        written = install(args.dry_run)
        if not args.dry_run:
            print(f"wrote {len(written)} Hermes wrapper files")
    if args.verify:
        errors = verify()
        if errors:
            for error in errors:
                print(error)
            return 1
        print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
