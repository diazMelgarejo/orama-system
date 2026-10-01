# Portal ↔ Perpetua cancel and rollback contract

**Status:** Documentation only (lockstep PR #374 / #414). No runtime change in
this document.

## Purpose

Define what orama may infer from a Perpetua job cancellation during swarm
dispatch rollback, and what remains explicitly out of scope until a later
containment workstream.

## States (do not conflate)

```text
cancel requested
    ≠ supervisor task cancelled
    ≠ child process terminated
    ≠ process tree reaped
    ≠ execution side effects ceased
```

Orama treats **supervisor cancellation finality** and **external process
containment** as distinct. This file records both; only the first is
implemented for portal rollback on the lockstep branch.

## Rollback-final cancellation (implemented on lockstep branch)

For portal preview restoration after a partial swarm dispatch, each accepted
Perpetua job must satisfy:

1. HTTP cancel succeeds with `cancel_requested: true`.
2. `terminal_state` is exactly `cancelled` (durable lifecycle event persisted).
3. On the Perpetua side, the cancelled worker task no longer occupies
   `OrchestrationSupervisor._active` (identity-safe removal in
   `cancel_with_terminal_state()` for pre-start cancellation; `_run_worker()`
   `finally` for running tasks).

Orama checks (1) and (2) only. (3) is a Perpetua invariant; violating it
exhausts `MAX_THREADS` and is covered by Perpetua regression tests.

## Non-retryable outcomes (orama fail-closed)

- Cancellation acknowledgement without `terminal_state == "cancelled"`.
- Ambiguous submission (transport/timeout) on a failed role.
- Accepted job with no identifiable `job_id` (`unknown:<role>` orphan).
- Cancel failure or orphan after rollback (`orphaned_jobs`, `launch_blocked`).
- CLI jobs where containment is required but not reported (future contract).

## Future containment (not in PR #414 / #374)

CLI workers may spawn OS subprocesses (`worker_registry`, `dangerous_workers`).
Supervisor task cancellation does not prove those processes exited. A later
workstream will expose redacted containment fields (for example
`containment_state: verified|unresolved|unsupported`) on job observations
and portal monitors. Until then, orama must not infer containment from
`CANCELLED` alone.

## Assertion surfaces (for later implementation)

| Layer | Seam |
|---|---|
| Perpetua | `supervisor.py`, `worker_registry.py`, `periscope_adapter.py` |
| Orama portal | `_render_supervisor_jobs_section`, `/api/status`, notification SSE |
| Design | `docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` |

## Cross-repository rule

**Perpetua** answers: did this job reach terminal cancellation, and does it
still hold an admission slot?

**Orama** answers: may this swarm approval be reused?

Neither repository answers the other's question.
