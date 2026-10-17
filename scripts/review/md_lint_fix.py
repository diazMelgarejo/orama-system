#!/usr/bin/env python3
"""Mechanical markdown lint repair: blank lines around structure, wrapped long prose.

Fixes only what is safe to fix without judgement, so the bytes of meaning never change:

* MD022 / MD032 / MD058  blank lines around headings, lists and tables
* MD013                  wrap prose and list items the linter would flag (non-strict rule)
* MD060 (compact)        normalise table delimiter rows such as ``|---|---|``

It never touches fenced code, front matter, HTML blocks or comments, block quotes,
indented code, headings, table rows or hard-break lines. A line that cannot be wrapped
safely (a long URL, or a wrap that would start a line with a list or heading marker) is
reported and left alone, because rewording is an author decision, not a formatter's.

Usage::

    python scripts/review/md_lint_fix.py --check FILE...    # exit 1 if anything would change
    python scripts/review/md_lint_fix.py --write FILE...    # rewrite in place (idempotent)

Exit codes: 0 clean, 1 changes needed (--check), 2 unfixable lines remain.
Run ``markdownlint-cli2`` afterwards: this tool narrows the gap, the linter stays the judge.
"""
from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path

DEFAULT_WIDTH = 100
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^\s*(```|~~~)")
DELIM_ROW = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
UNSAFE_START = re.compile(r"^\s*([-*+]\s|\d+[.)]\s|#|>|\|)")


def classify(line: str) -> str:
    """Return the structural kind of one line outside fenced code."""
    stripped = line.strip()
    if not stripped:
        return "blank"
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("|"):
        return "table"
    if LIST_ITEM.match(line):
        return "list"
    if stripped.startswith((">", "<")):
        return "opaque"
    return "text"


def normalise_delimiter(line: str) -> str:
    """Rewrite a compact table delimiter row to the spaced style the linter expects."""
    if not (line.lstrip().startswith("|") and DELIM_ROW.match(line)):
        return line
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return "| " + " | ".join(cells) + " |"


def too_long(line: str, width: int) -> bool:
    """Mirror markdownlint MD013 (non-strict): flag only when whitespace follows the limit.

    A line whose overflow is one unbreakable token (a URL) passes the linter, and wrapping
    it would only churn the diff, so the tool leaves it alone.
    """
    return re.match(rf"^.{{{width}}}.*\s.+$", line) is not None


def wrap(line: str, width: int) -> list[str] | None:
    """Wrap one prose or list line, or return None when it cannot be wrapped safely."""
    if not too_long(line, width) or line.endswith(("  ", "\\")):
        return [line]
    item = LIST_ITEM.match(line)
    if item:
        first = item.group(0)
        indent, subsequent = first, " " * len(first)
        body = line[len(first):]
    else:
        indent = subsequent = line[: len(line) - len(line.lstrip())]
        body = line[len(indent):]
    out = textwrap.wrap(body, width, initial_indent=indent, subsequent_indent=subsequent,
                        break_long_words=False, break_on_hyphens=False)
    if any(len(p) > width for p in out) or any(UNSAFE_START.match(p) for p in out[1:]):
        return None
    return out or [line]


def fix(text: str, width: int = DEFAULT_WIDTH) -> tuple[str, list[int]]:
    """Return the repaired text and the 1-based numbers of lines left unfixable."""
    lines = text.split("\n")
    out: list[str] = []
    unfixable: list[int] = []
    prev = "blank"
    in_fence = in_front = in_comment = False
    for number, raw in enumerate(lines, start=1):
        if number == 1 and raw.strip() == "---":
            in_front = True
            out.append(raw)
            continue
        if in_front:
            out.append(raw)
            in_front = raw.strip() != "---"
            continue
        if FENCE.match(raw):
            in_fence = not in_fence
            if in_fence and prev not in ("blank", "fence") and out and out[-1] != "":
                out.append("")
            out.append(raw)
            prev = "fence"
            continue
        if in_fence or in_comment:
            out.append(raw)
            if in_comment and "-->" in raw:
                in_comment = False
            continue
        if raw.lstrip().startswith("<!--"):
            out.append(raw)
            in_comment = "-->" not in raw
            prev = "opaque"
            continue

        kind = classify(raw)
        if kind == "table":
            raw = normalise_delimiter(raw)
        indented_cont = (prev in ("list", "listcont") and raw.startswith((" ", "\t"))
                         and kind == "text")
        if indented_cont:
            kind = "listcont"
        need_blank = (
            (kind == "heading" and prev not in ("blank", "heading"))
            or (prev == "heading" and kind != "blank")
            or (kind == "table" and prev not in ("blank", "table"))
            or (prev == "table" and kind not in ("blank", "table"))
            or (kind == "list" and prev not in ("blank", "list", "listcont"))
            or (kind == "text" and prev in ("list", "listcont"))
        )
        if need_blank and out and out[-1] != "":
            out.append("")
        if kind in ("list", "listcont") or (kind == "text" and not raw.startswith("    ")):
            wrapped = wrap(raw, width)
            if wrapped is None:
                unfixable.append(number)
                wrapped = [raw]
            out.extend(wrapped)
        else:
            out.append(raw)
        prev = kind
    return "\n".join(out), unfixable


def main(argv: list[str] | None = None) -> int:
    """Check or rewrite the given files; return the documented exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="exit 1 if any file would change")
    mode.add_argument("--write", action="store_true", help="rewrite files in place")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)

    changed = False
    stuck = False
    for path in args.files:
        original = path.read_text(encoding="utf-8")
        repaired, unfixable = fix(original, args.width)
        for number in unfixable:
            print(f"{path}:{number}: cannot wrap safely; edit by hand", file=sys.stderr)
        stuck = stuck or bool(unfixable)
        if repaired != original:
            changed = True
            if args.write:
                path.write_text(repaired, encoding="utf-8", newline="\n")
                print(f"fixed {path}")
            else:
                print(f"would change {path}")
    if stuck:
        return 2
    return 1 if (changed and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
