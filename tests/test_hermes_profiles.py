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
    return module


def test_install_writes_managed_profile_soul(profiles_installer):
    written = profiles_installer.install()
    orchestrator_soul = profiles_installer.HERMES_PROFILES / "orchestrator" / "SOUL.md"
    assert orchestrator_soul in written
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
