#!/usr/bin/env python3
"""Upgrade Perpetua-Tools path references in skill markdown to GitHub main links.

Shell fence rewrites use ``$PT_ROOT`` (set via sync-local-pt-checkout.md) to match
``scripts/discover.py::_resolve_perpetua_root_env``.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

PT_BASE = "https://github.com/diazMelgarejo/Perpetua-Tools/blob/main"
PT_PATH_RE = re.compile(
    r"(?:perplexity-api/)?Perpetua-Tools/([^\s`)\]|]+)"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)")

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def in_code_fence(lines: list[str], index: int) -> bool:
    count = 0
    for line in lines[: index + 1]:
        if line.strip().startswith("```"):
            count += 1
    return count % 2 == 1


def already_linked(text: str, start: int) -> bool:
    return any(
        match.start() <= start < match.end()
        for match in MARKDOWN_LINK_RE.finditer(text)
    )


def link_for(rel_path: str) -> str:
    rel_path = rel_path.rstrip(".,;:")
    return f"[`{rel_path}`]({PT_BASE}/{rel_path})"


def upgrade_line(line: str, in_fence: bool) -> str:
    if in_fence:
        line = line.replace('"$ROOT/Perpetua-Tools"', '"$PT_ROOT"')
        line = line.replace("$ROOT/Perpetua-Tools", "$PT_ROOT")
        line = line.replace('cd "$ROOT/Perpetua-Tools"', 'cd "$PT_ROOT"')
        line = line.replace('"$PERPETUA_TOOLS_PATH"', '"$PT_ROOT"')
        line = line.replace("$PERPETUA_TOOLS_PATH/", "$PT_ROOT/")
        line = line.replace("$PERPETUA_TOOLS_PATH", "$PT_ROOT")
        line = line.replace('cd "$PERPETUA_TOOLS_PATH"', 'cd "$PT_ROOT"')
        return line

    def repl_backtick(m: re.Match[str]) -> str:
        if already_linked(line, m.start()):
            return m.group(0)
        rel = m.group(1).rstrip(".,;:")
        return link_for(rel)

    line = re.sub(
        r"`(?:perplexity-api/)?Perpetua-Tools/([^`]+)`",
        repl_backtick,
        line,
    )

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
    _configure_logging()
    root = Path(__file__).resolve().parents[2] / "bin" / "orama-system" / "skills"
    updated: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".md"}:
            continue
        if upgrade_file(path):
            updated.append(str(path.relative_to(root.parents[1])))
    logger.info("Updated %d files", len(updated))
    for rel_path in updated:
        logger.info("  %s", rel_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
