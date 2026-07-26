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
    / "install_hermes_profiles.py"
)


@pytest.fixture
def profiles_installer(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("hermes_profiles_installer", INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    profiles_root = tmp_path / "profiles"
    monkeypatch.setattr(module, "HERMES_PROFILES", profiles_root)
    monkeypatch.setattr(module, "HERMES_HOME", tmp_path)
    monkeypatch.setattr(module, "assert_trusted_install", lambda: None)
    return module


def test_install_writes_managed_profile_soul(profiles_installer):
    stats = profiles_installer.install()
    orchestrator_soul = profiles_installer.HERMES_PROFILES / "orchestrator" / "SOUL.md"
    assert orchestrator_soul in stats.written
    text = orchestrator_soul.read_text(encoding="utf-8")
    assert "orama.orchestrator" in text
    assert profiles_installer.MANAGED_MARKER in text


def test_install_skips_unmanaged_profile_soul(profiles_installer, capsys):
    target = profiles_installer.HERMES_PROFILES / "context-agent" / "SOUL.md"
    target.parent.mkdir(parents=True)
    target.write_text("# operator-owned\n", encoding="utf-8")

    profiles_installer.install()
    assert target.read_text(encoding="utf-8") == "# operator-owned\n"
    assert "skipped unmanaged profile SOUL" in capsys.readouterr().out


def test_verify_fails_when_profile_missing(profiles_installer):
    errors = profiles_installer.verify()
    assert errors
    assert any("missing profile SOUL" in err for err in errors)


def test_verify_passes_after_install(profiles_installer):
    profiles_installer.install()
    assert profiles_installer.verify() == []


def test_install_skips_when_already_synced(profiles_installer, capsys):
    profiles_installer.install()
    stats = profiles_installer.install()
    assert stats.written == []
    assert "orchestrator" in stats.skipped_synced
    assert "already synced profile SOUL" in capsys.readouterr().out


def test_sync_skips_when_already_synced(profiles_installer, capsys):
    profiles_installer.install()
    assert profiles_installer.sync() == 0
    assert "profiles already synced" in capsys.readouterr().out


def test_invalid_profile_slug_rejected(profiles_installer):
    with pytest.raises(ValueError, match="invalid hermes_profile slug"):
        profiles_installer.validate_profile_slug("../evil")


def test_harmonize_memory_preserves_operator_content(profiles_installer, tmp_path):
    role = profiles_installer.load_roles()[0]
    profile_dir = profiles_installer.profile_paths_for_slug(role.hermes_profile)
    memory = profile_dir / "memories" / "MEMORY.md"
    memory.parent.mkdir(parents=True)
    memory.write_text("# operator notes\nkeep me\n", encoding="utf-8")

    stats = profiles_installer.InstallStats(
        written=[], skipped_synced=[], skipped_unmanaged=[], harmonized=[]
    )
    profiles_installer.install_profile_stubs(role, dry_run=False, harmonize_memory=True, stats=stats)

    text = memory.read_text(encoding="utf-8")
    assert "keep me" in text
    assert profiles_installer.HARMONIZE_SECTION in text
    assert memory in stats.harmonized
