#!/usr/bin/env python3
"""Parallel PT pipeline workers via spawn_hermes_agent (hermes-delegate command)."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Protocol


def _canonical_result(
    *,
    status: str,
    action: str,
    data: dict[str, Any],
    follow_up_actions: list[str] | None = None,
    warnings: list[str] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Builds the standard Hermes delegate response structure.
    
    Parameters:
        status (str): Overall outcome status.
        action (str): Action represented by the response.
        data (dict[str, Any]): Response payload.
        follow_up_actions (list[str] | None): Additional actions suggested by the result.
        warnings (list[str] | None): Warnings associated with the result.
        error (dict[str, str] | None): Structured error details, when applicable.
    
    Returns:
        dict[str, Any]: Canonical response containing agent metadata, action data,
        follow-up actions, warnings, and optional error details.
    """
    return {
        "status": status,
        "skill_id": "hermes-delegate",
        "agent_id": "hermes",
        "executor_id": "hermes",
        "command": "hermes-delegate",
        "action": action,
        "data": data,
        "files_modified": [],
        "follow_up_actions": follow_up_actions or [],
        "warnings": warnings or [],
        "error": error,
    }


# Worker inputs travel as argv, not interpolated into generated source.
# repr() already escapes safely and this runs via an argv list (no shell,
# no injection) -- the point of argv over interpolation is maintainability:
# no escaping behavior for the worker body to stay coupled to.
_WORKER_SOURCE = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from hermes_harness import spawn_hermes_agent\n"
    "payload = spawn_hermes_agent('executor', sys.argv[2])\n"
    "print(json.dumps(payload, default=str))\n"
)


_IS_WINDOWS = sys.platform == "win32"


def _worker_popen_kwargs() -> dict[str, Any]:
    """Configure platform-specific process-group settings for worker termination.
    
    Returns:
        dict[str, Any]: Keyword arguments for creating a worker in an independently
        terminable process group.
    """
    if _IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}  # own process group -> killable as a unit


class SpawnFunction(Protocol):
    """Structural contract for the injectable spawn_fn used by the
    ThreadPoolExecutor test path -- distinct from the real subprocess
    worker path, which always spawns via _WORKER_SOURCE regardless.
    """

    def __call__(self, role: str, task: str) -> dict[str, Any]: """
Execute a task for the specified worker role.

Parameters:
	role (str): Worker role used to execute the task.
	task (str): Task description to execute.

Returns:
	dict[str, Any]: Structured result produced by the worker.
"""
...


class _Worker:
    """A launched worker: its process plus CLAYGO temp files for its output.

    stdout/stderr are redirected to temp files rather than subprocess.PIPE.
    A chatty worker writing more than the OS pipe buffer (~64KB) would
    otherwise deadlock: the child blocks writing to a full pipe nobody is
    draining while the parent's poll loop only reads pipes after a worker
    exits. Files never fill up under the writer.
    """

    def __init__(self, task: str, pt_root: str) -> None:
        """Initialize a worker for the specified task and launch its subprocess.
        
        Parameters:
            task (str): Task to execute.
            pt_root (str): Project root containing the worker source directory.
        """
        self.task = task
        self._stdout_fh = tempfile.NamedTemporaryFile(
            mode="w+", prefix="hermes-delegate-out-", delete=False
        )
        self._stderr_fh = tempfile.NamedTemporaryFile(
            mode="w+", prefix="hermes-delegate-err-", delete=False
        )
        try:
            self.proc = subprocess.Popen(
                [sys.executable, "-c", _WORKER_SOURCE, os.path.join(pt_root, "src"), task],
                stdout=self._stdout_fh,
                stderr=self._stderr_fh,
                text=True,
                **_worker_popen_kwargs(),
            )
        except Exception:
            # Popen failed (e.g. resource exhaustion, bad interpreter path)
            # -- self.proc never got set, so nothing else will ever clean
            # these up. Close and remove both temp files ourselves before
            # re-raising, or they leak on every failed launch.
            self._stdout_fh.close()
            self._stderr_fh.close()
            for path in (self._stdout_fh.name, self._stderr_fh.name):
                try:
                    os.remove(path)
                except OSError:
                    pass
            raise

    def cleanup(self) -> None:
        """Closes the worker's output files and removes their temporary paths."""
        self._stdout_fh.close()
        self._stderr_fh.close()
        for path in (self._stdout_fh.name, self._stderr_fh.name):
            try:
                os.remove(path)
            except OSError:
                pass

    def read_output(self) -> tuple[str, str]:
        """Read and return the worker's captured standard output and standard error.
        
        Returns:
        	stdout, stderr (tuple[str, str]): The captured standard output and standard error.
        """
        self._stdout_fh.flush()
        self._stderr_fh.flush()
        with open(self._stdout_fh.name, encoding="utf-8") as f:
            stdout = f.read()
        with open(self._stderr_fh.name, encoding="utf-8") as f:
            stderr = f.read()
        return stdout, stderr


