"""Tests for scripts/hooks/check_ossf1_skill_md.py.

Regressions fixed per CodeRabbit review on PR #291:
- `has_list_key` accepted a scalar string (e.g. `triggers: "foo"`) as if it
  were a valid list.
- The Boundaries subsection checks (### Always Do / Ask First / Never Do)
  matched those headings anywhere in the document, not just within the
  ## Boundaries section itself.
- The hook read skill content from the working tree instead of the git
  index, so it could validate stale/wrong content relative to what was
  actually staged (and skipped staged-but-deleted-on-disk files).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts/hooks"))

import check_ossf1_skill_md as cosm  # noqa: E402


@pytest.mark.unit
def test_has_list_key_rejects_scalar_triggers_value() -> None:
    assert cosm.has_list_key({"triggers": "foo"}, "triggers") is False


@pytest.mark.unit
def test_has_list_key_rejects_quoted_scalar_triggers_value() -> None:
    assert cosm.has_list_key({"triggers": '"foo"'}, "triggers") is False


@pytest.mark.unit
def test_has_list_key_rejects_dash_prefixed_scalar_triggers_value() -> None:
    assert cosm.has_list_key({"triggers": "-foo"}, "triggers") is False


@pytest.mark.unit
def test_has_list_key_accepts_real_yaml_list() -> None:
    fm = {"triggers": "- mcp orchestration\n  - claude mcp setup"}
    assert cosm.has_list_key(fm, "triggers") is True


@pytest.mark.unit
def test_has_list_key_rejects_empty_list_markers() -> None:
    assert cosm.has_list_key({"triggers": "[]"}, "triggers") is False
    assert cosm.has_list_key({"triggers": "{}"}, "triggers") is False


@pytest.mark.unit
def test_has_list_key_missing_key_is_false() -> None:
    assert cosm.has_list_key({}, "triggers") is False


def _skill_text(boundaries_and_after: str) -> str:
    return (
        "---\n"
        "name: demo\n"
        "description: A demo skill long enough to pass the min-length check.\n"
        "version: 1.0.0\n"
        "compatibility: claude-code\n"
        "allowed-tools: bash\n"
        "triggers:\n"
        "  - demo trigger\n"
        "---\n\n"
        "# Demo\n\n"
        "## Purpose\n\n"
        "Demonstrates the skill format.\n\n"
        f"{boundaries_and_after}\n"
    )


@pytest.mark.unit
def test_boundary_subsections_matched_only_within_boundaries_section() -> None:
    """A '### Always Do' heading in a later, unrelated section must not
    satisfy the Boundaries check -- only content inside ## Boundaries,
    stopping at the next level-two heading, counts."""
    text = _skill_text(
        "## Boundaries\n\n"
        "### Ask First\n\n- Ask first about X.\n\n"
        "### Never Do\n\n- Never do Y.\n\n"
        "## Some Other Section\n\n"
        "### Always Do\n\n- This heading is outside Boundaries and must not count.\n"
    )
    _, body = cosm.parse_frontmatter(text)
    match = cosm.BOUNDARIES_RE.search(body)
    assert match is not None
    section = match.group(0)
    assert "### Always Do" not in section
    assert "### Ask First" in section
    assert "### Never Do" in section


@pytest.mark.unit
def test_boundary_subsections_all_present_within_section_passes() -> None:
    text = _skill_text(
        "## Boundaries\n\n"
        "### Always Do\n\n- Do X.\n\n"
        "### Ask First\n\n- Ask about Y.\n\n"
        "### Never Do\n\n- Never Z.\n"
    )
    _, body = cosm.parse_frontmatter(text)
    match = cosm.BOUNDARIES_RE.search(body)
    assert match is not None
    section = match.group(0)
    for sub in ("### Always Do", "### Ask First", "### Never Do"):
        assert sub in section


@pytest.mark.integration
def test_validate_flags_missing_boundary_subsection_defined_elsewhere() -> None:
    """End-to-end: validate() on a real staged file must still flag the
    missing '### Always Do' even though that heading text exists elsewhere
    in the document, outside ## Boundaries."""
    repo = _init_test_repo_with_skill(
        boundaries_and_after=(
            "## Boundaries\n\n"
            "### Ask First\n\n- Ask first about X.\n\n"
            "### Never Do\n\n- Never do Y.\n\n"
            "## Unrelated Section\n\n"
            "### Always Do\n\n- Not actually under Boundaries.\n"
        )
    )
    errors = _validate_in_repo(repo)
    assert any("### Always Do" in e for e in errors)


