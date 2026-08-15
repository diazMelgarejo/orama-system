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
from types import ModuleType

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
    rel = mod.repo_relative(spec.canonical)
    assert rel and rel in text
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

    monkeypatch.setattr("gemini_reconciliation.create_relative_link", disk_full)

    with pytest.raises(OSError) as raised:
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))

    assert raised.value.errno == errno.ENOSPC
    # create_relative_link is mocked to raise before touching disk at all, so
    # "SKILL.md never got created" is vacuous by construction. The lock IS
    # real (not mocked): confirm the failure path still releases it rather
    # than leaving it held.
    assert not (root / ".reconcile.lock").exists()


def test_lock_contention_fails_cleanly(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    lock = mod.acquire_reconcile_lock(archive, root, {"code-review"})
    try:
        with pytest.raises(mod.ReconcileLockHeldError):
            mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))
    finally:
        mod.release_reconcile_lock(lock)


def test_lock_terminated_owner_requires_guarded_recovery(mod, tmp_path: Path) -> None:
    # Lock lives beside the live root (not the archive root) since the
    # timestamped archive root changes per invocation and the live root is
    # the thing that actually needs serializing.
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    root.mkdir(parents=True)
    lock_path = root / ".reconcile.lock"
    stale_payload = {"pid": 99999999, "started_at": "2026-08-14T00:00:00Z", "source_digest": "a" * 64}
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(mod.ReconcileLockHeldError):
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))
    assert lock_path.exists()

    recovered = mod.force_unlock_gemini(root, "code-review")

    assert recovered == stale_payload
    assert not lock_path.exists()


def test_second_run_over_same_slug_is_a_no_op(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    old_skill = root / "code-review" / "SKILL.md"
    old_skill.parent.mkdir(parents=True)
    old_skill.write_text("old Gemini card\n", encoding="utf-8")

    first = mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))
    archived_before_second_run = sorted(archive.rglob("*"))
    second = mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))

    assert first == [root / "code-review"]
    assert second == []
    assert sorted(archive.rglob("*")) == archived_before_second_run
    assert not (root / ".reconcile.lock").exists()


# ── P1-4: activation-rollback. The data-loss path the whole plan exists to
# prevent — archive succeeds, then every path that could install the
# replacement fails. The backup existing is not enough; the LIVE skill must
# still be usable, because Gemini reads the live root at runtime and a
# recoverable-but-absent skill is still a broken skill. Required by the
# codex-reviewer review synthesis (2026-08-14) as a P1 gate condition.


def _seed_live_skill(root: Path, slug: str = "code-review", body: str = "old Gemini card\n") -> Path:
    skill = root / slug
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    (skill / "references" / "notes.md").parent.mkdir(parents=True)
    (skill / "references" / "notes.md").write_text("reference body\n", encoding="utf-8")
    return skill


