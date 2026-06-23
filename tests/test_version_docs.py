"""Version surface consistency tests.

Source of truth: src/orama_system/_version.py
All canonical doc/config surfaces must match __version__.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _ver():
    """Load the canonical version at test time — never hardcode."""
    try:
        ns: dict = {}
        exec((ROOT / "src" / "orama_system" / "_version.py").read_text(), ns)
        return ns["__version__"]
    except FileNotFoundError:
        # Branch predates _version.py — fall back to pyproject
        import re
        text = (ROOT / "pyproject.toml").read_text()
        m = re.search(r'version\s*=\s*"([^"]+)"', text)
        return m.group(1) if m else "UNKNOWN"


EXPECTED = _ver()


def test_active_version_surfaces_match_version_file():
    """All canonical surfaces must match the active version."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    claude    = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    skill     = (ROOT / "bin" / "orama-system" / "SKILL.md").read_text(encoding="utf-8")

    # pyproject: accept static declaration OR correct hatch dynamic wiring
    if f'version = "{EXPECTED}"' in pyproject:
        pass
    elif "dynamic" in pyproject and 'path = "src/orama_system/_version.py"' in pyproject:
        pass
    else:
        raise AssertionError(
            f"pyproject.toml must have version=\"{EXPECTED}\" or hatch dynamic wiring"
        )

    assert EXPECTED in claude, f"CLAUDE.md missing {EXPECTED}"
    assert f"version: {EXPECTED}" in skill, f"bin/orama-system/SKILL.md missing version: {EXPECTED}"


def test_readme_mentions_active_lan_helpers():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "portal_server.py" in readme
    assert "network_autoconfig.py" in readme


def test_bridge_docs_reference_current_version():
    bridge = (ROOT / "docs" / "PERPLEXITY_BRIDGE.md").read_text(encoding="utf-8")
    sync   = (ROOT / "docs" / "SYNC_ANALYSIS.md").read_text(encoding="utf-8")
    assert f"Version {EXPECTED}" in bridge, f"PERPLEXITY_BRIDGE.md missing Version {EXPECTED}"
    assert f"v{EXPECTED}" in sync, f"SYNC_ANALYSIS.md missing v{EXPECTED}"


def test_sync_version_check_if_present():
    """Run sync_version.py --check when the script exists; skip otherwise."""
    sv = ROOT / "scripts" / "sync_version.py"
    if not sv.exists():
        return  # branch predates sync_version.py
    r = subprocess.run(
        [sys.executable, str(sv), "--check"],
        capture_output=True, text=True, cwd=str(ROOT),
        timeout=60,
    )
    assert r.returncode == 0, f"sync_version.py --check found stale surfaces:\n{r.stdout}\n{r.stderr}"
