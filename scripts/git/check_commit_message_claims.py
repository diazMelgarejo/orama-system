#!/usr/bin/env python3
"""Verify add/register/introduce claims in a commit message against the
actual staged diff.

Catches the exact failure mode that motivated this check: writing "Added
`FOO` to bar.sh" in a commit message when the staged diff never actually
touches a line containing FOO -- e.g. editing a file's header comment while
believing (and saying) the array body itself was edited.

Heuristic, not exhaustive. It only flags a narrow, low-noise pattern: an
add/register/introduce verb within a short window of a code-symbol-looking
token (backtick-quoted, or a bare UPPER_SNAKE_CASE identifier -- the latter
because real commit messages often name constants/env-vars without
formatting them as code, which is exactly the case that first exposed this
gap). It cannot verify general prose claims; that needs real semantic
understanding this script does not have.
"""

from __future__ import annotations

import re
import subprocess
import sys

VERB_RE = r"(?:add(?:ed|s|ing)?|regist(?:er|ered|ers|ering)|introduc(?:e|ed|es|ing))"
IDENT_RE = r"[A-Za-z_][A-Za-z0-9_]{2,}"
PROXIMITY_WINDOW = 40  # chars between verb and identifier to count as "adjacent"

BACKTICK_IDENT_RE = re.compile(rf"`({IDENT_RE})`")
BARE_UPPER_IDENT_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,})\b")
VERB_MATCH_RE = re.compile(rf"\b{VERB_RE}\b", re.IGNORECASE)

SKIP_IDENTS = {"THE", "THIS", "THAT", "THEN", "TRUE", "FALSE", "NONE", "SELF", "TODO", "FIXME"}


def staged_added_lines() -> str:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--no-color"],
        capture_output=True,
        text=True,
        check=True,
    )
    added = []
    for line in proc.stdout.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
    return "\n".join(added)


def commit_message_body(path: str) -> str:
    lines = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            lines.append(line)
    return "".join(lines)


def _adjacent_to_a_verb(message: str, span: tuple[int, int]) -> bool:
    start = max(0, span[0] - PROXIMITY_WINDOW)
    end = min(len(message), span[1] + PROXIMITY_WINDOW)
    window = message[start:end]
    return bool(VERB_MATCH_RE.search(window))


def find_claims(message: str) -> list[str]:
    claims: set[str] = set()
    for pattern in (BACKTICK_IDENT_RE, BARE_UPPER_IDENT_RE):
        for match in pattern.finditer(message):
            ident = match.group(1)
            if ident.upper() in SKIP_IDENTS:
                continue
            if _adjacent_to_a_verb(message, match.span()):
                claims.add(ident)
    return sorted(claims)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_commit_message_claims.py <commit-msg-file>", file=sys.stderr)
        return 2
    message = commit_message_body(argv[1])
    claims = find_claims(message)
    if not claims:
        return 0
    added_text = staged_added_lines()
    missing = [c for c in claims if c not in added_text]
    if not missing:
        return 0
    print(
        "ERROR: commit message claims an add/register/introduce action for a\n"
        "symbol that does not appear in any added line of the staged diff:",
        file=sys.stderr,
    )
    for ident in missing:
        print(f"  - {ident}", file=sys.stderr)
    print(
        "\nIf this is accurate (e.g. the symbol already existed and this message\n"
        "only references it, not adds it), reword to drop the add/register/\n"
        "introduce verb from next to that name. If it's a real miss, fix the\n"
        "diff before committing -- this check exists to catch exactly that.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
