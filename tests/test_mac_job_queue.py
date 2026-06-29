"""Tests for mac_job_queue.py role routing."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"


def _load_queue():
    path = _SCRIPTS / "mac_job_queue.py"
    spec = importlib.util.spec_from_file_location("mac_job_queue", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_actionable_win_deliverable():
    q = _load_queue()
    assert q.is_actionable_assignment("win-pt183-reconcile.md", "code-review/bridge", "win")


def test_skip_ops_ack():
    q = _load_queue()
    assert q.is_actionable_assignment("win-cycle-005-ack.md", "ops/co-orchestration-active", "win") is False


def test_classify_researcher():
    q = _load_queue()
    assert q.classify_role("win-gpu-results-h5-final.md", "autoresearch/gpu-done") == "researcher"


def test_classify_orchestrator():
    q = _load_queue()
    assert q.classify_role("win-pt183-reconcile.md", "code-review/bridge") == "orchestrator"


def test_is_idle_empty():
    q = _load_queue()
    assert q.is_idle(q._empty_state()) is True
