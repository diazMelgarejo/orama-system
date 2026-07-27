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
PERP_SCRIPT="$(git rev-parse --show-toplevel)/perpetua-tools/src/hermes_harness.py"
IFS='|' read -ra TASKS <<< "$*"
echo "⚡ Spawning ${#TASKS[@]} parallel Hermes workers..."
python3 - <<'PYEOF'
import concurrent.futures, sys, json, os
sys.path.insert(0, "$(git rev-parse --show-toplevel)/perpetua-tools/src")
from hermes_harness import spawn_hermes_agent
tasks = [t.strip() for t in """$*""".split("|") if t.strip()]
with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
    futs = [ex.submit(spawn_hermes_agent, "executor", t) for t in tasks]
    results = [f.result() for f in concurrent.futures.as_completed(futs)]
print(json.dumps(results, indent=2))
PYEOF
```
