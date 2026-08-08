#!/usr/bin/env python3
"""Pre-commit gate: Oramasys Standard Skill Format (OSSF-1) for orama canonical SKILL.md.

Scope: staged files under bin/orama-system/ only (not .agents, .claude, or other repos).
See docs/v2/ and bin/orama-system/references/skill-architecture-guide.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
CANONICAL_PREFIX = "bin/orama-system/"
MAX_LINES = 500
MIN_DESC = 20

FM_RE = re.compile(r"^(?:<!--.*?-->\s*)?---\r?\n(.*?)\r?\n---", re.S | re.M)


def staged_skill_paths() -> list[Path]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        text=True,
    )
    paths: list[Path] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.endswith("/SKILL.md"):
            continue
        if not line.startswith(CANONICAL_PREFIX):
            continue
        paths.append(ROOT / line)
    return paths


def parse_frontmatter(text: str) -> tuple[dict[str, str], str] | tuple[None, str]:
    m = FM_RE.match(text)
    if not m:
        return None, text
    raw = m.group(1)
    body = text[m.end() :]
    data: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for line in raw.splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:", line) and not line.startswith(" "):
            if key is not None:
                data[key] = "\n".join(buf).strip()
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest in ("|", ">", "|-", ">-", ""):
                buf = []
            else:
                data[key] = rest
                key = None
                buf = []
        elif key is not None:
            buf.append(line)
    if key is not None:
        data[key] = "\n".join(buf).strip()
    return data, body


def has_list_key(fm: dict[str, str], key: str) -> bool:
    if key not in fm:
        return False
    val = fm[key].strip()
    return bool(val) and val not in ("[]", "{}")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.count("\n") + 1
    if lines > MAX_LINES:
        errors.append(f"{rel}: body {lines} lines exceeds OSSF-1 hard ceiling {MAX_LINES}")

    fm, body = parse_frontmatter(text)
    if fm is None:
        errors.append(f"{rel}: missing YAML frontmatter (--- block)")
        return errors

    for key in ("name", "description", "version"):
        if not fm.get(key, "").strip():
            errors.append(f"{rel}: frontmatter missing required key '{key}'")

    desc = fm.get("description", "")
    if desc and len(desc) < MIN_DESC:
        errors.append(f"{rel}: description too short ({len(desc)} chars; need >={MIN_DESC})")

    if not has_list_key(fm, "triggers") and "Activates for" not in desc and "Activates when" not in desc:
        errors.append(f"{rel}: add triggers: list or embed activation phrases in description")

    if not fm.get("compatibility", "").strip() and not fm.get("agent_compatibility", "").strip():
        errors.append(f"{rel}: missing compatibility (or agent_compatibility for overlays)")

    if not fm.get("allowed-tools", "").strip() and not fm.get("allowed_tools", "").strip():
        errors.append(f"{rel}: missing allowed-tools")

    if not re.search(r"^##\s+Boundaries\b", body, re.M):
        errors.append(f"{rel}: missing ## Boundaries section")
    else:
        for sub in ("### Always Do", "### Ask First", "### Never Do"):
            if sub not in body:
                errors.append(f"{rel}: missing {sub} under Boundaries")

    if not re.search(r"^##\s+(Purpose|When to Use)\b", body, re.M):
        errors.append(f"{rel}: missing ## Purpose or ## When to Use")

    return errors


def main() -> int:
    paths = staged_skill_paths()
    if not paths:
        return 0

    all_errors: list[str] = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        all_errors.extend(validate(path))

    if all_errors:
        print("OSSF-1 pre-commit: canonical SKILL.md validation failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "Fix staged bin/orama-system/**/SKILL.md files or unstage them.",
            file=sys.stderr,
        )
        return 1

    print(f"OSSF-1 pre-commit: OK ({len(paths)} canonical SKILL.md file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
