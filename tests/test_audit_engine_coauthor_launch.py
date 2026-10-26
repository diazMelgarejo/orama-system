"""The co-author policy check must be launched through bash.

A shebang script cannot be executed directly on Windows (WinError 193), which
made the attribution audit fail closed for every Windows push.
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_engine():
    """Import scripts/git/audit_engine.py under a private module name and return it."""
    spec = importlib.util.spec_from_file_location(
        "audit_engine_under_test", ROOT / "scripts" / "git" / "audit_engine.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_coauthor_check_is_launched_via_bash(monkeypatch):
    """The policy script is run as ``bash <script>``, never executed directly."""
    engine = _load_engine()
    seen = {}

    def fake_run(argv, **kwargs):
        """Record the command line and pretend the policy check succeeded."""
        seen["argv"] = list(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(engine.subprocess, "run", fake_run)
    assert engine._coauthor_policy_ok(ROOT, "plain message body\n") is True
    assert seen["argv"][0] == "bash"
    assert seen["argv"][1].endswith("check_commit_message.sh")


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_coauthor_check_runs_for_real_without_launch_error():
    """Run the real policy script: it must launch (no OSError) and accept a plain body."""
    engine = _load_engine()
    # A body with no trailers is acceptable under the policy; the point is that
    # the script actually executes instead of raising OSError on Windows.
    assert engine._coauthor_policy_ok(ROOT, "plain message body\n") is True
