#!/usr/bin/env python3
"""Parallel PT pipeline workers via spawn_hermes_agent (hermes-delegate command)."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from typing import Any


def _canonical_result(
    *,
    status: str,
    action: str,
    data: dict[str, Any],
    follow_up_actions: list[str] | None = None,
    warnings: list[str] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
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


def run_delegate(
    tasks: list[str],
    *,
    pt_root: str,
    worker_timeout_sec: int,
    spawn_fn: Any | None = None,
) -> dict[str, Any]:
    if spawn_fn is None:
        sys.path.insert(0, os.path.join(pt_root, "src"))
        from hermes_harness import spawn_hermes_agent  # type: ignore[import-not-found]

        spawn_fn = spawn_hermes_agent

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    follow_up: list[str] = []

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
        status="ok",
        action="delegate",
        data={"workers": rows},
        warnings=warnings,
    )


def main(argv: list[str] | None = None) -> int:
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
