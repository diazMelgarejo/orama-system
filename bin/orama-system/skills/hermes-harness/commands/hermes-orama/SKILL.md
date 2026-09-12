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
allowed-tools: Bash(git rev-parse *) Bash(bin/orama-system/skills/hermes-harness/scripts/hermes_orama.sh *)
triggers:
  - hermes-orama
  - orama 5-stage pipeline
  - full methodology on a single task
disable-model-invocation: true
---
```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
exec "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/hermes_orama.sh" "$@"
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

1. Invoke the repository-owned `scripts/hermes_orama.sh` launcher, which resolves
   the Perpetua-Tools `hermes_harness.py` script path and fails closed if PT isn't found.
2. The launcher prints the task being run.
3. The launcher invokes `hermes_harness.py` foreground, with the task text —
   the script itself drives all 5 stages sequentially/in-parallel as
   appropriate; this wrapper does not orchestrate the stages itself.

## Example

```text
/hermes-orama \
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

- Obtain separate explicit confirmation for the launcher/remote dispatch and
  for the exact task scope.
- Obtain explicit confirmation before a task may directly modify files.
- Never treat read-only launch approval as approval for later side effects.
- Never allow commit, deploy, delete, or account-setting changes without a
  separate explicit confirmation. This precedes crystallized-result review:
  Executor/Verifier run before Crystallizer.

### Never Do

- Never assume the run completed successfully just because the command
  returned — check the printed crystallized result, not just the exit
  code, since `hermes_harness.py` is the source of truth for success/failure
  here, not this thin wrapper.

## See Also

- [`../hermes-spawn/SKILL.md`](../hermes-spawn/SKILL.md) — background session variant
- [`../hermes-delegate/SKILL.md`](../hermes-delegate/SKILL.md) — 2-5 parallel independent workers
- [`../references/quickstart.md`](../references/quickstart.md) — first-run PT setup walkthrough
