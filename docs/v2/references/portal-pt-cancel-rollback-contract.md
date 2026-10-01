# Portal ↔ Perpetua cancel and rollback contract

**Status:** v1 direct-child containment implemented (lockstep follow-up to PR #374 /
#414). Process-tree reaping and expanded telemetry remain v2 documentation only.

## Purpose

Define what orama may infer from a Perpetua job cancellation during swarm
dispatch rollback, and what remains explicitly out of scope until v2.

## States (do not conflate)

```text
cancel requested
    ≠ supervisor task cancelled
    ≠ direct CLI child exited          (v1: containment_state)
    ≠ process tree reaped              (v2)
    ≠ execution side effects ceased
```

Orama treats **supervisor cancellation finality** and **direct CLI child
containment** as distinct. v1 exposes the second only through two redacted
fields on the cancel HTTP body and matching lifecycle events.

## Rollback-final cancellation (supervisor)

For portal preview restoration after a partial swarm dispatch, each accepted
Perpetua job must satisfy:

1. HTTP cancel succeeds with `cancel_requested: true`.
2. `terminal_state` is exactly `cancelled` (durable lifecycle event persisted).
3. On the Perpetua side, the cancelled worker task no longer occupies
   `OrchestrationSupervisor._active` (identity-safe removal in
   `cancel_with_terminal_state()` for pre-start cancellation; `_run_worker()`
   `finally` for running tasks).

Orama checks (1) and (2) for every job. (3) is a Perpetua invariant.

## v1 direct-child containment (Perpetua)

Perpetua registers the **direct** subprocess created by `codex`, `gemini`, and
`agy` workers (`DANGEROUS_CLI_BACKENDS`). After durable `cancelled` and
admission cleanup, the supervisor attempts `terminate()` on that object only,
waits up to `CANCEL_CONFIRM_TIMEOUT_SECONDS` (5.0s), and appends one
additional lifecycle line (still `status=cancelled`) with:

| Field | Values | Meaning |
|---|---|---|
| `worker_kind` | `cli` \| `in-process` | `cli` when a direct child was registered for the job. |
| `containment_state` | `verified` \| `unresolved` \| `not-applicable` | Direct-child outcome after cancel. |

- `verified`: registered direct child has `returncode is not None`.
- `unresolved`: child was registered and exit was not observed within the bound.
- `not-applicable`: no direct child was registered (echo, HTTP, or CLI cancelled
  before `create_subprocess_exec` returned).

`verified` certifies only the direct child exited, not grandchildren or detached
helpers. Never persist PID, argv, cwd, env, stdout, or stderr on these events.

## Orama rollback predicate (v1)

Today's predicate remains: restore only when `cancel_requested is True` and
`terminal_state == "cancelled"`.

Additionally, **block** preview restore when:

```text
worker_kind == "cli"
and containment_state is present
and containment_state is neither "verified" nor "not-applicable"
```

Mixed deploy: when `containment_state` is **absent**, orama keeps the legacy
rule (`terminal_state == "cancelled"` only). `worker_kind=in-process` with any
containment value does not add a CLI gate.

## Non-retryable outcomes (orama fail-closed)

- Cancellation acknowledgement without `terminal_state == "cancelled"`.
- Ambiguous submission (transport/timeout) on a failed role.
- Accepted job with no identifiable `job_id` (`unknown:<role>` orphan).
- Cancel failure or orphan after rollback (`orphaned_jobs`, `launch_blocked`).
- CLI jobs reporting present `containment_state` other than `verified` or
  `not-applicable`.

## v2 (documentation only — not implemented)

- Process-group / tree reaping and OS-specific job objects.
- Looking Glass UI columns, new SSE event types, `unsupported` as a separate
  public wire value, `containment_observed_at`, and Periscope schema extensions.
- Containment for non-CLI subprocesses (`gbrain_search`, MCP stdio, etc.).

## Cross-repository rule

**Perpetua** answers: did this job reach terminal cancellation, does it still
hold an admission slot, and (v1) did the direct CLI child exit after cancel?

**Orama** answers: may this swarm approval be reused?

Neither repository answers the other's question in full.