def _terminate_worker(worker: _Worker) -> None:
    """
    Terminate the worker process and its descendants, escalating to forced termination if necessary.
    
    Parameters:
    	worker (_Worker): Worker whose process should be terminated.
    """
    proc = worker.proc
    if proc.poll() is not None:
        proc.wait()
        return
    if _IS_WINDOWS:
        # /T = kill the whole process tree, /F = force. Windows has no
        # process-group signal equivalent to killpg; taskkill's recursive
        # tree-kill is the documented substitute for reaching grandchildren.
        # Unverified in this environment -- see _worker_popen_kwargs' note.
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _parse_worker_output(worker: _Worker) -> dict[str, Any]:
    """
    Parse a worker's captured output into a structured result.
    
    Parameters:
        worker (_Worker): Worker whose process output should be read.
    
    Returns:
        dict[str, Any]: Parsed JSON output, a raw-text result when the output is not valid JSON, or `{"ok": True}` when no output is produced.
    
    Raises:
        RuntimeError: If the worker exits with a nonzero status.
    """
    stdout, stderr = worker.read_output()
    if worker.proc.returncode != 0:
        detail = (stderr or stdout or "worker failed").strip()
        raise RuntimeError(detail)
    out = (stdout or "").strip()
    if not out:
        return {"ok": True}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}


