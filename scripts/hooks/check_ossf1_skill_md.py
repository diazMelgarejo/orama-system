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

CANONICAL_PREFIX = "bin/orama-system/"
MAX_LINES = 500
MIN_DESC = 20
ALLOWED_PROFILES = frozenset({"core", "composable-atom", "composite-consumer"})
APPROVAL_LIMITS = frozenset({"never", "ask-first", "auto"})

FM_RE = re.compile(r"^(?:<!--.*?-->\s*)?---\r?\n(.*?)\r?\n---", re.S | re.M)
BOUNDARIES_RE = re.compile(r"^##\s+Boundaries\b.*?(?=^##\s|\Z)", re.M | re.S)


def staged_skill_paths() -> list[Path]:
    """Repo-relative paths of staged canonical SKILL.md files.

    Returned as relative paths (not joined with ROOT) because validation reads
    content from the git index, not the working tree -- see read_staged_text.
    """
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
        paths.append(Path(line))
    return paths


def read_staged_text(rel: Path) -> str:
    """Read rel's content from the git INDEX (what will actually be committed).

    A pre-commit hook must validate staged content, not the working tree --
    an unstaged edit could make an invalid staged file look valid (or vice
    versa), and a staged-but-deleted-on-disk file must still be validated.
    """
    raw = subprocess.check_output(["git", "show", f":{rel.as_posix()}"])
    return raw.decode("utf-8", errors="replace")


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
    """True only if key's raw YAML value is list-shaped, not a scalar.

    This hand-rolled frontmatter parser stores a block-style YAML list
    (`key:\\n  - item`) as its joined item lines, which always begins with a
    "- " sequence marker once the leading indentation of the first line is
    stripped. A scalar value (e.g. `triggers: foo`, `triggers: "foo"`, or
    `triggers: -foo`) has no such marker and must be rejected -- it is not a
    list, regardless of whether it happens to be non-empty.
    """
    if key not in fm:
        return False
    val = fm[key].strip()
    if not val or val in ("[]", "{}"):
        return False
    return val.startswith("- ")


def validate(rel: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = read_staged_text(rel)
    except subprocess.CalledProcessError as exc:
        return [f"{rel}: could not read staged content from the git index ({exc})"]

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

    boundaries_match = BOUNDARIES_RE.search(body)
    if not boundaries_match:
        errors.append(f"{rel}: missing ## Boundaries section")
    else:
        section = boundaries_match.group(0)
        for subsection in ("Always Do", "Ask First", "Never Do"):
            sub = f"### {subsection}"
            heading_re = rf"^###[ \t]+{re.escape(subsection)}[ \t]*$"
            if not re.search(heading_re, section, re.M):
                errors.append(f"{rel}: missing {sub} under Boundaries")

    if not re.search(r"^##\s+(Purpose|When to Use)\b", body, re.M):
        errors.append(f"{rel}: missing ## Purpose or ## When to Use")

    # Part 1: allowed-tools is a YAML scalar, not a sequence.
    tools_key = "allowed-tools" if "allowed-tools" in fm else "allowed_tools"
    if tools_key in fm and has_list_key(fm, tools_key):
        errors.append(
            f"{rel}: allowed-tools MUST be a YAML scalar (comma-separated "
            "tokens), not a sequence"
        )

    errors.extend(_validate_profile(rel, fm))
    return errors


def _validate_profile(rel: Path, fm: dict[str, str]) -> list[str]:
    """Part 4 pipeline: unknown profile fails; Part 2 only for composable-atom.

    Existing core cards keep Part 1 only. New atoms that set
    ``format_profile: composable-atom`` MUST carry outcome, approval_limit,
    and a block-style typed ``references`` list.
    """
    errors: list[str] = []
    raw = fm.get("format_profile", "").strip()
    profile = raw or "core"
    if profile not in ALLOWED_PROFILES:
        errors.append(
            f"{rel}: format_profile {profile!r} is not one of "
            f"{sorted(ALLOWED_PROFILES)}"
        )
        return errors
    if profile != "composable-atom":
        return errors
    if not fm.get("outcome", "").strip():
        errors.append(f"{rel}: composable-atom missing required key 'outcome'")
    limit = fm.get("approval_limit", "").strip()
    if limit not in APPROVAL_LIMITS:
        errors.append(
            f"{rel}: composable-atom approval_limit must be one of "
            f"{sorted(APPROVAL_LIMITS)}"
        )
    if not has_list_key(fm, "references"):
        errors.append(
            f"{rel}: composable-atom requires a block-style references: list"
        )
    return errors



def main() -> int:
    paths = staged_skill_paths()
    if not paths:
        return 0

    all_errors: list[str] = []
    for rel in sorted(paths):
        all_errors.extend(validate(rel))

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