def test_live_skill_survives_when_every_activation_path_fails(
    mod, tmp_path: Path, monkeypatch
) -> None:
    """Symlink AND generated-wrapper both fail after a successful archive."""
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    _seed_live_skill(root)

    def refuse_symlink(_target: Path, _source: Path) -> None:
        raise OSError(errno.EPERM, "symlinks not permitted")

    def refuse_wrapper(_target: Path, _source: Path) -> None:
        raise OSError(errno.EROFS, "read-only file system")

    monkeypatch.setattr("gemini_reconciliation.create_relative_link", refuse_symlink)
    monkeypatch.setattr("gemini_reconciliation.write_generated_wrapper", refuse_wrapper)

    with pytest.raises(OSError) as raised:
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))

    # Positive outcome, not just "no crash": we got PAST the archive step, so
    # this genuinely exercises post-archive failure rather than an early abort.
    assert raised.value.errno == errno.EROFS
    assert (archive / "code-review" / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"

    # The live skill is intact, still a real directory, with both files.
    live = root / "code-review"
    assert live.is_dir() and not live.is_symlink()
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"
    assert (live / "references" / "notes.md").read_text(encoding="utf-8") == "reference body\n"

    # No staging or rollback debris left behind in the user's skill root.
    assert not list(root.glob(".*reconcile-staging"))
    assert not list(root.glob(".*reconcile-rollback"))
    assert not (root / ".reconcile.lock").exists()


def test_live_skill_is_restored_when_the_swap_fails_after_archive(
    mod, tmp_path: Path, monkeypatch
) -> None:
    """The narrowest window: staging built, live moved aside, then the final
    rename fails. Without the rollback restore the live skill is simply gone."""
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    _seed_live_skill(root)

    real_replace = mod.os.replace

    def fail_installing_stage(src, dst, *args, **kwargs):
        # Fail only the staging -> live install; let the rollback restore work,
        # otherwise we would be testing that os.replace is broken, not that
        # reconcile_gemini recovers.
        if ".reconcile-staging" in str(src):
            raise OSError(errno.EIO, "input/output error installing staged replacement")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(mod.os, "replace", fail_installing_stage)

    with pytest.raises(OSError) as raised:
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))

    assert raised.value.errno == errno.EIO
    assert (archive / "code-review" / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"

    live = root / "code-review"
    assert live.is_dir() and not live.is_symlink()
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"
    assert (live / "references" / "notes.md").read_text(encoding="utf-8") == "reference body\n"
    assert not list(root.glob(".*reconcile-rollback"))
    assert not (root / ".reconcile.lock").exists()


def test_live_skill_untouched_when_the_initial_rollback_move_fails(
    mod, tmp_path: Path, monkeypatch
) -> None:
    """The narrowest window on the OTHER side of P1-4: staging is built, but
    the very FIRST protective move (live -> .reconcile-rollback) itself
    fails. Before the fix, the except handler assumed that move had already
    succeeded and unconditionally deleted the still-intact live directory,
    then masked the real error by trying to replace a rollback that was
    never created (raising a confusing FileNotFoundError instead of the
    actual underlying OSError)."""
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    _seed_live_skill(root)

    real_replace = mod.os.replace

    def fail_moving_live_aside(src, dst, *args, **kwargs):
        if ".reconcile-rollback" in str(dst):
            raise OSError(errno.EPERM, "operation not permitted moving live aside")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(mod.os, "replace", fail_moving_live_aside)

    with pytest.raises(OSError) as raised:
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))

    # The REAL error must surface -- not a masking FileNotFoundError from
    # trying to restore a rollback directory that was never created.
    assert raised.value.errno == errno.EPERM

    live = root / "code-review"
    assert live.is_dir() and not live.is_symlink()
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"
    assert (live / "references" / "notes.md").read_text(encoding="utf-8") == "reference body\n"
    assert not list(root.glob(".*reconcile-rollback"))
    assert not (root / ".reconcile.lock").exists()


def test_reconcile_does_not_silently_skip_a_corrupt_receipt(mod, tmp_path: Path) -> None:
    """A truncated or otherwise invalid .receipt.json must not be trusted as
    proof reconciliation completed -- existence alone is not enough. Before
    the fix, existence-only checking silently returned [] even though the
    live directory was still the plain, unreconciled original and the
    archive/receipt pairing was never actually validated."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    _seed_live_skill(root)

    archive_skill = archive / "code-review"
    archive_skill.mkdir(parents=True)
    (archive_skill / ".receipt.json").write_text("not valid json{{{", encoding="utf-8")

    ownership = gr.GeminiOwnership("orama", "link", "code-review", "/fake/code-review/SKILL.md", "none")

    # Must NOT silently return [] -- an unparseable receipt cannot be
    # trusted, so this must surface loudly (an existing archive with no
    # trustworthy receipt is a genuine conflict) rather than pretend the
    # slug is already done.
    with pytest.raises(FileExistsError):
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: ownership)


def test_force_unlock_recovers_from_corrupt_lock_payload(mod, tmp_path: Path, capsys) -> None:
    """A lock file can be left as truncated/corrupt JSON if the writer was
    killed between O_CREAT|O_EXCL succeeding and the payload write
    completing. force_unlock_gemini must still be able to clear it: a
    corrupt payload can never belong to a currently-running, well-behaved
    writer (a normal exit always leaves well-formed JSON), so corruption is
    itself sufficient evidence the writer crashed."""
    root = tmp_path / "gemini" / "skills"
    root.mkdir(parents=True)
    lock_path = root / ".reconcile.lock"
    lock_path.write_text("{not valid json", encoding="utf-8")

    result = mod.force_unlock_gemini(root, "code-review")

    assert result == {}
    assert not lock_path.exists()
    assert "corrupt" in capsys.readouterr().err


def test_adapter_reconciliation_passes_verify_both_directions(mod, tmp_path: Path) -> None:
    """The 'link' action already has end-to-end verify coverage
    (test_fresh_install_passes_verify_both_directions); the adapter/
    cross-repo-adapter branch of verify_gemini's receipt-matching logic had
    none, in either the pass or the fail direction."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    ownership = gr.GeminiOwnership("orama", "adapter", "orama-system", "bin/orama-system/SKILL.md", "none")

    findings_before = mod.verify_gemini(root, archive, {"orama-system"})
    assert findings_before and findings_before[0].status == "failed"

    mod.reconcile_gemini(root, archive, {"orama-system"}, lambda s: ownership)
    findings_after = mod.verify_gemini(root, archive, {"orama-system"})
    assert findings_after == []


