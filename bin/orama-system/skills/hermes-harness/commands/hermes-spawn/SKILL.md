---
name: hermes-spawn
description: >
  (L-PT) Start, stop, or check the Perpetua-Tools hermes_harness.py background
  session (PID-file lifecycle). Not native Hermes delegate_task (L-H1) and not
  fleet cursor-agent dispatch (L-Fleet). Requires credentials in the process
  environment; missing variables fail clearly (no automatic .env loading).
  Activates for starting, stopping, or checking a background Hermes/PT session.
argument-hint: "<start|stop|status> [task description]"
version: "1.0"
compatibility: Claude, Hermes, Codex, Cursor
allowed-tools: bash
triggers:
  - hermes-spawn
  - start hermes session
  - background hermes task
disable-model-invocation: true
---
```bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
exec bash "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh" "$@"
```

**Dispatch lane:** L-PT — [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md)

## Purpose

Control the lifecycle (start/stop/status) of a single background
`hermes_harness.py` session running against Perpetua-Tools, tracked by a
PID file — not a foreground call, and not native Hermes `delegate_task`.

## When to Use

- Kicking off a long-running PT/hermes background task you don't want to
  block the current session on.
- Checking whether a session is already running before starting a second
  one (starting over an active session fails loudly, it does not queue).
- Stopping a session cleanly so its PID file doesn't go stale.

## Inputs

- Required: `action` — one of `start`, `stop`, `status` (defaults to
  `status` if omitted).
- Required for `start` only: a task description (everything after
  `start` is joined as the task text).
- Optional: `HERMES_SPAWN_SESSION` env var — session id, must match
  `[a-zA-Z0-9_-]+` (default `default`). Set this to run more than one
  session concurrently.
- Optional: `--json` flag — machine-readable output on stdout instead of
  the human-readable one-liner (human-readable status still goes to
  stderr for operator visibility even in JSON mode).

## Procedure

1. Resolve the Perpetua-Tools root (see
   [`../scripts/resolve_perp_harness.sh`](../scripts/resolve_perp_harness.sh))
   — fails closed with a clear error if not found.
2. Resolve the PID/lock file paths under `$XDG_RUNTIME_DIR` (or
   `$HOME/.cache` as fallback), keyed by session id.
3. Dispatch on `action`:
   - `start` — refuse if a live PID is already tracked; otherwise launch
     `hermes_harness.py` in the background, verify it's still alive after
     1s, and write the PID file.
   - `stop` — send `SIGTERM` to the tracked PID, wait up to 2s for exit,
     remove the PID file.
   - `status` — report whether the tracked PID is a live, verified
     `hermes_harness.py` process.

## Example

```bash
# Start a background session, then confirm it's running
bin/orama-system/skills/hermes-harness/hermes-spawn/SKILL.md start "summarize open PRs"
bin/orama-system/skills/hermes-harness/hermes-spawn/SKILL.md status
```

Full copy-paste walkthrough with expected output at every step:
[`../references/quickstart.md`](../references/quickstart.md).

## Output Contract

Human-readable (default):

```text
🚀 Spawning Hermes agent for: <task>
✅ Hermes started (pid <N>, session <id>)
```

`--json` (status action):

```json
{"pid": 12345, "session": "default", "running": true}
```

## Gotchas

- `status` with no active session exits non-zero (`1`) — this is a normal
  "nothing running" result, not a failure to be retried.
- A stale PID file (recorded PID no longer matches the expected process)
  is reported as an error on `status`, not silently cleaned up — run
  `stop` to clear it.
- `HERMES_SPAWN_SESSION` is validated strictly; a session id with `..` or
  characters outside `[a-zA-Z0-9_-]` is rejected before anything runs.
- Requires real credentials in the process environment already — this
  script does not auto-load `.env` files.

## Boundaries

### Always Do

- Check `status` before `start` when uncertain whether a session is
  already active for this session id.
- Use a distinct `HERMES_SPAWN_SESSION` for concurrent sessions instead
  of racing the shared `default` session id.

### Ask First

- Before setting `HERMES_SPAWN_SESSION` to something another process or
  operator might already be using for a live session.

### Never Do

- Never treat a non-zero exit from `status` (no active session) as an
  error condition to retry against — it is a normal result.
- Never delete or hand-edit the PID file directly; use `stop` so the
  tracked process is actually signaled first.

## See Also

- [`../references/quickstart.md`](../references/quickstart.md) — first-run walkthrough
- [`../hermes-delegate/SKILL.md`](../hermes-delegate/SKILL.md) — parallel-worker variant
- [`../hermes-orama/SKILL.md`](../hermes-orama/SKILL.md) — 5-stage pipeline variant
- [`../scripts/resolve_perp_harness.sh`](../scripts/resolve_perp_harness.sh) — PT-root resolution this depends on
