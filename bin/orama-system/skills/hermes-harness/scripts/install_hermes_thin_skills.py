#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


def resolve_repo_root() -> Path:
    """Return orama-system git toplevel; fall back to parents[5] when not in a worktree."""
    script = Path(__file__).resolve()
    try:
        top = subprocess.check_output(
            ["git", "-C", str(script.parent), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(top)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return script.parents[5]


def install_provenance() -> str:
    """Branch/commit stamp for thin wrappers — never hardcode stale PR numbers."""
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return f"Branch at install time: `{branch}` @ `{sha}`"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "Read canonical SKILL.md from the current orama-system checkout before acting."


REPO_ROOT = resolve_repo_root()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", LOCALAPPDATA / "hermes"))
HERMES_SKILLS = HERMES_HOME / "skills" / "pt-orama"
MANAGED_MARKER = "created_by: agent"


@dataclass(frozen=True)
class HermesWrapper:
    slug: str
    description: str
    canonical: str
    purpose: str


WRAPPERS = [
    HermesWrapper(
        slug="pt-hardware-policy",
        description="Thin Hermes command for PT canonical hardware affinity validation.",
        canonical="bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy/SKILL.md",
        purpose="Validate model↔hardware affinity via Perpetua-Tools policy before LM Studio dispatch.",
    ),
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
    HermesWrapper(
        slug="pt-orama-lesson-mining",
        description="Thin Hermes command for PT lesson graduation via learn.py.",
        canonical="bin/orama-system/skills/hermes-harness/commands/pt-orama-lesson-mining/SKILL.md",
        purpose="Graduate durable session insights into Perpetua-Tools semantic memory.",
    ),
]


def hermes_local_dir(slug: str) -> str:
    """Map canonical slug to Hermes local command folder name."""
    if slug.startswith("pt-orama-"):
        return slug.removeprefix("pt-orama-")
    return slug

def wrapper_text(spec: HermesWrapper) -> str:
    provenance = install_provenance()
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
- {provenance}
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

- Hermes one-shot: `hermes chat --query \"Reply with exactly: HERMES_READY\" --quiet --safe-mode --provider nous --model stepfun/step-3.7-flash:free --max-turns 1`
- AGY install (save-first — never pipe remote script to iex): `Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile \"$env:TEMP\\agy-install.ps1\"; Get-Content \"$env:TEMP\\agy-install.ps1\" | Select-Object -First 40; & powershell -NoProfile -ExecutionPolicy Bypass -File \"$env:TEMP\\agy-install.ps1\"`
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
    """Return whether *path* has our marker in its YAML frontmatter."""
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.strip() == MANAGED_MARKER:
            return True
    return False


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
        target = HERMES_SKILLS / hermes_local_dir(spec.slug) / "SKILL.md"
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
        target = HERMES_SKILLS / hermes_local_dir(spec.slug) / "SKILL.md"
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

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        global HERMES_SKILLS
        original_skills = HERMES_SKILLS
        HERMES_SKILLS = tmp_path / "skills"

        try:
            install()
            council_path = HERMES_SKILLS / "council" / "SKILL.md"
            if not council_path.is_file():
                print("FAIL: council wrapper not created")
                return 1

            if not is_managed_wrapper(council_path):
                print("FAIL: managed marker not found in fresh wrapper")
                return 1

            text = council_path.read_text(encoding="utf-8")
            if "hermes chat --query" not in text:
                print("FAIL: hermes chat command missing from wrapper")
                return 1
            if "--max-turns 1" not in text:
                print("FAIL: turn bound missing in wrapper")
                return 1

            council_path.write_text(text.replace("version: 1.0.0", "version: 1.0.1"), encoding="utf-8")
            install()
            if "version: 1.0.0" not in council_path.read_text(encoding="utf-8"):
                print("FAIL: agent-owned wrapper not updated on re-install")
                return 1

            user_text = text.replace(f"\n{MANAGED_MARKER}\n", "\ncreated_by: user\n")
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
