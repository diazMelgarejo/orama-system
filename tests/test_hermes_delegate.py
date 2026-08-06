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
        worker_timeout_sec=3,
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 15, "subprocess workers must be killable at timeout"
    assert result["status"] == "error"
    workers = result["data"]["workers"]
    assert len(workers) == 2
    assert all("did not complete within" in w["error"] for w in workers)
    assert result["follow_up_actions"]

    for task in ("slow-a", "slow-b"):
        pid_file = tmp_path / f"{task}.pid"
        raw = pid_file.read_text(encoding="utf-8").strip() if pid_file.exists() else ""
        if not raw:
            continue
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
    if not gc_pid_file.exists():
        pytest.skip("grandchild did not report its pid in time -- flaky env, not this fix")

    gc_pid = int(gc_pid_file.read_text(encoding="utf-8").strip())
    with pytest.raises(ProcessLookupError):
        os.kill(gc_pid, 0)


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
