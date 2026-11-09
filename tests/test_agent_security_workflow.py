"""Regression coverage for the agent-security workflow trigger and pins."""

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/agent-security.yml"
SCANNER = ROOT / "scripts/ci/run_agent_security_scans.sh"


def test_stacked_pull_requests_trigger_without_changing_push_scope():
    """Run security for every PR base while retaining the existing push scope."""
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    events = workflow["on"]
    assert events["pull_request"] == {"branches": ["**"]}
    assert events["push"] == {"branches": ["main", "develop"]}
    assert "pull_request_target" not in events


def test_security_workflow_retains_pinned_actions_and_scanners():
    """Keep existing action SHAs and scanner pins tied to their cache keys."""
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])

    script = SCANNER.read_text()
    pins = {
        "aguara": "2ad546a95a03eb81f5255471c500ca326ee5220b",
        "agent-audit": "d7b11f8bc02f0f212147a161e5d3bb10dcc117b2",
        "ramparts": "0.8.2",
    }
    assert f'AGUARA_REF="${{AGUARA_REF:-{pins["aguara"]}}}"' in script
    assert f'AGENT_AUDIT_REF="${{AGENT_AUDIT_REF:-{pins["agent-audit"]}}}"' in script
    assert f'RAMPARTS_VERSION="${{RAMPARTS_VERSION:-{pins["ramparts"]}}}"' in script
    for name, pin in pins.items():
        assert any(pin in step.get("with", {}).get("key", "") for step in jobs[name]["steps"])
        assert any(step.get("run") == f"bash scripts/ci/run_agent_security_scans.sh {name}"
                   for step in jobs[name]["steps"])
