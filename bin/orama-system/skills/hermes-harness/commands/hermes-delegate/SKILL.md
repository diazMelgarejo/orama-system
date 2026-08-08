---
name: hermes-delegate
description: >
  (L-PT) Run 2-5 parallel PT pipeline workers via spawn_hermes_agent — NOT native
  Hermes delegate_task. Use for independent subtasks (research + coding + review).
  Each worker is a separate AIAgent.chat thread from Perpetua-Tools/hermes_harness.py.
argument-hint: "<task1> | <task2> | <task3>"
disable-model-invocation: true
---
```bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export REPO_ROOT
TASKS_RAW="$*"
export TASKS_RAW

if [[ -z "$TASKS_RAW" ]]; then
  echo "Usage: task1 | task2 | task3" >&2
  exit 1
fi

TASK_COUNT="$(python3 - <<'PY'
import os
tasks = [t.strip() for t in os.environ["TASKS_RAW"].split("|") if t.strip()]
print(len(tasks))
PY
)"
if (( TASK_COUNT < 2 || TASK_COUNT > 5 )); then
  echo "ERROR: expected 2-5 tasks, got ${TASK_COUNT}" >&2
  exit 1
fi
echo "⚡ Spawning ${TASK_COUNT} parallel L-PT workers (PT hermes_harness, not delegate_task)..."
export TASKS_RAW
python3 <<'PYEOF'
import concurrent.futures
import json
import os
import sys

WORKER_TIMEOUT_SEC = int(os.environ.get("HERMES_DELEGATE_TIMEOUT_SEC", "1800"))

def is_pt_root(path: str) -> bool:
    return (
        os.path.isdir(path)
        and not os.path.islink(path)
        and os.path.exists(os.path.join(path, ".git"))
        and os.path.isfile(os.path.join(path, "orchestrator", "fastapi_app.py"))
    )

def resolve_pt_root():
    for var in (
        "PERPETUA_TOOLS_PATH",
        "PT_HOME",
        "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT",
    ):
        v = os.environ.get(var, "")
        if v and is_pt_root(v):
            return v
    orama_root = os.environ.get(
        "ORAMA_SYSTEM_PATH",
        os.environ.get("REPO_ROOT", ""),
    )
    paths_file = os.path.join(orama_root, ".paths") if orama_root else ""
    if paths_file and os.path.isfile(paths_file):
        with open(paths_file, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PT_DIR="):
                    pt_dir = line.split("=", 1)[1].strip().strip('"')
                    if pt_dir and is_pt_root(pt_dir):
                        return pt_dir
    if orama_root:
        mother = os.path.dirname(os.path.abspath(orama_root))

        def crawl_pt(base: str, depth: int) -> str | None:
            if is_pt_root(base):
                return base
            if depth <= 0 or not os.path.isdir(base):
                return None
            try:
                for name in os.listdir(base):
                    candidate = os.path.join(base, name)
                    if not os.path.isdir(candidate):
                        continue
                    if is_pt_root(candidate):
                        return candidate
                    found = crawl_pt(candidate, depth - 1)
                    if found:
                        return found
            except OSError:
                return None
            return None

        found = crawl_pt(mother, 2)
        if found:
            return found
    home = os.path.expanduser("~")
    found = crawl_pt(home, 3)
    if found:
        return found
    return None

pt_root = resolve_pt_root()
if not pt_root:
  sys.stderr.write(
      "ERROR: Perpetua-Tools root not resolved. "
      "Set PERPETUA_TOOLS_ROOT or see sync-local-pt-checkout.md.\n"
  )
  raise SystemExit(1)

repo_root = os.environ["REPO_ROOT"]
sys.path.insert(0, os.path.join(pt_root, "src"))
from hermes_harness import spawn_hermes_agent

tasks = [t.strip() for t in os.environ["TASKS_RAW"].split("|") if t.strip()]
if not tasks:
    raise SystemExit("no tasks provided")

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
    future_by_task = {
        ex.submit(spawn_hermes_agent, "executor", task): task for task in tasks
    }
    for fut in concurrent.futures.as_completed(future_by_task):
        task = future_by_task[fut]
        try:
            payload = fut.result(timeout=WORKER_TIMEOUT_SEC)
            results.append({"task": task, "status": "ok", "result": payload})
        except concurrent.futures.TimeoutError:
            results.append({
                "task": task,
                "status": "error",
                "error": f"worker did not complete within {WORKER_TIMEOUT_SEC}s",
            })
        except Exception as exc:
            results.append({
                "task": task,
                "status": "error",
                "error": str(exc),
            })

results.sort(key=lambda row: tasks.index(row["task"]))
print(json.dumps(results, indent=2))
PYEOF
```

**Dispatch lane:** L-PT — see [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md).
Native Hermes `delegate_task` subagents (L-H1) are a different runtime; do not conflate.
