#!/usr/bin/env python3
"""Upgrade Perpetua-Tools path references in skill markdown to GitHub main links."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PT_BASE = "https://github.com/diazMelgarejo/Perpetua-Tools/blob/main"
PT_PATH_RE = re.compile(
    r"(?:perplexity-api/)?Perpetua-Tools/([^\s`)\]|]+)"
)
SKIP_SUFFIXES = {".py", ".sh"}


def in_code_fence(lines: list[str], index: int) -> bool:
    count = 0
    for line in lines[: index + 1]:
        if line.strip().startswith("```"):
            count += 1
    return count % 2 == 1


def already_linked(text: str, start: int) -> bool:
    before = text[:start]
    return before.rfind("](") > before.rfind("[")


def link_for(rel_path: str) -> str:
    rel_path = rel_path.rstrip(".,;:")
    return f"[`{rel_path}`]({PT_BASE}/{rel_path})"


def upgrade_line(line: str, in_fence: bool) -> str:
    if in_fence:
        # Runtime shell: prefer env var over sibling path
        line = line.replace('"$ROOT/Perpetua-Tools"', '"$PERPETUA_TOOLS_PATH"')
        line = line.replace("$ROOT/Perpetua-Tools", "$PERPETUA_TOOLS_PATH")
        line = line.replace('cd "$ROOT/Perpetua-Tools"', 'cd "$PERPETUA_TOOLS_PATH"')
        return line

    def repl_backtick(m: re.Match[str]) -> str:
        rel = m.group(1).rstrip(".,;:")
        return link_for(rel)

    # Backtick-wrapped paths first
    line = re.sub(
        r"`(?:perplexity-api/)?Perpetua-Tools/([^`]+)`",
        repl_backtick,
        line,
    )

    # Bare paths (not already inside markdown links)
    offset = 0
    out = line
    for m in PT_PATH_RE.finditer(line):
        if already_linked(line, m.start()):
            continue
        rel = m.group(1).rstrip(".,;:")
        replacement = link_for(rel)
        start = m.start() + offset
        end = m.end() + offset
        out = out[:start] + replacement + out[end:]
        offset += len(replacement) - (m.end() - m.start())
    return out


def upgrade_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changed = False
    new_lines: list[str] = []
    for i, line in enumerate(lines):
        fence = in_code_fence(lines, i)
        new_line = upgrade_line(line, fence)
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    if changed:
        path.write_text("".join(new_lines), encoding="utf-8")
    return changed


def main() -> int:
    root = Path(__file__).resolve().parents[2] / "bin" / "orama-system" / "skills"
    updated: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".md"}:
            continue
        if upgrade_file(path):
            updated.append(str(path.relative_to(root.parents[1])))
    print(f"Updated {len(updated)} files")
    for p in updated:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
