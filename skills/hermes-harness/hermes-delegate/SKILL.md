---
name: hermes-delegate
description: >
  Spawn 2-5 parallel Hermes AIAgent workers for independent subtasks.
  Use when a task has genuinely parallel workstreams (e.g. research + coding
  + review simultaneously). Each worker gets its own isolated context.
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
echo "⚡ Spawning ${TASK_COUNT} parallel Hermes workers..."
export TASKS_RAW
python3 <<'PYEOF'
import concurrent.futures
import json
import os
import sys

repo_root = os.environ["REPO_ROOT"]
sys.path.insert(0, os.path.join(repo_root, "perpetua-tools", "src"))
from hermes_harness import spawn_hermes_agent

tasks = [t.strip() for t in os.environ["TASKS_RAW"].split("|") if t.strip()]
if not tasks:
    raise SystemExit("no tasks provided")

with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
    futs = [ex.submit(spawn_hermes_agent, "executor", t) for t in tasks]
    results = [f.result() for f in concurrent.futures.as_completed(futs)]
print(json.dumps(results, indent=2))
PYEOF
```