def _run_subprocess_workers(
    tasks: list[str],
    *,
    pt_root: str,
    worker_timeout_sec: int,
    max_concurrent: int = 5,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Execute tasks in child processes with bounded concurrency and a shared timeout.
    
    Parameters:
        worker_timeout_sec (int): Maximum time allowed for the worker batch.
        max_concurrent (int): Maximum number of workers running simultaneously.
    
    Returns:
        tuple[list[dict[str, Any]], list[str]]: Worker result records and recommended follow-up actions.
    """
    rows: list[dict[str, Any]] = []
    follow_up: list[str] = []
    launched: list[_Worker] = []

    try:
        queue = list(tasks)
        pending: list[_Worker] = []
        deadline = time.monotonic() + worker_timeout_sec

        while queue or pending:
            while queue and len(pending) < max_concurrent:
                if time.monotonic() >= deadline:
                    # Deadline reached mid-launch -- stop starting new
                    # workers and leave the rest in queue. The queue-drain
                    # loop below reports them as "did not start" rather
                    # than silently launching more work past the deadline.
                    break
                task = queue.pop(0)
                try:
                    worker = _Worker(task, pt_root)
                except Exception as exc:  # noqa: BLE001
                    # Construction itself failed (e.g. Popen raised on
                    # resource exhaustion) -- record it as this task's
                    # error and keep going, rather than letting the
                    # exception propagate and abort every other task
                    # still queued or in flight.
                    rows.append({"task": task, "status": "error", "error": str(exc)})
                    follow_up.append(f"retry task: {task[:80]}")
                    continue
                launched.append(worker)
                pending.append(worker)

            if time.monotonic() >= deadline:
                break

            still_pending: list[_Worker] = []
            for worker in pending:
                if worker.proc.poll() is None:
                    still_pending.append(worker)
                    continue
                try:
                    payload = _parse_worker_output(worker)
                    rows.append({"task": worker.task, "status": "ok", "result": payload})
                except Exception as exc:  # noqa: BLE001
                    rows.append({"task": worker.task, "status": "error", "error": str(exc)})
                    follow_up.append(f"inspect/retry task: {worker.task[:80]}")

            pending = still_pending
            if pending or queue:
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

        for worker in pending:
            _terminate_worker(worker)
            msg = f"worker did not complete within {worker_timeout_sec}s"
            rows.append({"task": worker.task, "status": "error", "error": msg})
            follow_up.append(f"retry task: {worker.task[:80]}")

        for task in queue:
            msg = f"worker did not start within {worker_timeout_sec}s (concurrency cap)"
            rows.append({"task": task, "status": "error", "error": msg})
            follow_up.append(f"retry task: {task[:80]}")
    finally:
        for worker in launched:
            if worker.proc.poll() is None:
                _terminate_worker(worker)
            worker.cleanup()

    return rows, follow_up


def run_delegate(
    tasks: list[str],
    *,
    pt_root: str,
    worker_timeout_sec: int,
    spawn_fn: SpawnFunction | None = None,
) -> dict[str, Any]:
    """
    Execute tasks concurrently through Hermes workers and assemble a canonical delegation result.
    
    Parameters:
    	tasks (list[str]): Tasks to execute.
    	pt_root (str): Project root used by worker processes.
    	worker_timeout_sec (int): Shared timeout for worker execution.
    	spawn_fn (SpawnFunction | None): Optional worker callable used for injectable execution.
    
    Returns:
    	dict[str, Any]: Canonical result containing worker outcomes, status, warnings, and follow-up actions.
    """
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    follow_up: list[str] = []

    if spawn_fn is None:
        rows, follow_up = _run_subprocess_workers(
            tasks,
            pt_root=pt_root,
            worker_timeout_sec=worker_timeout_sec,
        )
    else:
        # Injectable path (unit tests): thread pool with cooperative release.
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 5))
        try:
            future_by_task = {
                ex.submit(spawn_fn, "executor", task): task for task in tasks
            }
            pending = set(future_by_task.keys())
            deadline = time.monotonic() + worker_timeout_sec

            while pending:
                remaining = max(0.0, deadline - time.monotonic())
                if remaining == 0:
                    break
                done, pending = concurrent.futures.wait(
                    pending,
                    timeout=remaining,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for fut in done:
                    task = future_by_task[fut]
                    try:
                        payload = fut.result()
                        rows.append({"task": task, "status": "ok", "result": payload})
                    except Exception as exc:  # noqa: BLE001
                        rows.append({"task": task, "status": "error", "error": str(exc)})
                        follow_up.append(f"inspect/retry task: {task[:80]}")

            for fut in pending:
                task = future_by_task[fut]
                fut.cancel()
                msg = f"worker did not complete within {worker_timeout_sec}s"
                rows.append({"task": task, "status": "error", "error": msg})
                follow_up.append(f"retry task: {task[:80]}")
        finally:
            ex.shutdown(wait=False, cancel_futures=True)

    rows.sort(key=lambda row: tasks.index(row["task"]))
    errors = [r for r in rows if r.get("status") == "error"]
    status = "ok"
    if errors and len(errors) < len(rows):
        status = "partial"
        warnings.append(f"{len(errors)} of {len(rows)} workers failed")
    elif errors:
        status = "error"
        error = {
            "code": "hermes_delegate_worker_error",
            "message": f"{len(errors)} worker(s) failed or timed out",
        }
        return _canonical_result(
            status=status,
            action="delegate",
            data={"workers": rows},
            follow_up_actions=follow_up or ["inspect worker errors in data.workers"],
            warnings=warnings,
            error=error,
        )
    return _canonical_result(
        status=status,
        action="delegate",
        data={"workers": rows},
        follow_up_actions=follow_up,
        warnings=warnings,
    )


def main(argv: list[str] | None = None) -> int:
    """
    Parse command-line arguments, delegate the requested tasks, and print the results.
    
    Parameters:
    	argv (list[str] | None): Optional command-line arguments; uses the process arguments when omitted.
    
    Returns:
    	int: 0 when all workers succeed, or 1 when validation fails or delegation is incomplete.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="+", help="Tasks separated by | on the shell wrapper")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--pt-root", default=os.environ.get("PT_ROOT", ""))
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("HERMES_DELEGATE_TIMEOUT_SEC", "1800")),
        help="Per-delegate wall-clock timeout in seconds (parallel workers share one deadline)",
    )
    args = parser.parse_args(argv)

    raw = " ".join(args.tasks)
    tasks = [t.strip() for t in raw.split("|") if t.strip()]
    if len(tasks) < 2 or len(tasks) > 5:
        msg = f"expected 2-5 tasks, got {len(tasks)}"
        if args.json_out:
            print(
                json.dumps(
                    _canonical_result(
                        status="error",
                        action="delegate",
                        data={},
                        follow_up_actions=["provide 2-5 pipe-separated tasks"],
                        error={"code": "hermes_delegate_invalid_tasks", "message": msg},
                    ),
                    indent=2,
                )
            )
        else:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    pt_root = args.pt_root
    if not pt_root:
        print("ERROR: PT_ROOT not set", file=sys.stderr)
        return 1

    result = run_delegate(tasks, pt_root=pt_root, worker_timeout_sec=args.timeout)
    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result["data"]["workers"], indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
