"""Tests for the thin Hermes wrapper installer: install and refresh, managed detection, text, verify."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (
    ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "install_hermes_thin_skills.py"
)


@pytest.fixture
def installer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> types.ModuleType:
    """
    Load the installer module with its skill and harness paths redirected to temporary directories.
    
    Parameters:
    	monkeypatch (pytest.MonkeyPatch): Fixture used to isolate module state and paths.
    	tmp_path (Path): Temporary directory for the installer’s skill and harness files.
    
    Returns:
    	types.ModuleType: The dynamically loaded installer module.
    """
    spec = importlib.util.spec_from_file_location("hermes_thin_installer", INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERMES_SKILLS", tmp_path / "pt-orama")
    monkeypatch.setattr(module, "HERMES_HARNESS_ROOT", tmp_path / "hermes-harness")
    return module


def _target(installer, slug: str) -> Path:
    """Return the path where the installer writes the wrapper for *slug*."""
    return installer.HERMES_SKILLS / installer.hermes_local_dir(slug) / "SKILL.md"


def test_install_preserves_unmanaged_wrapper(installer, capsys):
    """A user-owned wrapper without the managed marker is left untouched."""
    target = _target(installer, "council")
    target.parent.mkdir(parents=True)
    original = "---\nname: personal-council\n---\n\n# Personal Council\n"
    target.write_text(original, encoding="utf-8")

    written = installer.install()

    assert target.read_text(encoding="utf-8") == original
    assert target not in written
    assert f"skipped unmanaged wrapper: {target}" in capsys.readouterr().out
    assert f"unmanaged wrapper preserved: {target}" in installer.verify()


def test_install_refreshes_managed_wrapper(installer):
    """A stale managed wrapper is rewritten with the generated text."""
    target = _target(installer, "review")
    target.parent.mkdir(parents=True)
    target.write_text("---\ncreated_by: agent\n---\n\nstale\n", encoding="utf-8")

    written = installer.install()
    review = next(spec for spec in installer.WRAPPERS if spec.slug == "pt-orama-review")

    assert target in written
    assert target.read_text(encoding="utf-8") == installer.wrapper_text(review)
    assert installer.verify() == []


def test_dry_run_reports_unmanaged_wrapper_without_writing(installer, capsys):
    """A dry run names the unmanaged wrapper it would skip."""
    target = _target(installer, "delegate")
    target.parent.mkdir(parents=True)
    target.write_text("# User-owned delegate\n", encoding="utf-8")

    assert installer.install(dry_run=True) == []

    output = capsys.readouterr().out
    assert f"would skip unmanaged wrapper: {target}" in output
    assert target.read_text(encoding="utf-8") == "# User-owned delegate\n"


# ── is_managed_wrapper ────────────────────────────────────────────────────────

def test_is_managed_wrapper_nonexistent_file(installer, tmp_path):
    """A missing file is not a managed wrapper."""
    assert installer.is_managed_wrapper(tmp_path / "no-such-file.md") is False


def test_is_managed_wrapper_no_frontmatter(installer, tmp_path):
    """The marker outside YAML frontmatter does not make a managed wrapper."""
    f = tmp_path / "plain.md"
    f.write_text("# Just a heading\ncreated_by: agent\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


def test_is_managed_wrapper_marker_after_closing_fence(installer, tmp_path):
    """created_by: agent after the closing --- must NOT trigger managed detection."""
    f = tmp_path / "not-managed.md"
    f.write_text("---\nname: my-skill\n---\n\ncreated_by: agent\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


def test_is_managed_wrapper_valid(installer, tmp_path):
    """A file with the marker inside its frontmatter is a managed wrapper."""
    f = tmp_path / "managed.md"
    f.write_text("---\nname: council\ncreated_by: agent\n---\n\n# body\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is True


def test_is_managed_wrapper_empty_file(installer, tmp_path):
    """An empty file is not a managed wrapper."""
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


# ── wrapper_text ──────────────────────────────────────────────────────────────

def test_wrapper_text_contains_slug_and_canonical(installer):
    """Generated text carries the slug, canonical path and purpose."""
    spec = installer.WRAPPERS[0]  # pt-orama-council
    text = installer.wrapper_text(spec)
    assert f"name: {spec.slug}" in text
    assert spec.canonical in text
    assert spec.purpose in text


def test_wrapper_text_contains_required_readiness_strings(installer):
    """Every core wrapper carries the readiness canaries and marker."""
    for spec in installer.WRAPPERS:
        text = installer.wrapper_text(spec)
        assert "HERMES_READY" in text
        assert "AGY_READY" in text
        assert "thin local Hermes" in text
        assert "created_by: agent" in text


def test_wrapper_text_all_core_wrappers(installer):
    """The core and optional wrapper sets are exactly the expected slugs."""
    slugs = {spec.slug for spec in installer.WRAPPERS}
    assert slugs == {
        "pt-hardware-policy",
        "pt-orama-council",
        "pt-orama-review",
        "pt-orama-delegate",
        "lan-peer-self-talk",
        "windows-hermes-setup",
    }
    optional = {spec.slug for spec in installer.OPTIONAL_WRAPPERS}
    assert optional == {"pt-orama-lesson-mining"}


def test_wrapper_text_carries_the_git_safety_rules(installer):
    """Every generated wrapper forbids unprompted git clean and branch switching on a dirty tree."""
    for spec in installer.WRAPPERS:
        text = installer.wrapper_text(spec)
        assert "git clean -fd" in text
        assert "git clean -fdx" in text
        assert "uncommitted working-tree changes" in text
        assert "Stay on the current branch" in text


def test_wrapper_text_carries_the_refresh_rule(installer):
    """Every generated wrapper says a refresh rewrites it, so patched-in workflow content is not durable."""
    for spec in installer.WRAPPERS:
        text = installer.wrapper_text(spec)
        assert "## Refresh rule" in text
        assert "rewrites managed wrappers" in text
        assert "not durable here" in text
        assert text.index("## Response Shape") < text.index("## Refresh rule")


def test_install_gives_an_older_managed_wrapper_the_new_sections(installer):
    """A managed wrapper written before these rules existed gains them on the next install."""
    target = _target(installer, "windows-hermes-setup")
    target.parent.mkdir(parents=True)
    target.write_text("---\nname: windows-hermes-setup\ncreated_by: agent\n---\n\nold body\n", encoding="utf-8")

    installer.install()

    text = target.read_text(encoding="utf-8")
    assert "old body" not in text
    assert "## Refresh rule" in text
    assert "git clean -fdx" in text


# ── install ───────────────────────────────────────────────────────────────────

def test_optional_wrapper_not_installed_by_default(installer):
    """The optional lesson-mining wrapper is not installed by default."""
    installer.install()
    assert not (installer.HERMES_SKILLS / "lesson-mining" / "SKILL.md").is_file()


def test_optional_wrapper_installed_with_flag(installer):
    """include_optional installs the optional wrapper."""
    installer.install(include_optional=True)
    assert (installer.HERMES_SKILLS / "lesson-mining" / "SKILL.md").is_file()


def test_install_fresh_creates_all_wrappers(installer):
    """A fresh install writes every core wrapper plus the harness redirect."""
    written = installer.install()
    assert len(written) == len(installer.WRAPPERS) + 1  # +1 for harness redirect (install_harness_redirect)
    for spec in installer.WRAPPERS:
        target = _target(installer, spec.slug)
        assert target.is_file()
    harness = installer.HERMES_HARNESS_ROOT / "SKILL.md"
    assert harness.is_file()
    assert harness in written


def test_install_creates_description_md(installer):
    """A fresh install writes DESCRIPTION.md naming PT-orama and orama-system."""
    installer.install()
    desc = installer.HERMES_SKILLS / "DESCRIPTION.md"
    assert desc.is_file()
    content = desc.read_text(encoding="utf-8")
    assert "PT-orama" in content
    assert "orama-system" in content


def test_install_dry_run_prints_targets_without_creating_files(installer, capsys):
    """A dry run lists every target and creates no files."""
    result = installer.install(dry_run=True)
    assert result == []
    assert not installer.HERMES_SKILLS.exists()
    out = capsys.readouterr().out
    for spec in installer.WRAPPERS:
        local = installer.hermes_local_dir(spec.slug)
        assert local in out


def test_install_dry_run_skips_no_files_for_fresh_install(installer, capsys):
    """Dry run on a directory with no existing files prints targets, not skips."""
    installer.install(dry_run=True)
    out = capsys.readouterr().out
    assert "would skip" not in out


# ── verify ────────────────────────────────────────────────────────────────────

def test_verify_all_missing(installer):
    """With nothing installed, verify reports every wrapper and the harness redirect as missing."""
    errors = installer.verify()
    assert len(errors) == len(installer.WRAPPERS) + 1  # +1 for harness redirect (install_harness_redirect)
    assert sum(1 for e in errors if "missing harness redirect:" in e) == 1
    assert sum(1 for e in errors if "missing wrapper:" in e) == len(installer.WRAPPERS)


def test_verify_passes_after_clean_install(installer):
    """verify returns no errors straight after a clean install."""
    installer.install()
    assert installer.verify() == []


def test_verify_detects_missing_required_string(installer, tmp_path):
    """If HERMES_READY is stripped from a managed wrapper, verify flags it."""
    installer.install()
    council_target = _target(installer, "council")
    original = council_target.read_text(encoding="utf-8")
    council_target.write_text(
        original.replace("HERMES_READY", "REPLACED"), encoding="utf-8"
    )
    errors = installer.verify()
    assert any("HERMES_READY" in e for e in errors)


def test_verify_unmanaged_wrapper_reported_as_preserved(installer, tmp_path):
    """verify reports a replaced user-owned wrapper as preserved."""
    installer.install()
    delegate_target = _target(installer, "delegate")
    # Replace managed wrapper with user-owned content.
    delegate_target.write_text("---\nname: user-delegate\n---\n# user content\n", encoding="utf-8")
    errors = installer.verify()
    assert any("unmanaged wrapper preserved" in e for e in errors)


def test_verify_no_openclaw_root_flags_violating_results(
    installer: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A results note that cites the OpenClaw root path is flagged."""
    results_dir = tmp_path / "bin/orama-system/skills/hermes-harness/references/results"
    results_dir.mkdir(parents=True)
    violating = results_dir / "some-fleet-report.md"
    violating.write_text("pull from `$OPENCLAW_ROOT/references/`\n", encoding="utf-8")
    monkeypatch.setattr(installer, "REPO_ROOT", tmp_path)
    errors = installer.verify_no_openclaw_root_in_results()
    assert errors
    assert any("$OPENCLAW_ROOT" in e for e in errors)


def test_verify_no_openclaw_root_allows_clean_results(
    installer: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A results note without that citation passes."""
    results_dir = tmp_path / "bin/orama-system/skills/hermes-harness/references/results"
    results_dir.mkdir(parents=True)
    clean = results_dir / "some-fleet-report.md"
    clean.write_text("pull from the workspace-level operator references tree\n", encoding="utf-8")
    monkeypatch.setattr(installer, "REPO_ROOT", tmp_path)
    assert installer.verify_no_openclaw_root_in_results() == []

