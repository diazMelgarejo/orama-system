from __future__ import annotations

"""Tests for the workspace_candidates(), workspace_path(), and repo_relative()
functions added/modified in
bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py.
"""

import errno
import importlib.util
import json
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
    strs = [c.as_posix() for c in candidates]
    assert any("orama-system/bin/orama-system/SKILL.md" in s for s in strs)
    assert any("ultrathink-system/bin/orama-system/SKILL.md" in s for s in strs)


def test_workspace_candidates_perpetua_exact(mod):
    candidates = mod.workspace_candidates("perplexity-api/Perpetua-Tools")
    strs = [c.as_posix() for c in candidates]
    assert any("perplexity-api/Perpetua-Tools" in s for s in strs)
    assert any("Perplexity-Tools" in s for s in strs)


def test_workspace_candidates_perpetua_subpath(mod):
    candidates = mod.workspace_candidates("perplexity-api/Perpetua-Tools/SKILL.md")
    strs = [c.as_posix() for c in candidates]
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


# ── SkillInventory / inventory_root / inventory_all_roots / render_inventory ──
# Task 1: read-only cross-root inventory. These functions must never call an
# install, archive, or symlink function — they only observe.

def test_render_inventory_is_sorted_and_portable(mod, tmp_path: Path) -> None:
    rows = [
        mod.SkillInventory("zeta", "gemini", "regular", "a" * 64, ("name",)),
        mod.SkillInventory("alpha", "agents", "symlink", "b" * 64, ("description", "name")),
    ]
    rendered = mod.render_inventory(rows, home=tmp_path)
    assert rendered.index("alpha") < rendered.index("zeta")
    assert str(tmp_path) not in rendered
    assert "agents" in rendered


def test_render_inventory_strips_home_if_it_leaks_into_a_row(mod, tmp_path: Path) -> None:
    """home= is not decorative: even if a row's slug somehow carried the raw
    home path, render_inventory must still not leak it into the output."""
    leaky_slug = f"weird-{tmp_path}"
    rows = [mod.SkillInventory(leaky_slug, "gemini", "regular", "c" * 64, ())]
    rendered = mod.render_inventory(rows, home=tmp_path)
    assert str(tmp_path) not in rendered
    assert "<home>" in rendered


def test_inventory_root_absent_when_root_missing(mod, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    rows = mod.inventory_root("gemini", missing)
    assert len(rows) == 1
    assert rows[0].entry_kind == "absent"
    assert rows[0].root_id == "gemini"
    assert rows[0].sha256 == ""


def test_inventory_root_detects_regular_directory(mod, tmp_path: Path) -> None:
    root = tmp_path / "skills"
    skill_dir = root / "some-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: some-skill\ndescription: test\n---\n# Some Skill\n",
        encoding="utf-8",
    )

    rows = mod.inventory_root("gemini", root)

    assert len(rows) == 1
    row = rows[0]
    assert row.slug == "some-skill"
    assert row.entry_kind == "regular"
    assert row.frontmatter_keys == ("name", "description")
    assert len(row.sha256) == 64


def test_inventory_root_detects_symlink(mod, tmp_path: Path) -> None:
    root = tmp_path / "skills"
    canonical = tmp_path / "canonical-skill"
    canonical.mkdir(parents=True)
    (canonical / "SKILL.md").write_text("---\nname: c\n---\n# C\n", encoding="utf-8")
    root.mkdir()
    (root / "linked-skill").symlink_to(canonical, target_is_directory=True)

    rows = mod.inventory_root("gemini", root)

    assert len(rows) == 1
    assert rows[0].entry_kind == "symlink"
    assert rows[0].slug == "linked-skill"


def test_inventory_root_skips_dotfiles_and_stray_files(mod, tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    (root / ".DS_Store").write_bytes(b"\x00")
    (root / "stray.txt").write_text("not a skill\n", encoding="utf-8")
    skill_dir = root / "real-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: real-skill\n---\n# Real\n", encoding="utf-8")

    rows = mod.inventory_root("gemini", root)

    assert [row.slug for row in rows] == ["real-skill"]


def test_inventory_root_missing_skill_md_has_no_digest_or_keys(mod, tmp_path: Path) -> None:
    root = tmp_path / "skills"
    (root / "empty-dir").mkdir(parents=True)

    rows = mod.inventory_root("gemini", root)

    assert len(rows) == 1
    assert rows[0].entry_kind == "regular"
    assert rows[0].sha256 == ""
    assert rows[0].frontmatter_keys == ()


def test_inventory_all_roots_covers_five_logical_roots(mod, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "HOME", tmp_path)
    rows = mod.inventory_all_roots()
    root_ids = {row.root_id for row in rows}
    assert root_ids == {"gemini", "claude", "codex", "agents", "antigravity"}
    # A fresh tmp_path has none of the five roots, so every row is a single
    # "absent" sentinel per root_id — and none of them may leak tmp_path.
    for row in rows:
        assert row.entry_kind == "absent"
        assert str(tmp_path) not in row.slug
        assert str(tmp_path) not in row.sha256


