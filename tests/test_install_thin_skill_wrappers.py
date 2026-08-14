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
    assert not (root / "code-review" / "SKILL.md").exists()


def test_lock_contention_fails_cleanly(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    lock = mod.acquire_reconcile_lock(archive, root, {"code-review"})
    try:
        with pytest.raises(mod.ReconcileLockHeldError):
            mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))
    finally:
        mod.release_reconcile_lock(lock)


def test_lock_terminated_owner_requires_guarded_recovery(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini" / "skills", tmp_path / "archive" / "batch-1"
    archive.mkdir(parents=True)
    lock_path = archive / ".reconcile.lock"
    stale_payload = {"pid": 99999999, "started_at": "2026-08-14T00:00:00Z", "source_digest": "a" * 64}
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(mod.ReconcileLockHeldError):
        mod.reconcile_gemini(root, archive, {"code-review"}, lambda s: __import__('gemini_reconciliation').GeminiOwnership('orama', 'link', s, f'/fake/{s}/SKILL.md', 'none'))
    assert lock_path.exists()

    recovered = mod.force_unlock_gemini(archive, "code-review")

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
    assert not (archive / ".reconcile.lock").exists()


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
    assert not (archive / ".reconcile.lock").exists()


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
    assert not (archive / ".reconcile.lock").exists()


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

def test_audit_reports_antigravity_shared_root(mod, tmp_path: Path) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    antigravity.symlink_to(agents, target_is_directory=True)
    finding = mod.verify_antigravity_root(agents, antigravity)
    assert finding.status == "shared-root"
    assert finding.operator_next_action == "Record the finding; no setup action is needed."

def test_audit_reports_missing_antigravity_root_with_operator_action(mod, tmp_path: Path) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    finding = mod.verify_antigravity_root(agents, antigravity)
    assert finding.status == "missing"
    assert finding.operator_next_action == "Ask a human operator to approve or decline deferred Task 5a; do not create an Antigravity root in this plan."

def test_audit_reports_divergent_antigravity_root_with_operator_action(mod, tmp_path: Path) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    antigravity.mkdir()
    finding = mod.verify_antigravity_root(agents, antigravity)
    assert finding.status == "divergent"
    assert finding.operator_next_action == "Ask a human operator to inspect both root owners and approve deferred Task 5a only after resolving the intended topology."