def test_validate_frontmatter_raises_on_malformed_yaml(mod) -> None:
    """A bare `except Exception: parsed = {}` used to silently turn genuinely
    malformed YAML into 'no frontmatter', indistinguishable from a skill
    card that legitimately had none. Malformed frontmatter must be reported,
    not silently downgraded."""
    import gemini_reconciliation as gr
    source = "---\nname: [unterminated\n---\n# Broken\n"
    with pytest.raises(ValueError, match="malformed YAML frontmatter"):
        gr._validate_frontmatter(source)


def test_validate_frontmatter_tolerates_crlf_line_endings(mod) -> None:
    """A CRLF-terminated file (e.g. authored on Windows) with otherwise
    valid frontmatter must still be recognized -- the \\n--- fence regex
    used to require a literal LF and silently treated CRLF frontmatter as
    absent."""
    import gemini_reconciliation as gr
    source = "---\r\nname: crlf-skill\r\ndescription: test\r\n---\r\n# CRLF\r\n"
    frontmatter = gr._validate_frontmatter(source)
    assert "name: crlf-skill" in frontmatter
    assert "description: test" in frontmatter


def test_verify_gemini_fails_when_symlink_target_no_longer_exists(mod, tmp_path: Path) -> None:
    """Path.resolve() is non-strict: a symlink whose canonical target has
    since been deleted still resolves (syntactically) to the same string,
    so a plain string comparison alone would report a dangling link as
    passing verification."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    canonical = tmp_path / "canonical" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("canonical\n", encoding="utf-8")
    ownership = gr.GeminiOwnership("orama", "link", "orama-afrp", str(canonical), "none")

    mod.reconcile_gemini(root, archive, {"orama-afrp"}, lambda s: ownership)
    assert mod.verify_gemini(root, archive, {"orama-afrp"}) == []

    canonical.unlink()
    findings = mod.verify_gemini(root, archive, {"orama-afrp"})

    assert findings
    assert findings[0].status == "failed"
    assert "no longer exists" in findings[0].detail


def test_audit_reports_antigravity_shared_root(mod: ModuleType, tmp_path: Path) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    antigravity.symlink_to(agents, target_is_directory=True)
    assert mod.verify_antigravity_root(agents, antigravity).status == "shared-root"


def test_audit_reports_missing_antigravity_root_with_operator_action(
    mod: ModuleType, tmp_path: Path
) -> None:
    finding = mod.verify_antigravity_root(tmp_path / "agents", tmp_path / "antigravity")
    assert finding.status == "missing"
    assert finding.operator_next_action == "Ask a human operator to approve or decline deferred Task 5a; do not create an Antigravity root in this plan."


def test_verify_antigravity_root_reports_unreadable_on_oserror(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permission error or broken symlink chain while resolving
    antigravity_root must not be silently folded into 'divergent' (a real
    topology mismatch) -- that mislabels an unreadable/indeterminate path as
    something it is not."""
    shared = tmp_path / "agents"
    antigravity = tmp_path / "antigravity"
    shared.mkdir()
    antigravity.symlink_to(shared, target_is_directory=True)

    real_resolve = Path.resolve

    def raise_on_antigravity(self, *args, **kwargs):
        if self == antigravity:
            raise OSError(errno.ELOOP, "too many levels of symbolic links")
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", raise_on_antigravity)

    finding = mod.verify_antigravity_root(shared, antigravity)

    assert finding.status == "unreadable"
    assert "too many levels of symbolic links" in finding.detail