def test_inventory_all_roots_agents_and_antigravity_share_one_physical_root(
    mod, tmp_path, monkeypatch
) -> None:
    """Antigravity resolves to the shared agent root (Global Constraints);
    populating ~/.agents/skills must show up under BOTH root_ids."""
    monkeypatch.setattr(mod, "HOME", tmp_path)
    agents_skills = tmp_path / ".agents" / "skills" / "shared-skill"
    agents_skills.mkdir(parents=True)
    (agents_skills / "SKILL.md").write_text("---\nname: shared-skill\n---\n# Shared\n", encoding="utf-8")

    rows = mod.inventory_all_roots()

    agents_slugs = {row.slug for row in rows if row.root_id == "agents"}
    antigravity_slugs = {row.slug for row in rows if row.root_id == "antigravity"}
    assert agents_slugs == {"shared-skill"}
    assert antigravity_slugs == {"shared-skill"}


def test_audit_gemini_cli_flag_prints_render_inventory(mod, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(mod, "HOME", tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--audit-gemini"])

    exit_code = mod.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "gemini" in captured.out
    assert str(tmp_path) not in captured.out


# ── Task 0: Gemini verification and reconciliation P1 review fixes ──────────


def _canonical_code_review() -> Path:
    return ROOT / "bin" / "orama-system" / "skills" / "code-review"


def test_gemini_verify_reports_failure_when_not_reconciled(mod, tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / ".gemini" / "skills"
    (root / "code-review").mkdir(parents=True)
    (root / "code-review" / "SKILL.md").write_text("old Gemini card\n", encoding="utf-8")

    findings = mod.verify_gemini(root, tmp_path / ".gemini" / "skills-archive", {"code-review"})

    assert findings
    assert findings[0].status == "failed"
    assert findings[0].slug == "code-review"
    monkeypatch.setattr(mod, "HOME", tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--verify", "--only", "code-review"])
    assert mod.main() == 1
    captured = capsys.readouterr()
    assert "verification passed" not in captured.out
    assert "code-review" in captured.err


def test_gemini_verify_fails_on_missing_receipt(mod, tmp_path: Path) -> None:
    root = tmp_path / "gemini" / "skills"
    root.mkdir(parents=True)
    (root / "code-review").symlink_to(_canonical_code_review(), target_is_directory=True)

    findings = mod.verify_gemini(root, tmp_path / "archive", {"code-review"})

    assert findings
    assert findings[0].status == "failed"
    assert "code-review" in findings[0].detail


def test_gemini_verify_fails_on_mismatched_receipt(mod, tmp_path: Path) -> None:
    root, archive_parent = tmp_path / "gemini" / "skills", tmp_path / "archive"
    root.mkdir(parents=True)
    (root / "code-review").symlink_to(_canonical_code_review(), target_is_directory=True)
    receipt_dir = archive_parent / "batch-1" / "code-review"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "SKILL.md").write_text("archived source\n", encoding="utf-8")
    (archive_parent / "index.json").write_text(
        json.dumps({"code-review": "batch-1"}), encoding="utf-8"
    )
    (receipt_dir / ".receipt.json").write_text(
        json.dumps(
            {
                "slug": "code-review",
                "source_digest": "a" * 64,
                "archive_digest": "a" * 64,
                "final_target_kind": "symlink",
                "canonical_target": str(tmp_path / "wrong-target"),
            }
        ),
        encoding="utf-8",
    )

    findings = mod.verify_gemini(root, archive_parent, {"code-review"})

    assert findings
    assert findings[0].status == "failed"
    assert "code-review" in findings[0].detail


def test_oserror_with_unrelated_errno_propagates(mod, tmp_path: Path, monkeypatch) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"

    def disk_full(_target: Path, _source: Path) -> None:
        raise OSError(errno.ENOSPC, "disk full")

    monkeypatch.setattr(mod, "create_relative_link", disk_full)

    with pytest.raises(OSError) as raised:
        mod.reconcile_gemini(root, archive, {"code-review"})

    assert raised.value.errno == errno.ENOSPC
    assert not (root / "code-review" / "SKILL.md").exists()


def test_lock_contention_fails_cleanly(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    lock = mod.acquire_reconcile_lock(archive, root, {"code-review"})
    try:
        with pytest.raises(mod.ReconcileLockHeldError):
            mod.reconcile_gemini(root, archive, {"code-review"})
    finally:
        mod.release_reconcile_lock(lock)


def test_lock_terminated_owner_requires_guarded_recovery(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    archive.mkdir(parents=True)
    lock_path = archive / ".reconcile.lock"
    stale_payload = {"pid": 99999999, "started_at": "2026-08-14T00:00:00Z", "source_digest": "a" * 64}
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(mod.ReconcileLockHeldError):
        mod.reconcile_gemini(root, archive, {"code-review"})
    assert lock_path.exists()

    recovered = mod.force_unlock_gemini(archive, "code-review")

    assert recovered == stale_payload
    assert not lock_path.exists()


def test_second_run_over_same_slug_is_a_no_op(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    old_skill = root / "code-review" / "SKILL.md"
    old_skill.parent.mkdir(parents=True)
    old_skill.write_text("old Gemini card\n", encoding="utf-8")

    first = mod.reconcile_gemini(root, archive, {"code-review"})
    archived_before_second_run = sorted(archive.rglob("*"))
    second = mod.reconcile_gemini(root, archive, {"code-review"})

    assert first == [root / "code-review"]
    assert second == []
    assert sorted(archive.rglob("*")) == archived_before_second_run
    assert not (archive / ".reconcile.lock").exists()
