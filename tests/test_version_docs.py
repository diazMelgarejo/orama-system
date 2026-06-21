from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_active_version_surfaces_are_v1100():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    skill = (ROOT / "bin" / "orama-system" / "SKILL.md").read_text(encoding="utf-8")

    assert 'version = "1.1.0.0"' in pyproject
    assert "1.1.0.0" in claude
    assert "version: 1.1.0.0" in skill


def test_readme_mentions_active_lan_helpers():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "portal_server.py" in readme
    assert "network_autoconfig.py" in readme


def test_bridge_docs_reference_09994_and_bin_skills():
    bridge = (ROOT / "docs" / "PERPLEXITY_BRIDGE.md").read_text(encoding="utf-8")
    sync = (ROOT / "docs" / "SYNC_ANALYSIS.md").read_text(encoding="utf-8")

    assert "Version 1.1.0.0" in bridge
    assert "v1.1.0.0" in sync
