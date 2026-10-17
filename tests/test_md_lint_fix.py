"""The mechanical markdown repair tool is safe, idempotent, and leaves code alone."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "review" / "md_lint_fix.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("md_lint_fix", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_blank_lines_are_added_around_headings_lists_and_tables(tool) -> None:
    src = "# T\ntext\n## H\n- a\n- b\nafter\n| a | b |\n|---|---|\n| 1 | 2 |\nend"
    out, stuck = tool.fix(src)
    assert stuck == []
    assert out == ("# T\n\ntext\n\n## H\n\n- a\n- b\n\nafter\n\n"
                   "| a | b |\n| --- | --- |\n| 1 | 2 |\n\nend")


def test_long_prose_and_list_items_wrap_with_hanging_indent(tool) -> None:
    long = "word " * 40
    out, _ = tool.fix(f"- {long.strip()}\n\n{long.strip()}")
    assert all(len(line) <= 100 for line in out.split("\n"))
    items = out.split("\n\n")[0].split("\n")
    assert items[0].startswith("- ") and all(line.startswith("  ") for line in items[1:])


def test_fences_front_matter_comments_and_headings_are_untouched(tool) -> None:
    long = "x " * 80
    src = f"---\nk: {long}\n---\n# {long}\n\n```\n{long}\n```\n\n<!-- {long} -->\n"
    out, _ = tool.fix(src)
    assert out == src


def test_unwrappable_lines_are_reported_not_mangled(tool) -> None:
    url = "https://example.com/" + "a" * 120
    out, stuck = tool.fix(f"see {url}\n")
    assert stuck == [1] and out == f"see {url}\n"


def test_a_wrap_never_starts_a_line_with_a_list_marker(tool) -> None:
    line = "a" * 99 + " - b and some more words"
    out, stuck = tool.fix(line)
    assert stuck == [1] and out == line


def test_fix_is_idempotent(tool) -> None:
    src = "# T\ntext " + "word " * 40 + "\n- a\n|x|y|\n|-|-|\n"
    once, _ = tool.fix(src)
    assert tool.fix(once)[0] == once


def test_check_mode_exit_codes(tool, tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("# T\n\ntext\n", encoding="utf-8")
    dirty = tmp_path / "dirty.md"
    dirty.write_text("# T\ntext\n", encoding="utf-8")
    assert tool.main(["--check", str(clean)]) == 0
    assert tool.main(["--check", str(dirty)]) == 1
    assert tool.main(["--write", str(dirty)]) == 0
    assert dirty.read_text(encoding="utf-8") == "# T\n\ntext\n"
