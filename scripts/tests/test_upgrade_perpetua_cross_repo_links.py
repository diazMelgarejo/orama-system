from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills"))
from upgrade_perpetua_cross_repo_links import upgrade_line


def test_preserves_existing_markdown_link_with_backtick_label() -> None:
    line = (
        "[`Perpetua-Tools/config/SKILL.md`]"
        "(https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md)"
    )
    assert upgrade_line(line, in_fence=False) == line


def test_preserves_existing_markdown_link_with_bare_path_label() -> None:
    line = (
        "[Perpetua-Tools/config/SKILL.md]"
        "(https://example.invalid/config/SKILL.md)"
    )
    assert upgrade_line(line, in_fence=False) == line


def test_converts_bare_path_outside_link() -> None:
    line = "See Perpetua-Tools/config/SKILL.md for policy."
    out = upgrade_line(line, in_fence=False)
    assert out == (
        "See [`config/SKILL.md`]"
        "(https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md) "
        "for policy."
    )


def test_idempotent_on_already_upgraded_line() -> None:
    line = (
        "[`config/SKILL.md`]"
        "(https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md)"
    )
    assert upgrade_line(line, in_fence=False) == line
