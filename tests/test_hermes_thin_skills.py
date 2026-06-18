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
    return installer.HERMES_SKILLS / slug / "SKILL.md"


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
