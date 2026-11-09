"""Regression coverage for the agent-security workflow trigger and pins."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/agent-security.yml"
SCANNER = ROOT / "scripts/ci/run_agent_security_scans.sh"


def test_stacked_pull_requests_trigger_without_changing_push_scope() -> None:
    """Run security for every PR base while retaining the existing push scope."""
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    events = workflow["on"]
    assert events["pull_request"] == {"branches": ["**"]}
    assert events["push"] == {"branches": ["main", "develop"]}
    assert "pull_request_target" not in events
    for name in ("aguara", "agent-audit", "skill-scanner", "mcp-scanner", "ramparts"):
        job = workflow["jobs"][name]
        assert "if" not in job and "needs" not in job
        scan = next(step for step in job["steps"] if step.get("run") ==
                    f"bash scripts/ci/run_agent_security_scans.sh {name}")
        assert "if" not in scan


def test_security_workflow_retains_pinned_actions_and_scanners() -> None:
    """Keep existing action SHAs and scanner pins tied to their cache keys."""
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    actions = {
        "actions/checkout": "fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
        "gitleaks/gitleaks-action": "dcedce43c6f43de0b836d1fe38946645c9c638dc",
        "actions/setup-go": "40f1582b2485089dde7abd97c1529aa768e1baff",
        "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
        "actions/cache": "0057852bfaa89a56745cba8c7296529d2fc39830",
        "dtolnay/rust-toolchain": "6c977a6ca4077a0ceb28ffbe03f59d46e9ac8772",
    }
    seen = set()
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                action, ref = step["uses"].rsplit("@", 1)
                assert actions[action] == ref
                seen.add(action)
    assert seen == set(actions)

    script = SCANNER.read_text()
    pins = {
        "aguara": "2ad546a95a03eb81f5255471c500ca326ee5220b",
        "agent-audit": "d7b11f8bc02f0f212147a161e5d3bb10dcc117b2",
        "ramparts": "0.8.2",
    }
    assert f'AGUARA_REF="${{AGUARA_REF:-{pins["aguara"]}}}"' in script
    assert f'AGENT_AUDIT_REF="${{AGENT_AUDIT_REF:-{pins["agent-audit"]}}}"' in script
    assert f'RAMPARTS_VERSION="${{RAMPARTS_VERSION:-{pins["ramparts"]}}}"' in script
    paths = {"aguara": "~/go/bin/aguara", "agent-audit": "/tmp/agent-sec-cache/agent-audit",
             "ramparts": "~/.cargo/bin"}
    for name, pin in pins.items():
        steps = jobs[name]["steps"]
        scan_index = next(i for i, step in enumerate(steps) if step.get("run") ==
                          f"bash scripts/ci/run_agent_security_scans.sh {name}")
        caches = [step for step in steps[:scan_index] if step.get("uses") ==
                  f"actions/cache@{actions['actions/cache']}" and
                  paths[name] in step.get("with", {}).get("path", "").splitlines()]
        assert len(caches) == 1
        assert caches[0]["with"]["key"] == f"{name}-${{{{ runner.os }}}}-{pin}"
        assert "if" not in caches[0]
