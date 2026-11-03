"""Tests for dual_path_dispatch.py."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "dual_path_dispatch.py"


def _load_dispatch():
    """Import dual_path_dispatch.py as a fresh module for testing."""
    spec = importlib.util.spec_from_file_location("dual_path_dispatch_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_prompt_names_queue_job():
    """The prompt names the queue and the job id."""
    dispatch = _load_dispatch()

    prompt = dispatch.build_prompt(".cursor/agents/mac-orchestrator-queue.md", "orchestrator", "mac-job.md")

    assert " - execute ONE " in prompt
    assert "execute ONE orchestrator job (mac-job.md)" in prompt
    assert "mac_job_queue / inbox" in prompt


def test_run_candidates_keeps_first_success(tmp_path):
    """The first candidate to succeed wins and the slower one is stopped."""
    dispatch = _load_dispatch()
    slow = dispatch.Candidate(
        "slow-success",
        [sys.executable, "-c", "import time; time.sleep(3); raise SystemExit(0)"],
    )
    fast = dispatch.Candidate("fast-success", [sys.executable, "-c", "raise SystemExit(0)"])

    result = dispatch.run_candidates([slow, fast], tmp_path, timeout=10)

    assert result["status"] == "ok"
    assert result["winner"]["name"] == "fast-success"
    assert (tmp_path / "fast-success.log").is_file()
    assert "slow-success" in result["containment"]  # the loser was tree-killed


def test_run_candidates_waits_for_second_when_first_fails(tmp_path):
    """A failing first candidate does not stop the second from winning."""
    dispatch = _load_dispatch()
    failing = dispatch.Candidate("failing", [sys.executable, "-c", "raise SystemExit(7)"])
    succeeding = dispatch.Candidate(
        "succeeding",
        [sys.executable, "-c", "import time; time.sleep(0.2); raise SystemExit(0)"],
    )

    result = dispatch.run_candidates([failing, succeeding], tmp_path, timeout=10)

    assert result["status"] == "ok"
    assert result["winner"]["name"] == "succeeding"
    assert any(item["name"] == "failing" and item["returncode"] == 7 for item in result["attempts"])


def test_run_candidates_closes_stdin_for_every_candidate(tmp_path):
    """Regression guard for the closed-stdin contract: candidates run
    detached/non-interactive in parallel, so an inherited-but-unfed stdin
    can leave a dispatched CLI (e.g. Codex) blocked on "Reading additional
    input..." forever. See dispatch_codex_partner.py's own stdin-hygiene
    fix and codex-cli-v142-dispatch.md's Stdin hygiene section."""
    dispatch = _load_dispatch()
    candidates = [
        dispatch.Candidate("a", [sys.executable, "-c", "raise SystemExit(0)"]),
        dispatch.Candidate("b", [sys.executable, "-c", "raise SystemExit(1)"]),
    ]

    fake_proc = MagicMock()
    fake_proc.poll.return_value = 0

    with patch.object(dispatch, "launch_tree", return_value=fake_proc) as mock_popen:
        dispatch.run_candidates(candidates, tmp_path, timeout=10)

    assert mock_popen.call_count == len(candidates)
    for call in mock_popen.call_args_list:
        assert call.kwargs.get("stdin") == subprocess.DEVNULL


def test_run_candidates_contains_launch_failures(tmp_path: Path) -> None:
    """A candidate whose launch fails is recorded and the next candidate still runs."""
    dispatch = _load_dispatch()
    broken = dispatch.Candidate("broken", [sys.executable, "-c", "raise SystemExit(0)"])
    good = dispatch.Candidate("good", [sys.executable, "-c", "raise SystemExit(0)"])
    real_launch = dispatch.launch_tree

    def launch(argv: list[str], **kwargs: object) -> subprocess.Popen[str]:
        """Fail the broken candidate's launch; start the other one for real."""
        if str(getattr(kwargs["stdout"], "name", "")).endswith("broken.log"):
            raise dispatch.LaunchError("job assignment failed")
        return real_launch(argv, **kwargs)

    with patch.object(dispatch, "launch_tree", side_effect=launch):
        result = dispatch.run_candidates([broken, good], tmp_path, timeout=10)

    assert result["status"] == "ok" and result["winner"]["name"] == "good"
    failed = [item for item in result["attempts"] if item["name"] == "broken"]
    assert failed and failed[0]["returncode"] == "launch-failed"
    assert "launch failed" in (tmp_path / "broken.log").read_text(encoding="utf-8")


def test_all_failed_result_reports_containment(tmp_path: Path) -> None:
    """When every candidate fails the result still carries containment and its scope note."""
    dispatch = _load_dispatch()
    bad = dispatch.Candidate("bad", [sys.executable, "-c", "raise SystemExit(3)"])

    result = dispatch.run_candidates([bad], tmp_path, timeout=10)

    assert result["status"] == "error" and result["reason"] == "all dispatch candidates failed"
    assert "bad" in result["containment"]
    assert result["containment_note"] == dispatch.CONTAINMENT_SCOPE_NOTE
