"""Regression coverage for the agent-security workflow trigger and pins."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/agent-security.yml"
SCANNER = ROOT / "scripts/ci/run_agent_security_scans.sh"


def _not_suppressed(value: object) -> bool:
    """Accept only an absent or explicit YAML boolean false; a quoted "false" is a string and is rejected."""
    return value is None or value is False


def _typed_jobs() -> dict:
    """Load jobs with YAML scalar types preserved (BaseLoader would stringify booleans)."""
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def _exact_cache_key(key: str, name: str, pin: str) -> bool:
    """Require the full scanner cache key; a longer or shorter version never matches."""
    return key == f"{name}-${{{{ runner.os }}}}-{pin}"


def test_stacked_pull_requests_trigger_without_changing_push_scope() -> None:
    """Run security for every PR base while retaining the existing push scope."""
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    events = workflow["on"]
    assert events["pull_request"] == {"branches": ["**"]}
    assert events["push"] == {"branches": ["main", "develop"]}
    assert "pull_request_target" not in events
    for job in _typed_jobs().values():
        assert _not_suppressed(job.get("continue-on-error"))
        assert all(_not_suppressed(step.get("continue-on-error")) for step in job["steps"])
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
        assert _exact_cache_key(caches[0]["with"]["key"], name, pin)
        assert not caches[0]["with"].get("restore-keys", "").strip()
        assert "if" not in caches[0]


def test_suppression_predicate_rejects_quoted_false_and_other_values() -> None:
    """Only a missing key or a real YAML false counts as not suppressed."""
    assert _not_suppressed(None) and _not_suppressed(False)
    for bad in ("false", "False", True, "true", 0, ""):
        assert not _not_suppressed(bad)
    quoted = yaml.safe_load("continue-on-error: 'false'\nother: false\n")
    assert not _not_suppressed(quoted["continue-on-error"]) and _not_suppressed(quoted["other"])


def test_cache_key_match_is_exact_so_082_cannot_select_0820() -> None:
    """A requested 0.8.2 cache key never equals, or prefixes into, a 0.8.20 key."""
    base = "ramparts-${{ runner.os }}-"
    assert _exact_cache_key(base + "0.8.2", "ramparts", "0.8.2")
    for other in ("0.8.20", "0.8.2.1", "0.8.", "0.8.2 "):
        assert not _exact_cache_key(base + other, "ramparts", "0.8.2")
    assert not _exact_cache_key(base + "0.8.2", "ramparts", "0.8.20")
