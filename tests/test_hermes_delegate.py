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
    """
    Load and return the Hermes delegate module from its script path.
    
    Returns:
    	types.ModuleType: The loaded Hermes delegate module.
    """
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
        """
        Wait for the parent process to release the worker, then report success.
        
        Returns:
        	dict[str, Any]: A result containing ``{"ok": True}``.
        """
        release.wait(timeout=30)
        return {"ok": True}

    timeout_sec = 1
    t0 = time.monotonic()
    try:
        result = mod.run_delegate(
            ["task-a", "task-b"],
            pt_root=str(ROOT),
            worker_timeout_sec=timeout_sec,
            _spawn_fn=hang,
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
        """Marks a task as completed.
        
        Parameters:
        	task (str): The task to mark as completed.
        
        Returns:
        	dict[str, str]: A mapping containing the task and a completion indicator.
        """
        return {"task": task, "done": "true"}

    result = mod.run_delegate(
        ["alpha", "beta"],
        pt_root=str(ROOT),
        worker_timeout_sec=5,
        _spawn_fn=fast,
    )
    assert result["status"] == "ok"
    assert len(result["data"]["workers"]) == 2


def test_partial_status_when_some_workers_fail() -> None:
    mod = _load_delegate_module()

    def mixed(_role: str, task: str) -> dict[str, str]:
        """Process a task and report its completion status.
        
        Parameters:
        	task (str): The task to process.
        
        Returns:
        	dict[str, str]: A mapping containing the task and a completion value of `"true"`.
        
        Raises:
        	RuntimeError: If task is `"bad"`.
        """
        if task == "bad":
            raise RuntimeError("boom")
        return {"task": task, "done": "true"}

    result = mod.run_delegate(
        ["good", "bad"],
        pt_root=str(ROOT),
        worker_timeout_sec=5,
        _spawn_fn=mixed,
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
    worker_timeout_sec = 3
    result = mod.run_delegate(
        ["slow-a", "slow-b"],
        pt_root=str(pt),
        worker_timeout_sec=worker_timeout_sec,
    )
    elapsed = time.monotonic() - t0
    # A small, explicit margin over worker_timeout_sec, not a fixed bound
    # that stops meaning anything if worker_timeout_sec changes -- default
    # SIGTERM kills an unhandled time.sleep() near-instantly, so 2 sequential
    # terminations plus polling overhead comfortably fit in +5s.
    assert elapsed < worker_timeout_sec + 5, "subprocess workers must be killable at timeout"
    assert result["status"] == "error"
    workers = result["data"]["workers"]
    assert len(workers) == 2
    assert all("did not complete within" in w["error"] for w in workers)
    assert result["follow_up_actions"]

    for task in ("slow-a", "slow-b"):
        pid_file = tmp_path / f"{task}.pid"
        assert pid_file.exists(), f"{task} must have written its PID before being killed"
        raw = pid_file.read_text(encoding="utf-8").strip()
        assert raw, f"{task}'s PID file must not be empty"
        pid = int(raw)
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_subprocess_worker_timeout_kills_grandchild(tmp_path: Path) -> None:
    """A worker that spawns its own child must not leave it running past the deadline.

    proc.kill() only stops the direct `python -c` child. If a worker's own
    work spawns further children (a delegation harness makes this likely),
    those grandchildren survive unless the whole process group is signalled.
    """
    mod = _load_delegate_module()
    pt = tmp_path / "pt"
    src = pt / "src"
    src.mkdir(parents=True)

    grandchild_script = tmp_path / "grandchild.py"
    grandchild_script.write_text(
        "import os, sys, time\n"
        "pid_path = sys.argv[1]\n"
        "with open(pid_path, 'w', encoding='utf-8') as fh:\n"
        "    fh.write(str(os.getpid()))\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    (src / "hermes_harness.py").write_text(
        "import os, subprocess, sys\n"
        f"PID_DIR = {str(tmp_path)!r}\n"
        f"GRANDCHILD_SCRIPT = {str(grandchild_script)!r}\n"
        "def spawn_hermes_agent(role, task):\n"
        "    gc_pid_path = os.path.join(PID_DIR, task + '.gc.pid')\n"
        "    grandchild = subprocess.Popen(\n"
        "        [sys.executable, GRANDCHILD_SCRIPT, gc_pid_path]\n"
        "    )\n"
        "    grandchild.wait()\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    result = mod.run_delegate(
        ["slow-gc"],
        pt_root=str(pt),
        worker_timeout_sec=3,
    )
    assert result["status"] == "error"

    # Poll briefly for the grandchild's own pid file -- it writes it after
    # os.getpid(), which races the parent's timeout/kill.
    gc_pid_file = tmp_path / "slow-gc.gc.pid"
    deadline = time.monotonic() + 5
    while not gc_pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert gc_pid_file.exists(), "grandchild must have reported its PID before being killed"

    gc_pid = int(gc_pid_file.read_text(encoding="utf-8").strip())
    # Poll for the actual kill, not a single immediate check -- diagnosed
    # directly against this environment: killpg's signal delivery and the
    # kernel fully reaping a killed grandchild are not synchronous with
    # _terminate_worker returning, even though the worker's own blocking
    # wait() on the grandchild is causally gated on its death. A single
    # check right after run_delegate returns can catch the grandchild in
    # that reap window and see it as still "alive" for a few hundred ms.
    kill_deadline = time.monotonic() + 5
    grandchild_dead = False
    while time.monotonic() < kill_deadline:
        try:
            os.kill(gc_pid, 0)
        except ProcessLookupError:
            grandchild_dead = True
            break
        time.sleep(0.1)
    assert grandchild_dead, "grandchild must be killed, not just the direct child"


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
    assert observed_max > 1, "workers must run concurrently, not serially"
    assert len(rows) == len(tasks)
    assert all(r["status"] == "ok" for r in rows)
    assert not follow_up


def test_worker_construction_failure_does_not_abort_the_batch(tmp_path: Path) -> None:
    """Regression for PR #280 review 4875271204: if _Worker.__init__ raises
    for one task (e.g. Popen fails), the other tasks in the batch must
    still run to completion -- not have the exception propagate and abort
    everything else in flight or still queued.
    """
    mod = _load_delegate_module()
    pt = tmp_path / "pt"
    src = pt / "src"
    src.mkdir(parents=True)
    (src / "hermes_harness.py").write_text(
        "import json, sys\n"
        "def spawn_hermes_agent(role, task):\n"
        "    return {'ok': True, 'task': task}\n",
        encoding="utf-8",
    )

    real_worker_cls = mod._Worker
    call_count = {"n": 0}

    class _FlakyWorker(real_worker_cls):
        def __init__(self, task: str, pt_root: str) -> None:
            """
            Simulate a worker construction failure for the second instance.
            
            Raises:
            	OSError: If this is the second worker instance being constructed.
            """
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("simulated Popen failure for this task only")
            super().__init__(task, pt_root)

    import unittest.mock

    with unittest.mock.patch.object(mod, "_Worker", _FlakyWorker):
        rows, follow_up = mod._run_subprocess_workers(
            ["task-a", "task-b", "task-c"],
            pt_root=str(pt),
            worker_timeout_sec=10,
            max_concurrent=5,
        )

    assert len(rows) == 3, "all 3 tasks must have a row, including the one that failed to launch"
    by_task = {r["task"]: r for r in rows}
    assert by_task["task-a"]["status"] == "ok"
    assert by_task["task-c"]["status"] == "ok"
    assert by_task["task-b"]["status"] == "error"
    assert "simulated Popen failure" in by_task["task-b"]["error"]
    assert any("task-b" in f for f in follow_up)


def test_deadline_stops_new_launches_leaving_queued_tasks_unlaunched(tmp_path: Path) -> None:
    """Regression for PR #280 review 4875271204: the launch loop must check
    the deadline before each new worker, not just after finishing a full
    batch of launches. With max_concurrent=1 (strictly sequential) and a
    deadline sized for ~2 completions, later tasks should be correctly
    reported as never started, not silently launched past the deadline.

    Per-task timing (0.2s sleep, ~0.22s wall time including interpreter
    startup) and the 0.6s deadline were verified empirically before
    writing this test -- 2 sequential tasks reliably complete by ~0.45s,
    a 3rd would finish around ~0.67s, past the 0.6s deadline -- giving
    real margin on both sides rather than a razor-thin boundary.
    """
    mod = _load_delegate_module()
    pt = tmp_path / "pt"
    src = pt / "src"
    src.mkdir(parents=True)
    (src / "hermes_harness.py").write_text(
        "import json, sys, time\n"
        "def spawn_hermes_agent(role, task):\n"
        "    time.sleep(0.2)\n"
        "    return {'ok': True, 'task': task}\n",
        encoding="utf-8",
    )

    rows, follow_up = mod._run_subprocess_workers(
        ["task-a", "task-b", "task-c", "task-d", "task-e"],
        pt_root=str(pt),
        worker_timeout_sec=0.6,
        max_concurrent=1,
    )

    assert len(rows) == 5
    by_task = {r["task"]: r for r in rows}
    completed = [t for t in by_task if by_task[t]["status"] == "ok"]
    unlaunched = [t for t in by_task if by_task[t]["status"] == "error"]

    assert len(completed) >= 1, "at least the first, already-launched worker must complete"
    assert len(unlaunched) >= 1, "at least one later task must never have launched"
    assert len(completed) + len(unlaunched) == 5
    for t in unlaunched:
        assert "did not start" in by_task[t]["error"], (
            f"{t} must be reported as never started, not launched past the deadline"
        )
        assert any(t in f for f in follow_up)
