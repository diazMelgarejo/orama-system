---
name: hermes-delegate
description: >
  (L-PT) Run 2-5 parallel PT pipeline workers via spawn_hermes_agent — NOT native
  Hermes delegate_task. Use for independent subtasks (research + coding + review).
  Each worker is a separate AIAgent.chat thread from Perpetua-Tools/hermes_harness.py.
  Activates for fanning out 2-5 independent subtasks to parallel PT workers.
argument-hint: "<task1> | <task2> | <task3> [--json]"
version: "1.0"
compatibility: Claude, Hermes, Codex, Cursor
allowed-tools: bash, python
triggers:
  - hermes-delegate
  - parallel PT workers
  - fan out independent subtasks
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

## Purpose

Fan a task out to 2-5 independent PT `hermes_harness.py` workers in
parallel, each its own `AIAgent.chat` thread — for genuinely independent
subtasks (e.g. research + coding + review), not for a single sequential
pipeline (see `hermes-orama` for that).

## When to Use

- The work splits cleanly into 2-5 subtasks with no dependency between
  them.
- You want results collected and reported together rather than run one
  at a time.

## Inputs

- Required: 2 to 5 task descriptions, pipe-separated (`task1 | task2 |
  task3`). Fewer than 2 or more than 5 is rejected before anything runs.
- Optional: `--json` flag — full canonical result object on stdout
  instead of just the worker list.
- Optional: `HERMES_DELEGATE_TIMEOUT_SEC` env var — per-worker wall-clock
  timeout in seconds, shared across all parallel workers (default 1800).
- Requires: Perpetua-Tools root resolvable (see
  [`../scripts/resolve_perp_harness.sh`](../scripts/resolve_perp_harness.sh)).

## Procedure

1. Parse and validate the pipe-separated task list (2-5 tasks required).
2. Resolve `PT_ROOT` via [`resolve_pt_root`](../scripts/resolve_perp_harness.sh)
   — fail closed with a clear error if not found.
3. Launch one worker per task concurrently, each a separate
   `AIAgent.chat` thread against `hermes_harness.py`, sharing one
   wall-clock deadline.
4. Collect results in original task order; if some workers failed, report
   `partial`; if all failed, report `error`.

## Example

```text
/hermes-delegate research the current caching strategy | write a test for the cache eviction bug | review the fix once it's written
```

For direct shell use (bypassing the slash command), the underlying
implementation is `scripts/hermes_delegate.py`:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/hermes_delegate.py \
  "research the current caching strategy" \
  "write a test for the cache eviction bug" \
  "review the fix once it's written"
```

## Output Contract

Default (human-readable): the `data.workers` array only, one row per
task, in task order — each row carries at least `task` and `status`.

```json
[
  {"task": "research the current caching strategy", "status": "ok"},
  {"task": "write a test for the cache eviction bug", "status": "ok"}
]
```

`--json`: the full canonical envelope —

```json
{
  "status": "ok|partial|error",
  "skill_id": "hermes-delegate",
  "data": {"workers": ["..."]},
  "warnings": [],
  "follow_up_actions": []
}
```

## Gotchas

- Task count is strictly 2-5 — a single task or more than 5 is rejected
  up front, not silently clamped.
- `status: "partial"` means SOME workers failed, not all — check
  `data.workers[].status` per-row before assuming the whole run succeeded.
- All workers share one timeout deadline; a slow worker can starve
  others' remaining budget under load, not just its own.

## Boundaries

### Always Do

- Verify the tasks are genuinely independent before delegating — shared
  state or ordering dependencies between them will race.
- Check `data.workers[].status` per row, not just the top-level `status`,
  before trusting a `partial` result as "good enough."

### Ask First

- Before raising `HERMES_DELEGATE_TIMEOUT_SEC` significantly for
  long-running workers that could tie up shared PT capacity.

### Never Do

- Never delegate a task count outside 2-5 by working around the
  validation (e.g. padding with no-op tasks) — split into multiple
  delegate calls instead.
- Never assume `status: "ok"` at the top level means every individual
  worker succeeded without checking the per-row detail.

## See Also

- [`../hermes-spawn/SKILL.md`](../hermes-spawn/SKILL.md) — single background session variant
- [`../hermes-orama/SKILL.md`](../hermes-orama/SKILL.md) — sequential 5-stage pipeline variant
- [`../references/quickstart.md`](../references/quickstart.md) — first-run PT setup walkthrough
