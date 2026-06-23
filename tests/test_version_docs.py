"""Version surface consistency tests.

Source of truth: src/orama_system/_version.py
All canonical doc/config surfaces must match __version__.
Run `python3 scripts/sync_version.py` to propagate any bump.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _ver() -> str:
    """Load the canonical version at test time — never hardcode.

    Falls back to pyproject.toml for branches that predate _version.py,
    so this file runs correctly on experiment/pr branches without the file.
    """
    try:
        ns: dict = {}
        exec((ROOT / "src" / "orama_system" / "_version.py").read_text(), ns)
        return ns["__version__"]
    except FileNotFoundError:
        import re as _re
        text = (ROOT / "pyproject.toml").read_text()
        m = _re.search(r'version\s*=\s*"([^"]+)"', text)
        return m.group(1) if m else "UNKNOWN"


EXPECTED = _ver()


def test_active_version_surfaces_match_version_file():
    """All canonical surfaces must match src/orama_system/_version.py."""
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
            f"pyproject.toml must have version=\"{EXPECTED}\" or hatch dynamic wiring "
            f"(path = src/orama_system/_version.py)"
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


def test_agent_registry_version():
    import json
    for reg in [
        ROOT / "bin" / "config" / "agent_registry.json",
        ROOT / "bin" / "orama-system" / "config" / "agent_registry.json",
    ]:
        if reg.exists():
            data = json.loads(reg.read_text())
            assert data.get("version") == EXPECTED, (
                f"{reg.relative_to(ROOT)} version={data.get('version')!r} != {EXPECTED!r}"
            )


def test_portal_server_version_constant():
    portal = (ROOT / "src" / "orama_system" / "portal_server.py").read_text(encoding="utf-8")
    assert f'VERSION = "{EXPECTED}"' in portal, (
        f"portal_server.py VERSION constant != {EXPECTED!r}"
    )


def test_sync_version_leaves_no_stale_surfaces():
    """sync_version.py --check must exit 0 (all surfaces already at EXPECTED).

    Skips gracefully when sync_version.py does not exist on this branch
    (branches predating the centralized version system).
    """
    sv = ROOT / "scripts" / "sync_version.py"
    if not sv.exists():
        return  # branch predates sync_version.py — skip
    r = subprocess.run(
        [sys.executable, str(sv), "--check"],
        capture_output=True, text=True, cwd=str(ROOT),
        timeout=60,  # prevent CI hang if sync_version.py stalls
    )
    assert r.returncode == 0, (
        f"sync_version.py --check found stale surfaces:\n{r.stdout}\n{r.stderr}"
    )
