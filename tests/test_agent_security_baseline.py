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
    """Require a versioned baseline containing full SHA-256 fingerprints."""
    data = json.loads(BASELINE.read_text())
    assert data["version"] == 1 and isinstance(data["fingerprints"], list) and data["fingerprints"]
    assert all(isinstance(f, str) and len(f) == 64 for f in data["fingerprints"])


def test_the_baseline_is_justified_in_writing() -> None:
    """Keep each retained scanner exemption linked to its safety rationale."""
    note = (ROOT / "config/agent-security/aguara-agents.baseline.md").read_text()
    for needle in (
        "SUPPLY_018", "sandbox_run.py", "lexical", "false positive", "kernel sandbox",
        "SUPPLY_017", "seat_contracts.py", "mkstemp", "exclusive",
    ):
        assert needle in note, needle


def test_the_scan_script_applies_the_baseline_to_bin_agents_and_fails_closed_without_it() -> None:
    """Keep the wrapper's explicit baseline and missing-file refusal visible."""
    text = SCRIPT.read_text()
    assert "aguara-agents.baseline.json" in text
    assert 'path" == "bin/agents"' in text.replace("$path", "path") or '"bin/agents"' in text
    assert "missing baseline" in text


def test_the_source_names_the_platform_tool_in_exactly_one_place() -> None:
    """Keep the platform executable name centralized in the sandbox module."""
    src = (ROOT / "bin/agents/sandbox_run.py").read_text()
    assert src.count("sandbox-exec") == 1


@pytest.mark.skipif(shutil.which("aguara") is None, reason="aguara is not installed")
def test_the_agents_scan_passes_with_the_baseline() -> None:
    """Require the installed scanner to accept the reviewed agent baseline."""
    out = subprocess.run(
        ["aguara", "scan", str(ROOT / "bin/agents"), "--ci", "--baseline", str(BASELINE), "--no-update-check"],
        capture_output=True, text=True, check=False, cwd=ROOT,
    )
    assert out.returncode == 0, out.stdout[-800:] + out.stderr[-400:]


@pytest.mark.skipif(shutil.which("aguara") is None, reason="aguara is not installed")
def test_the_agents_scan_still_fails_without_the_baseline() -> None:
    """Confirm the baseline still covers an actual finding rather than stale data."""
    out = subprocess.run(
        ["aguara", "scan", str(ROOT / "bin/agents"), "--ci", "--no-update-check"],
        capture_output=True, text=True, check=False, cwd=ROOT,
    )
    assert out.returncode != 0, "the finding disappeared; the baseline may no longer be needed"


def test_aguara_wrapper_enforces_agents_baseline_with_stub(tmp_path: Path) -> None:
    """Exercise baseline selection, scanner failure, and missing-baseline refusal offline."""
    import os
    import shutil
    import subprocess

    script = tmp_path / "scripts/ci/run_agent_security_scans.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(SCRIPT, script)
    (tmp_path / "bin/agents").mkdir(parents=True)
    (tmp_path / "bin/orama-system/skills").mkdir(parents=True)
    config = tmp_path / "config/agent-security"
    config.mkdir(parents=True)
    agents = config / "aguara-agents.baseline.json"
    agents.write_text("{}")
    (config / "aguara-skills.baseline.json").write_text("{}")
    bindir = tmp_path / "stub-bin"
    bindir.mkdir()
    scanner = bindir / "aguara"
    scanner.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$SCAN_LOG"\nprintf "END\\n" >> "$SCAN_LOG"\nexit "${SCAN_STATUS:-0}"\n')
    scanner.chmod(0o755)
    log = tmp_path / "scan.log"
    env = {"PATH": str(bindir) + os.pathsep + os.defpath, "RUNNER_TEMP": str(tmp_path), "SCAN_LOG": str(log)}

    def run(status: int = 0) -> subprocess.CompletedProcess[str]:
        """Run the isolated wrapper with a controlled scanner exit status."""
        return subprocess.run(["bash", str(script), "aguara"], env={**env, "SCAN_STATUS": str(status)},
                              capture_output=True, text=True, timeout=10)

    assert run().returncode == 0
    calls = log.read_text().split("END\n")
    assert calls[0].splitlines() == ["scan", str(tmp_path / "bin/agents"), "--ci", "--baseline", str(agents)]
    assert run(7).returncode != 0
    log.unlink()
    agents.unlink()
    result = run()
    assert result.returncode != 0
    assert "missing baseline" in result.stdout
    assert str(tmp_path / "bin/agents") not in log.read_text().splitlines()
