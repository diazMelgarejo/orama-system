"""Regression tests for hermes-delegate (F6 timeout deadlock fix)."""

from __future__ import annotations

import importlib.util
import os
import time
import types
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
DELEGATE_PY = ROOT / "bin/orama-system/skills/hermes-harness/scripts/hermes_delegate.py"


def _load_delegate_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("hermes_delegate", DELEGATE_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hanging_worker_times_out_within_deadline() -> None:
    mod = _load_delegate_module()
    release = __import__("threading").Event()

    def hang(_role: str, _task: str) -> dict[str, Any]:
        # Wait until the parent releases after timeout handling completes.
        release.wait(timeout=30)
        return {"ok": True}

    timeout_sec = 1
    t0 = time.monotonic()
    try:
        result = mod.run_delegate(
            ["task-a", "task-b"],
            pt_root=str(ROOT),
            worker_timeout_sec=timeout_sec,
            spawn_fn=hang,
        )
    finally:
        release.set()
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


def test_partial_status_when_some_workers_fail() -> None:
    mod = _load_delegate_module()

    def mixed(_role: str, task: str) -> dict[str, str]:
        if task == "bad":
            raise RuntimeError("boom")
        return {"task": task, "done": "true"}

    result = mod.run_delegate(
        ["good", "bad"],
        pt_root=str(ROOT),
        worker_timeout_sec=5,
        spawn_fn=mixed,
    )
    assert result["status"] == "partial"
    assert result["follow_up_actions"]
    assert len(result["data"]["workers"]) == 2


def test_subprocess_worker_timeout_kills_child(tmp_path: Path) -> None:
    """Production path must terminate a hung child process at the deadline."""
    mod = _load_delegate_module()
    pt = tmp_path / "pt"
    src = pt / "src"
    src.mkdir(parents=True)
    (src / "hermes_harness.py").write_text(
        "import os, time\n"
        f"PID_DIR = {str(tmp_path)!r}\n"
        "def spawn_hermes_agent(role, task):\n"
        "    with open(os.path.join(PID_DIR, task + '.pid'), 'w', encoding='utf-8') as fh:\n"
        "        fh.write(str(os.getpid()))\n"
        "    time.sleep(60)\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    t0 = time.monotonic()
    result = mod.run_delegate(
        ["slow-a", "slow-b"],
        pt_root=str(pt),
        worker_timeout_sec=1,
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 5, "subprocess workers must be killable at timeout"
    assert result["status"] == "error"
    workers = result["data"]["workers"]
    assert len(workers) == 2
    assert all("did not complete within" in w["error"] for w in workers)
    assert result["follow_up_actions"]

    for task in ("slow-a", "slow-b"):
        pid = int((tmp_path / f"{task}.pid").read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_subprocess_workers_respect_concurrency_cap(tmp_path: Path) -> None:
    """More tasks than max_concurrent must never run more than the cap at once."""
    import threading

    mod = _load_delegate_module()
    pt = tmp_path / "pt"
    src = pt / "src"
    src.mkdir(parents=True)
    marker_dir = tmp_path / "markers"
    marker_dir.mkdir()
    (src / "hermes_harness.py").write_text(
        "import os, time, uuid\n"
        f"MARKER_DIR = {str(marker_dir)!r}\n"
        "def spawn_hermes_agent(role, task):\n"
        "    marker = os.path.join(MARKER_DIR, task + '.running')\n"
        "    open(marker, 'w', encoding='utf-8').close()\n"
        "    time.sleep(0.4)\n"
        "    os.remove(marker)\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )

    tasks = [f"task-{i}" for i in range(8)]
    max_concurrent = 3
    observed_max = 0
    stop = threading.Event()

    def poll_concurrency() -> None:
        nonlocal observed_max
        while not stop.is_set():
            count = len(list(marker_dir.glob("*.running")))
            observed_max = max(observed_max, count)
            time.sleep(0.02)

    poller = threading.Thread(target=poll_concurrency, daemon=True)
    poller.start()
    try:
        rows, follow_up = mod._run_subprocess_workers(
            tasks,
            pt_root=str(pt),
            worker_timeout_sec=10,
            max_concurrent=max_concurrent,
        )
    finally:
        stop.set()
        poller.join(timeout=2)

    assert observed_max <= max_concurrent, (
        f"observed {observed_max} concurrent workers, cap was {max_concurrent}"
    )
    assert len(rows) == len(tasks)
    assert all(r["status"] == "ok" for r in rows)
    assert not follow_up
