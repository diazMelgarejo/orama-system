from __future__ import annotations

import importlib.util
import sys
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
def installer(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("hermes_thin_installer", INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERMES_SKILLS", tmp_path / "pt-orama")
    return module


def _target(installer, slug: str) -> Path:
    return installer.HERMES_SKILLS / installer.hermes_local_dir(slug) / "SKILL.md"


def test_install_preserves_unmanaged_wrapper(installer, capsys):
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
    target = _target(installer, "review")
    target.parent.mkdir(parents=True)
    target.write_text("---\ncreated_by: agent\n---\n\nstale\n", encoding="utf-8")

    written = installer.install()
    review = next(spec for spec in installer.WRAPPERS if spec.slug == "pt-orama-review")

    assert target in written
    assert target.read_text(encoding="utf-8") == installer.wrapper_text(review)
    assert installer.verify() == []


def test_dry_run_reports_unmanaged_wrapper_without_writing(installer, capsys):
    target = _target(installer, "delegate")
    target.parent.mkdir(parents=True)
    target.write_text("# User-owned delegate\n", encoding="utf-8")

    assert installer.install(dry_run=True) == []

    output = capsys.readouterr().out
    assert f"would skip unmanaged wrapper: {target}" in output
    assert target.read_text(encoding="utf-8") == "# User-owned delegate\n"


# ── is_managed_wrapper ────────────────────────────────────────────────────────

def test_is_managed_wrapper_nonexistent_file(installer, tmp_path):
    assert installer.is_managed_wrapper(tmp_path / "no-such-file.md") is False


def test_is_managed_wrapper_no_frontmatter(installer, tmp_path):
    f = tmp_path / "plain.md"
    f.write_text("# Just a heading\ncreated_by: agent\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


def test_is_managed_wrapper_marker_after_closing_fence(installer, tmp_path):
    """created_by: agent after the closing --- must NOT trigger managed detection."""
    f = tmp_path / "not-managed.md"
    f.write_text("---\nname: my-skill\n---\n\ncreated_by: agent\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


def test_is_managed_wrapper_valid(installer, tmp_path):
    f = tmp_path / "managed.md"
    f.write_text("---\nname: council\ncreated_by: agent\n---\n\n# body\n", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is True


def test_is_managed_wrapper_empty_file(installer, tmp_path):
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    assert installer.is_managed_wrapper(f) is False


# ── wrapper_text ──────────────────────────────────────────────────────────────

def test_wrapper_text_contains_slug_and_canonical(installer):
    spec = installer.WRAPPERS[0]  # pt-orama-council
    text = installer.wrapper_text(spec)
    assert f"name: {spec.slug}" in text
    assert spec.canonical in text
    assert spec.purpose in text


def test_wrapper_text_contains_required_readiness_strings(installer):
    for spec in installer.WRAPPERS:
        text = installer.wrapper_text(spec)
        assert "HERMES_READY" in text
        assert "AGY_READY" in text
        assert "thin local Hermes" in text
        assert "created_by: agent" in text


def test_wrapper_text_all_core_wrappers(installer):
    slugs = {spec.slug for spec in installer.WRAPPERS}
    assert slugs == {
        "pt-hardware-policy",
        "pt-orama-council",
        "pt-orama-review",
        "pt-orama-delegate",
        "lan-peer-self-talk",
    }
    optional = {spec.slug for spec in installer.OPTIONAL_WRAPPERS}
    assert optional == {"pt-orama-lesson-mining"}


# ── install ───────────────────────────────────────────────────────────────────

def test_optional_wrapper_not_installed_by_default(installer):
    installer.install()
    assert not (installer.HERMES_SKILLS / "lesson-mining" / "SKILL.md").is_file()


def test_optional_wrapper_installed_with_flag(installer):
    installer.install(include_optional=True)
    assert (installer.HERMES_SKILLS / "lesson-mining" / "SKILL.md").is_file()


def test_install_fresh_creates_all_wrappers(installer):
    written = installer.install()
    assert len(written) == len(installer.WRAPPERS)
    for spec in installer.WRAPPERS:
        target = _target(installer, spec.slug)
        assert target.is_file()


def test_install_creates_description_md(installer):
    installer.install()
    desc = installer.HERMES_SKILLS / "DESCRIPTION.md"
    assert desc.is_file()
    content = desc.read_text(encoding="utf-8")
    assert "PT-orama" in content
    assert "orama-system" in content


def test_install_dry_run_prints_targets_without_creating_files(installer, capsys):
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
    errors = installer.verify()
    assert len(errors) == len(installer.WRAPPERS)
    for error in errors:
        assert "missing wrapper:" in error


def test_verify_passes_after_clean_install(installer):
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
    installer.install()
    delegate_target = _target(installer, "delegate")
    # Replace managed wrapper with user-owned content.
    delegate_target.write_text("---\nname: user-delegate\n---\n# user content\n", encoding="utf-8")
    errors = installer.verify()
    assert any("unmanaged wrapper preserved" in e for e in errors)
