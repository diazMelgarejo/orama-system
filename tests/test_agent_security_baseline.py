"""The bin/agents security scan uses a reviewed, justified baseline and fails closed without one."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "config/agent-security/aguara-agents.baseline.json"
SCRIPT = ROOT / "scripts/ci/run_agent_security_scans.sh"


def test_the_agents_baseline_exists_and_is_well_formed() -> None:
    data = json.loads(BASELINE.read_text())
    assert data["version"] == 1 and isinstance(data["fingerprints"], list) and data["fingerprints"]
    assert all(isinstance(f, str) and len(f) == 64 for f in data["fingerprints"])


def test_the_baseline_is_justified_in_writing() -> None:
    note = (ROOT / "config/agent-security/aguara-agents.baseline.md").read_text()
    for needle in ("SUPPLY_018", "sandbox_run.py", "lexical", "false positive", "kernel sandbox"):
        assert needle in note, needle


def test_the_scan_script_applies_the_baseline_to_bin_agents_and_fails_closed_without_it() -> None:
    text = SCRIPT.read_text()
    assert "aguara-agents.baseline.json" in text
    assert 'path" == "bin/agents"' in text.replace("$path", "path") or '"bin/agents"' in text
    assert "missing baseline" in text


def test_the_source_names_the_platform_tool_in_exactly_one_place() -> None:
    src = (ROOT / "bin/agents/sandbox_run.py").read_text()
    assert src.count("sandbox-exec") == 1


@pytest.mark.skipif(shutil.which("aguara") is None, reason="aguara is not installed")
def test_the_agents_scan_passes_with_the_baseline() -> None:
    out = subprocess.run(
        ["aguara", "scan", str(ROOT / "bin/agents"), "--ci", "--baseline", str(BASELINE), "--no-update-check"],
        capture_output=True, text=True, check=False, cwd=ROOT,
    )
    assert out.returncode == 0, out.stdout[-800:] + out.stderr[-400:]


@pytest.mark.skipif(shutil.which("aguara") is None, reason="aguara is not installed")
def test_the_agents_scan_still_fails_without_the_baseline() -> None:
    out = subprocess.run(
        ["aguara", "scan", str(ROOT / "bin/agents"), "--ci", "--no-update-check"],
        capture_output=True, text=True, check=False, cwd=ROOT,
    )
    assert out.returncode != 0, "the finding disappeared; the baseline may no longer be needed"