@pytest.mark.integration
def test_validate_rejects_boundary_subsection_mentioned_only_in_prose() -> None:
    """A heading-looking token embedded in prose is not a subsection heading."""
    repo = _init_test_repo_with_skill(
        boundaries_and_after=(
            "## Boundaries\n\n"
            "The text `### Always Do` appears in an inline code example.\n\n"
            "### Ask First\n\n- Ask first about X.\n\n"
            "### Never Do\n\n- Never do Y.\n"
        )
    )
    errors = _validate_in_repo(repo)
    assert any("### Always Do" in e for e in errors)


def _init_test_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "f.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)


def _skill_rel_path() -> Path:
    return Path("bin/orama-system/skills/demo/SKILL.md")


def _init_test_repo_with_skill(boundaries_and_after: str, tmp_dir: Path | None = None) -> Path:
    base = tmp_dir if tmp_dir is not None else Path(tempfile.mkdtemp())
    repo = base / "repo"
    _init_test_repo(repo)
    skill_path = repo / _skill_rel_path()
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(boundaries_and_after), encoding="utf-8")
    subprocess.run(["git", "add", str(skill_path)], cwd=repo, check=True)
    return repo


def _validate_in_repo(repo: Path) -> list[str]:
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        return cosm.validate(_skill_rel_path())
    finally:
        os.chdir(cwd)


@pytest.mark.integration
def test_validate_reads_staged_content_not_working_tree(tmp_path: Path) -> None:
    """The hook must validate what's staged in the index, not whatever the
    working-tree file currently contains -- an unstaged edit made *after*
    `git add` must not change the verdict."""
    repo = _init_test_repo_with_skill(
        boundaries_and_after=(
            "## Boundaries\n\n"
            "### Always Do\n\n- Do X.\n\n"
            "### Ask First\n\n- Ask about Y.\n\n"
            "### Never Do\n\n- Never Z.\n"
        ),
        tmp_dir=tmp_path,
    )
    skill_path = repo / _skill_rel_path()

    # Corrupt the working-tree copy *after* staging. The index still holds
    # the valid version, so validation (which reads the index) must pass.
    skill_path.write_text("not a skill file at all", encoding="utf-8")

    errors = _validate_in_repo(repo)
    assert errors == [], errors


@pytest.mark.integration
def test_validate_does_not_require_working_tree_file_to_exist(tmp_path: Path) -> None:
    """A staged-but-deleted-on-disk file must still be validated from the
    index, not skipped because the working-tree path no longer exists."""
    repo = _init_test_repo_with_skill(
        boundaries_and_after=(
            "## Boundaries\n\n"
            "### Always Do\n\n- Do X.\n\n"
            "### Ask First\n\n- Ask about Y.\n\n"
            "### Never Do\n\n- Never Z.\n"
        ),
        tmp_dir=tmp_path,
    )
    skill_path = repo / _skill_rel_path()
    skill_path.unlink()  # gone from disk, still staged in the index

    errors = _validate_in_repo(repo)
    assert errors == [], errors


@pytest.mark.integration
def test_main_exits_zero_for_valid_staged_skill(tmp_path: Path) -> None:
    repo = _init_test_repo_with_skill(
        boundaries_and_after=(
            "## Boundaries\n\n"
            "### Always Do\n\n- Do X.\n\n"
            "### Ask First\n\n- Ask about Y.\n\n"
            "### Never Do\n\n- Never Z.\n"
        ),
        tmp_dir=tmp_path,
    )
    result = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts/hooks/check_ossf1_skill_md.py")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
def test_main_exits_nonzero_for_scalar_triggers(tmp_path: Path) -> None:
    """End-to-end regression pin: a skill with a scalar `triggers:` value
    and no 'Activates for/when' phrase in its description must fail, not
    be silently accepted as if it had a real triggers list."""
    text = (
        "---\n"
        "name: demo\n"
        "description: A demo skill long enough to pass the min-length check.\n"
        "version: 1.0.0\n"
        "compatibility: claude-code\n"
        "allowed-tools: bash\n"
        'triggers: "not-a-list"\n'
        "---\n\n"
        "# Demo\n\n"
        "## Purpose\n\n"
        "Demonstrates the skill format.\n\n"
        "## Boundaries\n\n"
        "### Always Do\n\n- Do X.\n\n"
        "### Ask First\n\n- Ask about Y.\n\n"
        "### Never Do\n\n- Never Z.\n"
    )
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    skill_path = repo / _skill_rel_path()
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", str(skill_path)], cwd=repo, check=True)

    result = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts/hooks/check_ossf1_skill_md.py")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "triggers" in result.stderr
