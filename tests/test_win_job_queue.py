"""Tests for win_job_queue.py role routing."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"


def _load_queue():
    path = _SCRIPTS / "win_job_queue.py"
    spec = importlib.util.spec_from_file_location("win_job_queue", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_classify_autoresearcher():
    q = _load_queue()
    assert q.classify_role("win-autoresearcher-h5-gpu.md", "autoresearch/gpu-run") == "autoresearcher"
    assert q.classify_role("mac-h4-comparison.md", "autoresearch/gpu-done") == "autoresearcher"


def test_classify_coder():
    q = _load_queue()
    assert q.classify_role("win-coder-frugal-spawn.md", "code-review/bridge-merge") == "coder"


def test_skip_ops_noise():
    q = _load_queue()
    assert q.classify_role("coord-003-go.md", "ops/co-orchestration-active") is None


def test_skip_mac_deliverables():
    q = _load_queue()
    assert q.is_actionable_assignment("mac-h4-comparison.md", "autoresearch/gpu-done", "mac") is False
    assert q.is_actionable_assignment("win-autoresearcher-h5-cross-frugal.md", "autoresearch/gpu-run", "mac") is True


def test_prune_pending_drops_noise():
    q = _load_queue()
    state = q._empty_state()
    state["autoresearcher"]["pending"] = [
        {"id": "mac-h4-comparison.md", "filename": "mac-h4-comparison.md", "topic": "autoresearch/gpu-done"},
        {"id": "win-autoresearcher-h5-gpu.md", "filename": "win-autoresearcher-h5-gpu.md", "topic": "autoresearch/gpu-run"},
    ]
    removed = q.prune_pending(state)
    assert "mac-h4-comparison.md" in removed
    assert [j["id"] for j in state["autoresearcher"]["pending"]] == ["win-autoresearcher-h5-gpu.md"]


def test_first_actionable_skips_blocked():
    q = _load_queue()
    state = q._empty_state()
    state["coder"]["pending"] = [
        {"id": "win-coder-l1-comms-autoplan-backlog.md", "filename": "win-coder-l1-comms-autoplan-backlog.md"},
        {"id": "win-coder-frugal-spawn.md", "filename": "win-coder-frugal-spawn.md"},
    ]
    pick = q._first_actionable_pending(state)
    assert pick is not None
    assert pick["id"] == "win-coder-frugal-spawn.md"