def test_audit_reports_divergent_antigravity_root_with_operator_action(
    mod: ModuleType, tmp_path: Path
) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    antigravity.mkdir()
    finding = mod.verify_antigravity_root(agents, antigravity)
    assert finding.status == "divergent"
    assert finding.operator_next_action == "Ask a human operator to inspect both root owners and approve deferred Task 5a only after resolving the intended topology."


def test_audit_antigravity_root_reports_missing_when_no_root_is_configured(
    mod: ModuleType, tmp_path: Path
) -> None:
    finding = mod.audit_antigravity_root(tmp_path / "agents", None)

    assert finding.status == "missing"
    assert "No Antigravity skills root" in finding.detail


def test_audit_antigravity_cli_is_read_only_and_reports_missing(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(mod, "HOME", tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--audit-antigravity"])

    exit_code = mod.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "missing:" in captured.out
    assert "No Antigravity skills root" in captured.out
    assert not list(tmp_path.iterdir())

def test_reconcile_never_replaces_gstack_upgrade(mod, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="preserve-external"):
        mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"gstack-upgrade"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('gstack', 'preserve-external', 'gstack-upgrade', '', 'external'))


def test_reconcile_never_replaces_skillify(mod, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="preserve-external"):
        mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"skillify"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('gstack', 'preserve-external', 'skillify', '', 'external'))

def test_reconcile_rejects_unknown_frontmatter_key_for_adapter(mod, tmp_path: Path) -> None:
    root = tmp_path / "gemini"
    skill = root / "orama-system" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: orama-system\nunsupported: true\n---\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported frontmatter"):
        mod.reconcile_gemini(root, tmp_path / "archive", {"orama-system"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'adapter', 'orama-system', '/path/SKILL.md', 'validated'))

def test_reconcile_reports_the_exact_unknown_frontmatter_key(mod, tmp_path: Path) -> None:
    root = tmp_path / "gemini"
    skill = root / "orama-system" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: orama-system\nunsupported: true\n---\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unsupported frontmatter key: unsupported"):
        mod.reconcile_gemini(root, tmp_path / "archive", {"orama-system"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'adapter', 'orama-system', '/path/SKILL.md', 'validated'))

