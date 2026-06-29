"""Tests for mac_job_queue.py role routing."""
from __future__ import annotations

import argparse
import importlib.util
import json
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


def test_blocked_pending_skipped_in_pick():
    q = _load_queue()
    state = q._empty_state()
    state["orchestrator"]["pending"] = [
        {"id": "win-coder-l1-comms-autoplan-backlog.md", "filename": "win-coder-l1-comms-autoplan-backlog.md"},
        {"id": "win-pt199-frugality-reconcile.md", "filename": "win-pt199-frugality-reconcile.md"},
    ]
    pick = q._first_actionable_pending(state)
    assert pick is not None
    assert pick["id"] == "win-pt199-frugality-reconcile.md"


def test_pulse_gate_idle_empty_queue(tmp_path, monkeypatch):
    q = _load_queue()
    seen = tmp_path / "seen.json"
    seen.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(q, "list_inbox", lambda: [])
    monkeypatch.setattr(q, "load_queue", q._empty_state)
    monkeypatch.setattr(q, "save_queue", lambda _s: None)
    monkeypatch.setattr(q, "enqueue_from_inbox", lambda _s: [])

    args = argparse.Namespace(seen_file=str(seen))
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        q.cmd_pulse_gate(args)
    out = json.loads(buf.getvalue())
    assert out["status"] == "idle"
