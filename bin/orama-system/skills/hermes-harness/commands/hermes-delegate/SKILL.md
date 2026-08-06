---
name: hermes-delegate
description: >
  (L-PT) Run 2-5 parallel PT pipeline workers via spawn_hermes_agent — NOT native
  Hermes delegate_task. Use for independent subtasks (research + coding + review).
  Each worker is a separate AIAgent.chat thread from Perpetua-Tools/hermes_harness.py.
argument-hint: "<task1> | <task2> | <task3> [--json]"
disable-model-invocation: true
---
```bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCRIPT="${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/hermes_delegate.py"
JSON_ARGS=()
TASKS_PART=()

for arg in "$@"; do
  case "$arg" in
    --json) JSON_ARGS+=(--json) ;;
    *) TASKS_PART+=("$arg") ;;
  esac
done

TASKS_RAW="${TASKS_PART[*]:-}"
export TASKS_RAW
if [[ -z "$TASKS_RAW" ]]; then
  echo "Usage: task1 | task2 | task3 [--json]" >&2
  exit 1
fi

# shellcheck source=../../scripts/resolve_perp_harness.sh
source "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"
PT_ROOT="$(resolve_pt_root || true)"
if [[ -z "$PT_ROOT" ]]; then
  echo "ERROR: Perpetua-Tools root not resolved. Set PERPETUA_TOOLS_ROOT or see ../../../oramasys-method/references/sync-local-pt-checkout.md." >&2
  exit 1
fi
export PT_ROOT

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

if [[ ${#JSON_ARGS[@]} -eq 0 ]]; then
  echo "⚡ Spawning ${TASK_COUNT} parallel L-PT workers (PT hermes_harness, not delegate_task)..." >&2
fi

exec python3 "$SCRIPT" "${JSON_ARGS[@]}" "$TASKS_RAW"
```

**Dispatch lane:** L-PT — see [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md).
Native Hermes `delegate_task` subagents (L-H1) are a different runtime; do not conflate.
