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
waits up to `CONTAINMENT_TIMEOUT_SECONDS` (5.0s), and appends one
additional lifecycle line (still `status=cancelled`) with:

| Field | Values | Meaning |
|---|---|---|
| `worker_kind` | `cli` \| `in-process` | `cli` when a direct child was registered for the job. |
| `containment_state` | `verified` \| `unresolved` \| `not-applicable` | Direct-child outcome after cancel. |

- `not-applicable`: no direct CLI child exists for this job.
- `verified`: a registered direct child has exited (`returncode is not None`).
  Calling `terminate()` is not sufficient.
- `unresolved`: a direct child was registered, but exit was not confirmed
  within `CONTAINMENT_TIMEOUT_SECONDS`.

`worker_kind` is derived by Perpetua from the execution path (`cli` only when a
direct child was registered). Callers cannot submit or override it.

`verified` certifies only the direct child exited, not grandchildren or detached
helpers. Never persist PID, argv, cwd, env, stdout, or stderr on these events.

Cancel confirmation (`CANCEL_CONFIRM_TIMEOUT_SECONDS`) and containment
confirmation (`CONTAINMENT_TIMEOUT_SECONDS`) are separate bounds. v1 sets them
to the same duration (5.0s). Containment waits use a monotonic clock.

A failure while writing the containment annotation does not revoke durable
`cancelled`. The supervisor logs the failure at WARNING. If the annotation
never lands, orama applies the mixed-deploy rule (absent `containment_state`
may still allow restore). That is intentional: cancellation finality beats
telemetry persistence; operators rely on logs for annotation gaps.

### v1 edge cases (documented, not process-tree scope)

| Case | Perpetua behavior | Orama rollback |
|---|---|---|
| Cancel during `create_subprocess_exec` before `note_child` | Shield creation, await the spawned process, register, re-raise cancel; supervisor containment records `cli` + outcome | Uses cancel body when present; absent fields → mixed deploy |
| `note_child` refuses to replace a still-running first process | Identity policy: keep first live mapping | Containment follows whichever child was registered |
| Containment annotation write fails after durable `cancelled` | `terminal_state` stays `cancelled`; WARNING log; no PID/argv on event | Missing `containment_state` → mixed-deploy restore allowed |

Process-tree reaping and grandchildren remain v2 only.

## Orama rollback predicate (v1)

One function, `cancellation_allows_restore`, owns the decision:

| Worker | Terminal state | Containment state | Restore |
|---|---|---|---|
| CLI | cancelled | verified | Yes |
| CLI | cancelled | not-applicable | Yes |
| CLI | cancelled | unresolved | No |
| CLI | cancelled | any other present value | No |
| CLI | cancelled | absent | Yes, mixed deploy |
| non-CLI | cancelled | any or absent | Yes |
| any | not cancelled | any | No |
| any | missing | any | No |

`cancel_requested` must also be true. Once a partially dispatched swarm has an
accepted job whose cancellation cannot be positively established as
rollback-safe, the approval claim remains consumed. The same rule covers
ambiguous submission and cancel transport failures.

## Non-retryable outcomes (orama fail-closed)

- Cancellation acknowledgement without `terminal_state == "cancelled"`.
- Ambiguous submission (transport/timeout) on a failed role.
- Accepted job with no identifiable `job_id` (`unknown:<role>` orphan).
- Cancel failure or orphan after rollback (`orphaned_jobs`, `launch_blocked`).
- CLI jobs reporting present `containment_state` other than `verified` or
  `not-applicable`.

## v2 (documentation only — not implemented)

Do not redefine v1 `verified` as process-tree containment. A later contract may
add `containment_scope` (`direct-child`, `process-tree`, `process-group`) and
may distinguish:

- `unresolved`: containment was attempted and exit was not confirmed.
- `unsupported`: this execution type has no containment capability.

v1 does not emit `unsupported`; non-CLI work uses `not-applicable`.

Also deferred: grandchild tracking, OS-specific job objects, persistent child
identity, Looking Glass UI, new SSE event types, and Periscope schema
extensions. Looking Glass, when built, reads redacted semantic fields
(`worker_kind`, `terminal_state`, `containment_state`, `containment_scope`) and
does not read PID, argv, environment, or process output.

## Cross-repository rule

**Perpetua** answers: did this job reach terminal cancellation, does it still
hold an admission slot, and (v1) did the direct CLI child exit after cancel?

**Orama** answers: may this swarm approval be reused?

Neither repository answers the other's question in full.
