---
name: hermes-orama
description: >
  (L-PT) Run the Orama 5-stage pipeline via Perpetua-Tools hermes_harness.py —
  sequential AIAgent.chat stages, not native Hermes delegate_task children.
  Context → Architect → Refiner → Executor/Verifier (parallel) → Crystallizer.
  Activates for running a single task through the full 5-stage Orama pipeline.
argument-hint: "<task description>"
version: "1.0"
compatibility: Claude, Hermes, Codex, Cursor
allowed-tools: bash, python
triggers:
  - hermes-orama
  - orama 5-stage pipeline
  - full methodology on a single task
disable-model-invocation: true
---
```bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# shellcheck source=../../scripts/resolve_perp_harness.sh
source "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"
PERP_SCRIPT="$(resolve_perp_harness_script)"
TASK="$*"
[ -z "$TASK" ] && echo "Usage: /hermes-orama <task description>" && exit 1
echo "🧠 L-PT: Orama 5-stage pipeline (PT hermes_harness, not delegate_task): $TASK"
python3 "$PERP_SCRIPT" "$TASK"
```

**Dispatch lane:** L-PT — [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md)

## Purpose

Run the full Orama 5-stage methodology (Context → Architect → Refiner →
Executor/Verifier in parallel → Crystallizer) against a single task,
foreground, via Perpetua-Tools `hermes_harness.py` — sequential
`AIAgent.chat` stages, not native Hermes `delegate_task` children.

## When to Use

- A single task genuinely needs the full staged methodology (context
  gathering, design, refinement, parallel execute+verify, crystallize),
  not just a quick answer or a background session.
- You want one task run through the pipeline in the foreground and want
  to see it complete before moving on — for a background/non-blocking
  run instead, use `hermes-spawn`; for 2-5 independent parallel tasks
  instead, use `hermes-delegate`.

## Inputs

- Required: a single task description (everything after the command is
  joined as the task text; empty input is rejected with a usage message).
- Requires: Perpetua-Tools root resolvable (see
  [`../scripts/resolve_perp_harness.sh`](../scripts/resolve_perp_harness.sh)).

## Procedure

1. Resolve the Perpetua-Tools `hermes_harness.py` script path — fails
   closed with a clear error if PT isn't found.
2. Print the task being run.
3. Invoke `hermes_harness.py` directly, foreground, with the task text —
   the script itself drives all 5 stages sequentially/in-parallel as
   appropriate; this wrapper does not orchestrate the stages itself.

## Example

```bash
bin/orama-system/skills/hermes-harness/hermes-orama/SKILL.md \
  "design and implement a rate limiter for the /health endpoint"
```

## Output Contract

Human-readable only — this wrapper prints one status line, then streams
whatever `hermes_harness.py` itself prints for the run (stage transitions,
final crystallized result). There is no `--json` mode on this wrapper
(unlike `hermes-spawn`/`hermes-delegate`); if you need structured output,
use `hermes-delegate` for a single task (`task1 | task1` is invalid — it
requires 2-5 distinct tasks) or parse `hermes_harness.py`'s own output
directly.

## Gotchas

- This call blocks in the foreground until the full 5-stage run
  completes — for long tasks, prefer `hermes-spawn start` instead so it
  doesn't tie up the current session.
- An empty task description exits immediately with a usage message; it
  does not silently no-op or prompt for input.

## Boundaries

### Always Do

- Use `hermes-spawn start` instead when the task is long-running and
  shouldn't block the current session.
- Confirm the task genuinely needs all 5 stages before reaching for this
  over a direct answer.

### Ask First

- Before invoking `hermes_harness.py` for a task whose Executor stage may
  modify files, commit, deploy, delete, or change account settings —
  obtain explicit confirmation before dispatch, not after. This is
  separate from, and precedes, reviewing the crystallized result: the
  5-stage pipeline runs Executor/Verifier before Crystallizer, so by the
  time a crystallized result exists to review, any side effect has
  already happened.

### Never Do

- Never assume the run completed successfully just because the command
  returned — check the printed crystallized result, not just the exit
  code, since `hermes_harness.py` is the source of truth for success/failure
  here, not this thin wrapper.

## See Also

- [`../hermes-spawn/SKILL.md`](../hermes-spawn/SKILL.md) — background session variant
- [`../hermes-delegate/SKILL.md`](../hermes-delegate/SKILL.md) — 2-5 parallel independent workers
- [`../references/quickstart.md`](../references/quickstart.md) — first-run PT setup walkthrough