def test_reconcile_falls_back_to_wrapper_when_symlink_fails(mod, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("gemini_reconciliation.create_relative_link", lambda target, source: (_ for _ in ()).throw(OSError(errno.EPERM, "links disabled")))
    root = tmp_path / "gemini"
    skill = root / "code-review" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("old", encoding="utf-8")
    changed = mod.reconcile_gemini(root, tmp_path / "archive", {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', 'code-review', f'/fake/code-review/SKILL.md', 'none'))
    assert changed == [root / "code-review"]
    assert (root / "code-review" / "SKILL.md").is_file()

def test_orama_gstack_adapter_targets_gstack_gbrain(mod) -> None:
    import gemini_reconciliation
    ownership = gemini_reconciliation.GeminiOwnership("orama", "adapter", "orama-gstack", "bin/orama-system/gstack-gbrain/SKILL.md", "validated")
    text = gemini_reconciliation.gemini_adapter(ownership)
    assert "bin/orama-system/gstack-gbrain/SKILL.md" in text
    assert "bin/orama-system/gstack/SKILL.md" not in text

def test_code_review_reconciliation_drops_glm_fallback(mod, tmp_path: Path) -> None:
    root = tmp_path / "gemini"
    skill = root / "code-review" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("GLM-5.2 Fallback content", encoding="utf-8")
    canonical = tmp_path / "canonical" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("Canonical content", encoding="utf-8")
    changed = mod.reconcile_gemini(root, tmp_path / "archive", {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', 'code-review', str(canonical), 'none'))
    assert all("GLM-5.2 Fallback" not in p.read_text(encoding="utf-8") for p in changed if p.is_file())
    # Positive assertion, not just absence: the symlinked entry must
    # actually resolve to and read as the canonical file's real content.
    live = root / "code-review"
    assert live.is_symlink() and live.resolve() == canonical.resolve()
    assert live.read_text(encoding="utf-8") == "Canonical content"

def test_perpetua_wrapper_uses_environment_root_not_caller_repo(mod) -> None:
    import gemini_reconciliation
    ownership = gemini_reconciliation.GeminiOwnership("perpetua", "adapter", "perpetua-config", "$PERPETUA_TOOLS_PATH/config/SKILL.md", "validated")
    text = gemini_reconciliation.cross_repo_wrapper(ownership)
    assert '"$PERPETUA_TOOLS_PATH/config/SKILL.md"' in text
    assert "git rev-parse --show-toplevel" not in text

def test_perpetua_wrapper_explains_missing_root(mod) -> None:
    import gemini_reconciliation
    ownership = gemini_reconciliation.GeminiOwnership("perpetua", "adapter", "perpetua-tools", "$PERPETUA_TOOLS_PATH/SKILL.md", "validated")
    assert "PERPETUA_TOOLS_PATH is not set" in gemini_reconciliation.cross_repo_wrapper(ownership)


# ── Post-consolidation findings (codex-reviewer, fc384e6b review + independent
# confirmation, board records 1432/1440): four issues that survive the
# consolidated tip (824bb503). Bug 4 (adapter/cross-repo-adapter verify) and
# the duplicate-shadowing tests were already closed upstream by agy/codex;
# these four were not.


def test_fresh_install_digest_is_self_consistent(mod, tmp_path: Path) -> None:
    """Bug 5: _tree_sha256 must not return a different sentinel for 'path does
    not exist' than it returns for 'path exists but is empty' — reconcile
    writes the former as the receipt digest, verify recomputes the latter
    against the archive dir _write_receipt itself creates, and the two must
    describe the same 'no content' state or every fresh install fails verify."""
    import gemini_reconciliation as gr
    missing = tmp_path / "does-not-exist"
    empty = tmp_path / "empty-dir"
    empty.mkdir()
    assert gr._tree_sha256(missing) == gr._tree_sha256(empty)


def test_fresh_install_passes_verify_both_directions(mod, tmp_path: Path) -> None:
    """The end-to-end version of the digest bug: a slug that never existed in
    the Gemini root before reconciliation must still pass verify_gemini once
    reconciled, and an unreconciled fresh root must still fail it."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini", tmp_path / "archive" / "batch-1"
    ownership = gr.GeminiOwnership("orama", "link", "orama-afrp", str(tmp_path / "canonical" / "SKILL.md"), "none")
    canonical = tmp_path / "canonical" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("canonical\n", encoding="utf-8")

    findings_before = mod.verify_gemini(root, archive, {"orama-afrp"})
    assert findings_before and findings_before[0].status == "failed"

    mod.reconcile_gemini(root, archive, {"orama-afrp"}, lambda s: ownership)
    findings_after = mod.verify_gemini(root, archive, {"orama-afrp"})
    assert findings_after == []


def test_lock_scoped_to_live_root_not_timestamped_archive(mod, tmp_path: Path) -> None:
    """Bug 1: two invocations with DIFFERENT --archive-root values (the real
    CLI timestamps a fresh one per run) against the SAME live root must
    contend on the same lock, not acquire two independent ones."""
    root = tmp_path / "gemini" / "skills"
    archive_a = tmp_path / "archive" / "batch-a"
    archive_b = tmp_path / "archive" / "batch-b"
    lock = mod.acquire_reconcile_lock(archive_a, root, {"code-review"})
    try:
        with pytest.raises(mod.ReconcileLockHeldError):
            mod.acquire_reconcile_lock(archive_b, root, {"code-review"})
    finally:
        mod.release_reconcile_lock(lock)


def test_link_target_anchored_to_repo_root_not_caller_cwd(mod, tmp_path: Path, monkeypatch) -> None:
    """Bug 2: a manifest canonical_path is repo-relative (e.g.
    'bin/orama-system/skills/code-review/SKILL.md'). The real symlink must
    resolve against the repo root regardless of the process's CWD at
    invocation time -- not accidentally agree with itself only because
    creation and verification happened to run from the same directory."""
    import gemini_reconciliation as gr

    repo_root = tmp_path / "repo"
    canonical_dir = repo_root / "bin" / "orama-system" / "skills" / "code-review"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "SKILL.md").write_text("canonical\n", encoding="utf-8")

    other_cwd = tmp_path / "somewhere-else-entirely"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    ownership = gr.GeminiOwnership(
        "orama", "link", "code-review", "bin/orama-system/skills/code-review/SKILL.md", "none"
    )
    mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: ownership, canonical_root=repo_root)

    live = root / "code-review"
    assert live.is_symlink()
    assert live.resolve() == canonical_dir / "SKILL.md"


def test_receipt_write_failure_restores_previously_live_skill(mod, tmp_path: Path, monkeypatch) -> None:
    """Bug 3: if _write_receipt raises AFTER the stage->live swap succeeds
    (e.g. a corrupt index.json), the live directory must be restored to its
    PRE-reconciliation state, not left as an unreceipted, unverifiable
    mutation. A receipt is the only proof reconciliation happened; a swap
    without one is exactly the unrecoverable state this plan exists to
    prevent."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    old = root / "code-review"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("old Gemini card\n", encoding="utf-8")

    archive.mkdir(parents=True)
    (archive.parent / "index.json").write_text("not valid json{{{", encoding="utf-8")

    ownership = gr.GeminiOwnership("orama", "link", "code-review", "/fake/code-review/SKILL.md", "none")
    with pytest.raises(ValueError, match="archive index is invalid JSON"):
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: ownership)

    live = root / "code-review"
    assert live.is_dir() and not live.is_symlink()
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "old Gemini card\n"


def test_receipt_write_failure_removes_fresh_install(mod, tmp_path: Path) -> None:
    """Symmetric case: nothing existed at this slug before, the swap
    succeeds, then the receipt write fails. The correct end state is 'as if
    reconciliation never ran' -- no half-installed, unreceipted skill."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    archive.mkdir(parents=True)
    (archive.parent / "index.json").write_text("not valid json{{{", encoding="utf-8")

    ownership = gr.GeminiOwnership("orama", "link", "code-review", "/fake/code-review/SKILL.md", "none")
    with pytest.raises(ValueError, match="archive index is invalid JSON"):
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: ownership)

    live = root / "code-review"
    # .exists() alone follows a dangling symlink and reports False even when
    # the symlink entry is still on disk -- check both, or this assertion
    # passes for the wrong reason (a link_target that happens not to exist
    # rather than a genuinely absent slug).
    assert not live.is_symlink() and not live.exists()


def test_second_run_over_same_slug_is_a_no_op_for_adapter_action(mod, tmp_path: Path) -> None:
    """The 'link' action has an early-exit for 'already correctly pointed at
    the canonical target'; adapter/cross-repo-adapter actions have no
    filesystem-target equivalent to compare against (their live entry is
    generated content, not a symlink), so idempotence for them must come
    from the archive receipt instead -- a receipt at this exact archive_root
    is proof this slug's reconciliation into this batch already completed."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    ownership = gr.GeminiOwnership("orama", "adapter", "orama-system", "bin/orama-system/SKILL.md", "none")

    first = mod.reconcile_gemini(root, archive, {"orama-system"}, lambda s: ownership)
    archived_before_second_run = sorted(archive.rglob("*"))
    second = mod.reconcile_gemini(root, archive, {"orama-system"}, lambda s: ownership)

    assert first == [root / "orama-system"]
    assert second == []
    assert sorted(archive.rglob("*")) == archived_before_second_run
    assert not (root / ".reconcile.lock").exists()


def test_adapter_idempotence_does_not_compare_against_its_own_generated_output(
    mod, tmp_path: Path
) -> None:
    """The receipt-based check must not regenerate 'expected' output from
    whatever text is currently live and then compare it against itself --
    on a second run the live SKILL.md IS the generated adapter body, not
    the original Gemini source, so that comparison is tautological. Forcing
    the receipt to look wrong (a different archive_root, so no receipt
    exists there) must still trigger a full re-run rather than a false
    idempotent skip, proving the check depends on the receipt, not on
    re-deriving text from the live file."""
    import gemini_reconciliation as gr
    root = tmp_path / "gemini" / "skills"
    archive_a = tmp_path / "archive" / "batch-a"
    archive_b = tmp_path / "archive" / "batch-b"
    ownership = gr.GeminiOwnership("orama", "adapter", "orama-system", "bin/orama-system/SKILL.md", "none")

    mod.reconcile_gemini(root, archive_a, {"orama-system"}, lambda s: ownership)
    second = mod.reconcile_gemini(root, archive_b, {"orama-system"}, lambda s: ownership)

    # Different archive_root, no receipt there yet -- must actually re-run
    # (and re-archive), not silently skip because the live content already
    # "looks like" a correctly generated adapter.
    assert second == [root / "orama-system"]
    assert (archive_b / "orama-system" / ".receipt.json").is_file()


def test_index_json_write_is_atomic_against_a_mid_write_crash(mod, tmp_path: Path, monkeypatch) -> None:
    """_write_receipt's index.json update must not stream JSON directly into
    the real file: a process killed mid-write leaves index.json truncated
    and unparseable, which is exactly the kind of corruption archive-first
    was designed to prevent, just one file over. The index must be built in
    a temp file and atomically swapped in with os.replace, so a crash during
    the write leaves the ORIGINAL index.json (or none, on the first-ever
    write) completely untouched -- never a half-written file."""
    import gemini_reconciliation as gr
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    old = root / "code-review"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("v1\n", encoding="utf-8")

    ownership = gr.GeminiOwnership("orama", "link", "code-review", "/fake/code-review/SKILL.md", "none")
    mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: ownership)

    index_path = archive.parent / "index.json"
    original_index_bytes = index_path.read_bytes()

    real_write_text = Path.write_text

    def crash_on_index_write(self, data, *args, **kwargs):
        if self.name in ("index.json", ".index.json.tmp"):
            # A real kill-mid-write leaves PARTIAL bytes on disk, not zero --
            # a mock that raises before touching the file at all would pass
            # trivially whether or not the write is atomic. Write half the
            # intended content directly to whatever path is targeted, then
            # crash: this hits index.json for the OLD non-atomic
            # implementation (corrupting the real file) and hits the temp
            # file for the FIXED implementation (real index.json untouched,
            # since os.replace of the temp file never runs).
            with open(self, "w", encoding="utf-8") as fh:
                fh.write(data[: len(data) // 2])
            raise OSError("simulated crash mid-write")
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", crash_on_index_write)

    old2 = root / "orama-afrp"
    old2.mkdir(parents=True)
    (old2 / "SKILL.md").write_text("v1\n", encoding="utf-8")
    ownership2 = gr.GeminiOwnership("orama", "link", "orama-afrp", "/fake/orama-afrp/SKILL.md", "none")
    with pytest.raises(OSError, match="simulated crash mid-write"):
        mod.reconcile_gemini(root, archive, {"orama-afrp"}, lambda s: ownership2)

    assert index_path.read_bytes() == original_index_bytes
    assert not list(archive.parent.glob(".index.json.tmp*"))


def test_cli_anchors_gemini_link_targets_to_repo_root_not_workspace_root(
    mod, tmp_path: Path, monkeypatch
) -> None:
    """ROOT is the WORKSPACE parent (one level above this repo, used for
    workspace-relative CANONICAL_SKILLS entries like
    'orama-system/bin/orama-system/...'). The Gemini ownership manifest's
    canonical_path values are REPO-relative instead
    ('bin/orama-system/skills/code-review/SKILL.md', no leading
    'orama-system/'), so the CLI's reconcile call site must anchor them
    against REPO_ROOT, not ROOT -- anchoring against ROOT resolves one
    directory too high whenever this script runs without the workspace
    wrapper nesting, which is every isolated worktree, found via a real
    sandbox proof against actual data (verify_gemini's dangling-symlink
    check caught reconcile silently writing symlinks one level too high;
    the old self-consistency-only verify check could not, since write and
    read both used the same wrong anchor and agreed with each other).

    Simulate the exact broken topology: a repo root with NO workspace
    wrapper above it (ROOT and REPO_ROOT necessarily differ), then prove the
    live symlink actually resolves under REPO_ROOT.
    """
    repo_root = tmp_path / "repo-with-no-workspace-wrapper"
    canonical_dir = repo_root / "bin" / "orama-system" / "skills" / "code-review"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "SKILL.md").write_text("canonical\n", encoding="utf-8")

    gemini_root = tmp_path / "gemini" / "skills"
    archive_root = tmp_path / "archive" / "batch-1"
    manifest_path = tmp_path / "gemini-skill-ownership.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": {
                    "code-review": {
                        "owner": "orama",
                        "action": "link",
                        "canonical_slug": "code-review",
                        "canonical_path": "bin/orama-system/skills/code-review/SKILL.md",
                        "metadata_policy": "none",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "HOME", tmp_path)
    # ROOT stays whatever this test process's real workspace happens to be;
    # REPO_ROOT is set to the topology-mismatched repo above, with nothing
    # one level up from it. If the CLI call site ever regresses to using
    # ROOT again, the symlink will resolve outside repo_root entirely and
    # the assertion below catches it.
    monkeypatch.setattr(mod, "REPO_ROOT", repo_root)
    import gemini_reconciliation as gr

    monkeypatch.setattr(
        mod,
        "load_gemini_ownership",
        lambda _path: {
            "code-review": gr.GeminiOwnership(
                "orama", "link", "code-review", "bin/orama-system/skills/code-review/SKILL.md", "none"
            )
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--reconcile-gemini",
            "--gemini-root",
            str(gemini_root),
            "--archive-root",
            str(archive_root),
            "--only",
            "code-review",
        ],
    )

    assert mod.main() == 0

    live = gemini_root / "code-review"
    assert live.is_symlink()
    assert live.resolve() == canonical_dir / "SKILL.md"
    # The decisive check: the resolved target must live UNDER repo_root.
    # Anchoring against the wrong (workspace) root would resolve outside it
    # entirely -- exactly the failure the real sandbox proof caught.
    assert repo_root in live.resolve().parents


def test_repo_root_is_computed_five_parents_up_not_monkeypatched(mod) -> None:
    """The test above monkeypatches mod.REPO_ROOT directly, which proves the
    CLI USES REPO_ROOT correctly but not that REPO_ROOT is COMPUTED
    correctly -- a regression from parents[5] back to parents[6] (the exact
    bug this branch fixed) would silently survive that test, because the
    monkeypatch bypasses the real arithmetic entirely. Adversarial review
    (Agnes, 2026-08-15) found this gap via mutation testing: M4 (revert to
    parents[6]) survived against the monkeypatched test. This test checks
    the literal computation with no monkeypatching, so the same mutation
    kills it directly."""
    script = (
        Path(__file__).resolve().parents[1]
        / "bin"
        / "orama-system"
        / "skills"
        / "skillify"
        / "scripts"
        / "install_thin_skill_wrappers.py"
    )
    assert mod.REPO_ROOT == script.resolve().parents[5]
    # REPO_ROOT is one level BELOW ROOT: ROOT is the workspace parent
    # (containing this repo and Perpetua-Tools as siblings, parents[6]);
    # REPO_ROOT is this repo's own root, one level inside it (parents[5]).
    # If this relationship ever breaks, the workspace-layout assumption
    # both constants depend on has changed and needs re-deriving together,
    # not silently.
    assert mod.REPO_ROOT.parent == mod.ROOT
