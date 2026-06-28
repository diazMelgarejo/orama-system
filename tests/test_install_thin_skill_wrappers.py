from __future__ import annotations

"""Tests for the workspace_candidates(), workspace_path(), and repo_relative()
functions added/modified in
bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py.
"""

import importlib.util
import sys
from pathlib import Path, PurePosixPath

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "skillify"
    / "scripts"
    / "install_thin_skill_wrappers.py"
)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("install_thin_skill_wrappers", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ── workspace_candidates ──────────────────────────────────────────────────────

def test_workspace_candidates_orama_exact(mod):
    candidates = mod.workspace_candidates("orama-system")
    # Should include both "orama-system" and "ultrathink-system" as Path objects.
    strs = [c.name for c in candidates]
    assert "orama-system" in strs
    assert "ultrathink-system" in strs


def test_workspace_candidates_orama_subpath(mod):
    candidates = mod.workspace_candidates("orama-system/bin/orama-system/SKILL.md")
    # Both aliases should carry the suffix.
    strs = [str(c) for c in candidates]
    assert any("orama-system/bin/orama-system/SKILL.md" in s for s in strs)
    assert any("ultrathink-system/bin/orama-system/SKILL.md" in s for s in strs)


def test_workspace_candidates_perpetua_exact(mod):
    candidates = mod.workspace_candidates("perplexity-api/Perpetua-Tools")
    strs = [str(c) for c in candidates]
    assert any("perplexity-api/Perpetua-Tools" in s for s in strs)
    assert any("Perplexity-Tools" in s for s in strs)


def test_workspace_candidates_perpetua_subpath(mod):
    candidates = mod.workspace_candidates("perplexity-api/Perpetua-Tools/SKILL.md")
    strs = [str(c) for c in candidates]
    assert any("Perpetua-Tools/SKILL.md" in s for s in strs)
    assert any("Perplexity-Tools/SKILL.md" in s for s in strs)


def test_workspace_candidates_no_match_returns_single(mod):
    candidates = mod.workspace_candidates("some-other/path/SKILL.md")
    assert len(candidates) == 1
    assert candidates[0].name == "SKILL.md"


def test_workspace_candidates_no_duplicates(mod):
    """The first alias is the same as the original rel, so no duplicates."""
    candidates = mod.workspace_candidates("orama-system")
    strs = [str(c) for c in candidates]
    assert len(strs) == len(set(strs))


# ── workspace_path ────────────────────────────────────────────────────────────

def test_workspace_path_returns_existing_candidate(mod, tmp_path, monkeypatch):
    """workspace_path returns the first existing Path among the candidates."""
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    # Create only the "ultrathink-system" variant; "orama-system" does not exist.
    ultra_dir = tmp_path / "ultrathink-system"
    ultra_dir.mkdir()
    skill = ultra_dir / "SKILL.md"
    skill.write_text("# skill\n", encoding="utf-8")

    result = mod.workspace_path("orama-system/SKILL.md")
    assert result == skill


def test_workspace_path_returns_first_candidate_when_none_exist(mod, tmp_path, monkeypatch):
    """When no candidate exists, workspace_path returns candidates[0]."""
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    result = mod.workspace_path("orama-system/missing/SKILL.md")
    # First candidate should be ROOT / "orama-system/missing/SKILL.md"
    assert result == tmp_path / "orama-system" / "missing" / "SKILL.md"


def test_workspace_path_prefers_primary_over_alias(mod, tmp_path, monkeypatch):
    """If both primary and alias exist, the primary (first candidate) wins."""
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    for name in ("orama-system", "ultrathink-system"):
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

    result = mod.workspace_path("orama-system/SKILL.md")
    assert result == tmp_path / "orama-system" / "SKILL.md"


# ── repo_relative ─────────────────────────────────────────────────────────────

def test_repo_relative_strips_orama_prefix(mod):
    result = mod.repo_relative("orama-system/bin/orama-system/cidf/SKILL.md")
    assert result == "bin/orama-system/cidf/SKILL.md"


def test_repo_relative_strips_perpetua_prefix(mod):
    result = mod.repo_relative("perplexity-api/Perpetua-Tools/config/SKILL.md")
    assert result == "config/SKILL.md"


def test_repo_relative_exact_orama_prefix_returns_dot(mod):
    result = mod.repo_relative("orama-system")
    assert result == "."


def test_repo_relative_exact_perpetua_prefix_returns_dot(mod):
    result = mod.repo_relative("perplexity-api/Perpetua-Tools")
    assert result == "."


def test_repo_relative_no_known_prefix_splits_on_first_slash(mod):
    result = mod.repo_relative("some-repo/path/to/SKILL.md")
    assert result == "path/to/SKILL.md"


def test_repo_relative_no_slash_returns_as_is(mod):
    result = mod.repo_relative("singleword")
    assert result == "singleword"


def test_repo_relative_longer_prefix_wins(mod):
    """perplexity-api/Perpetua-Tools is longer than a bare alias; it must win."""
    result = mod.repo_relative("perplexity-api/Perpetua-Tools/hardware/SKILL.md")
    assert result == "hardware/SKILL.md"


# ── wrapper() uses PurePosixPath for rel_dir ──────────────────────────────────

def test_wrapper_rel_dir_uses_posix_separators(mod):
    """wrapper() must embed forward-slash rel_dir even on Windows paths."""
    spec = mod.SkillSpec(
        slug="hermes-harness",
        canonical="orama-system/bin/orama-system/skills/hermes-harness/SKILL.md",
        name="Hermes Harness",
        description="Test description.",
    )
    text = mod.wrapper(spec)
    rel = mod.repo_relative(spec.canonical)
    rel_dir = PurePosixPath(rel).parent.as_posix()
    # The cd command should use a POSIX separator path.
    assert f'cd "$ROOT/{rel_dir}"' in text
    assert "\\" not in rel_dir


def test_wrapper_embeds_repo_relative_not_absolute(mod):
    """wrapper() must never embed an absolute host path."""
    spec = mod.SkillSpec(
        slug="hermes-harness",
        canonical="orama-system/bin/orama-system/skills/hermes-harness/SKILL.md",
        name="Hermes Harness",
        description="Test.",
    )
    text = mod.wrapper(spec)
    assert str(ROOT) not in text
    assert str(Path.home()) not in text


# ── hermes-harness is in CANONICAL_SKILLS ────────────────────────────────────

def test_hermes_harness_in_canonical_skills(mod):
    assert "orama-system/bin/orama-system/skills/hermes-harness/SKILL.md" in mod.CANONICAL_SKILLS