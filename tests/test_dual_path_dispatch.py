"""Tests for dual_path_dispatch.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "dual_path_dispatch.py"


def _load_dispatch():
    spec = importlib.util.spec_from_file_location("dual_path_dispatch_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_prompt_names_queue_job():
    dispatch = _load_dispatch()

    prompt = dispatch.build_prompt(".cursor/agents/mac-orchestrator-queue.md", "orchestrator", "mac-job.md")

    assert " - execute ONE " in prompt
    assert "execute ONE orchestrator job (mac-job.md)" in prompt
    assert "mac_job_queue / inbox" in prompt


def test_run_candidates_keeps_first_success(tmp_path):
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


def test_run_candidates_waits_for_second_when_first_fails(tmp_path):
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
