"""Regression tests for hermes-delegate (F6 timeout deadlock fix)."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
DELEGATE_PY = ROOT / "bin/orama-system/skills/hermes-harness/scripts/hermes_delegate.py"


def _load_delegate_module():
    spec = importlib.util.spec_from_file_location("hermes_delegate", DELEGATE_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hanging_worker_times_out_within_deadline() -> None:
    mod = _load_delegate_module()

    def hang(_role: str, _task: str) -> dict[str, Any]:
        # Block longer than worker_timeout_sec; delegate must return before this completes.
        time.sleep(timeout_sec + 5)
        return {"ok": True}

    timeout_sec = 1
    t0 = time.monotonic()
    result = mod.run_delegate(
        ["task-a", "task-b"],
        pt_root=str(ROOT),
        worker_timeout_sec=timeout_sec,
        spawn_fn=hang,
    )
    elapsed = time.monotonic() - t0

    assert elapsed < timeout_sec + 2, "delegate must not hang past worker timeout"
    assert result["status"] == "error"
    workers = result["data"]["workers"]
    assert len(workers) == 2
    assert all(w["status"] == "error" for w in workers)
    assert all("did not complete within" in w["error"] for w in workers)


def test_fast_workers_complete_ok() -> None:
    mod = _load_delegate_module()

    def fast(_role: str, task: str) -> dict[str, str]:
        return {"task": task, "done": "true"}

    result = mod.run_delegate(
        ["alpha", "beta"],
        pt_root=str(ROOT),
        worker_timeout_sec=5,
        spawn_fn=fast,
    )
    assert result["status"] == "ok"
    assert len(result["data"]["workers"]) == 2
