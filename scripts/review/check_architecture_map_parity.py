"""Compare only the five shared graph meanings in two local architecture maps.

Canonical implementation: legacy orama-system. CI supplies the other repository
at an explicit revision; this checker never fetches a moving branch or network
resource. Audience-specific prose, columns and row order may differ.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


GRAPHS = frozenset({"Execution", "Coordination", "Knowledge", "Evidence", "Audit"})


def cells(line: str) -> list[str]:
    """Split unescaped pipes, retaining escaped content and normalized whitespace."""
    parts = [""]
    escaped = False
    for character in line.strip():
        if character == "|" and not escaped:
            parts.append("")
        else:
            parts[-1] += character
        escaped = not escaped if character == "\\" else False
    if not parts[0]:
        parts.pop(0)
    if parts and not parts[-1]:
        parts.pop()
    return [" ".join(cell.split()) for cell in parts]


def visible_lines(text: str) -> list[str]:
    """Blank code blocks without joining table fragments across a hidden block.

    Fences use matching backticks or tildes, at least three markers, and at most
    three leading spaces. A closer must be at least as long as its opener and
    contain no trailing content. An unclosed fence hides the rest of the file.
    """
    result: list[str] = []
    fence: str | None = None
    indented_code = False
    paragraph = False
    table = False
    for line in text.splitlines():
        expanded = line.expandtabs(4)
        if fence is None:
            if not line.strip():
                paragraph = table = False
                result.append("")
                continue
            indented = expanded.startswith("    ")
            if indented and (indented_code or not (paragraph or table)):
                indented_code = True
                result.append("")
                continue
            indented_code = False
        marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
        if fence is not None:
            if (marker and marker[1][0] == fence[0]
                    and len(marker[1]) >= len(fence) and not marker[2].strip()):
                fence = None
            result.append("")
            paragraph = table = False
        elif marker and (marker[1][0] != "`" or "`" not in marker[2]):
            fence = marker[1]
            result.append("")
            paragraph = table = False
        else:
            result.append(line)
            setext = paragraph and bool(re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", line))
            table = line.strip().startswith("|")
            paragraph = not setext and not table and not bool(re.match(r" {0,3}(?:#{1,6}\s|[-*_]{3,}\s*$)", line))
    return result


def meanings(path: Path) -> dict[str, str]:
    """Read exactly one shared-meaning table and reject incomplete definitions."""
    try:
        lines = visible_lines(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read {path}: {type(error).__name__}") from error
    headers = [index for index, line in enumerate(lines)
               if line.strip().startswith("|") and cells(line)[:2] == ["Graph", "Shared meaning"]]
    if len(headers) != 1:
        raise ValueError(f"{path}: expected exactly one Graph / Shared meaning table")
    start = headers[0]
    header = cells(lines[start])
    if start + 1 >= len(lines):
        raise ValueError(f"{path}: missing table separator")
    separator = cells(lines[start + 1])
    if len(separator) != len(header) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        raise ValueError(f"{path}: invalid table separator")
    result: dict[str, str] = {}
    for line in lines[start + 2:]:
        if not line.strip().startswith("|"):
            break
        row = cells(line)
        if len(row) != len(header):
            raise ValueError(f"{path}: malformed shared-meaning table row")
        graph, meaning = row[:2]
        if graph in result:
            raise ValueError(f"{path}: duplicate graph {graph}")
        if not meaning:
            raise ValueError(f"{path}: empty shared meaning for {graph}")
        result[graph] = meaning
    if result.keys() != GRAPHS:
        missing = sorted(GRAPHS - result.keys())
        extra = sorted(result.keys() - GRAPHS)
        raise ValueError(f"{path}: invalid graphs; missing={missing}, extra={extra}")
    return result


def main() -> int:
    """Compare both maps, reporting taxonomy failures without silently skipping."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("v1", type=Path, help="legacy ARCHITECTURE.md")
    parser.add_argument("v2", type=Path, help="clean ARCHITECTURE.md at an explicit revision")
    args = parser.parse_args()
    try:
        left, right = meanings(args.v1), meanings(args.v2)
        drift = sorted(graph for graph in GRAPHS if left[graph] != right[graph])
        if drift:
            raise ValueError(f"shared meaning differs: {', '.join(drift)}")
    except ValueError as error:
        print(f"architecture-map-parity: FAIL: {error}", file=sys.stderr)
        return 1
    print("architecture-map-parity: PASS: 5 shared graph meanings match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
