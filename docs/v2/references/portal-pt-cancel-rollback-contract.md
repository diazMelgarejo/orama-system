# Portal ↔ Perpetua cancel and rollback contract

**Status:** v1 direct-child containment implemented (lockstep follow-up to PR #374
and PR #414). Process-tree reaping and expanded telemetry remain v2
documentation only.

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
`cancelled`. Perpetua retries the annotation a bounded number of times. If a
direct child remains registered after the final failure, the public
`has_registered_child()` predicate is true and the cancel HTTP body is
`worker_kind=cli` with `containment_state=unresolved` even when the lifecycle
event has no annotation. Orama's `cancellation_allows_restore` therefore fails
closed and does not restore the preview. The mixed-deploy rule applies only
when **both** containment fields are absent and no direct-child mapping
remains, such as a true in-process cancellation on an older Perpetua
deployment.

### v1 edge cases (documented, not process-tree scope)

| Case | Perpetua behavior | Orama rollback |
|---|---|---|
| Cancel during `create_subprocess_exec` before `note_child` | Shield creation, await the spawned process, register, re-raise cancel; supervisor containment records `cli` + outcome | Uses cancel body when present; absent fields → mixed deploy |
| `note_child` refuses to replace a still-running first process | Identity policy: keep first live mapping | Containment follows whichever child was registered |
| Containment annotation write fails after durable `cancelled` | Retry the annotation; after final failure retain the child mapping and return `cli` / `unresolved`; no PID/argv on event | Fail closed; preview remains consumed |

Process-tree reaping and grandchildren remain v2 only.

## Orama rollback predicate (v1)

One function, `cancellation_allows_restore`, owns the decision:

| Worker | Terminal state | Containment state | Restore |
|---|---|---|---|
| both fields absent | cancelled | absent | Yes, mixed deploy |
| CLI | cancelled | verified | Yes |
| in-process | cancelled | not-applicable | Yes |
| CLI | cancelled | not-applicable | No |
| CLI | cancelled | unresolved or any other value | No |
| CLI | cancelled | absent while `worker_kind` is present | No |
| in-process | cancelled | any value other than not-applicable, or absent | No |
| unknown or any other kind | cancelled | any | No |
| containment present, `worker_kind` absent | cancelled | any | No |
| any | not cancelled | any | No |
| any | missing | any | No |

`cancel_requested` must also be true. Once a partially dispatched swarm has an
accepted job whose cancellation cannot be positively established as
rollback-safe, the approval claim remains consumed. The same rule covers
ambiguous submission and cancel transport failures.

## Orama cancel HTTP timeout

Portal cancel POSTs (swarm-launch rollback and `POST /api/jobs/{job_id}/cancel`)
use `PT_CANCEL_HTTP_TIMEOUT_S` (15.0s). That budget covers Perpetua
`CANCEL_CONFIRM_TIMEOUT_SECONDS` (5.0s) plus `CONTAINMENT_TIMEOUT_SECONDS`
(5.0s) plus annotation retries and I/O. Shorter httpx timeouts fail closed as
orphaned/unresolved cancellations.

## Non-retryable outcomes (orama fail-closed)

- Cancellation acknowledgement without `terminal_state == "cancelled"`.
- Ambiguous submission (transport/timeout) on a failed role.
- Accepted job with no identifiable `job_id` (`unknown:<role>` orphan).
- Cancel failure or orphan after rollback (`orphaned_jobs`, `launch_blocked`).
- Any present containment pair other than `cli` / `verified` or
  `in-process` / `not-applicable`. Legacy restore applies only when both
  `worker_kind` and `containment_state` are absent.

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

### Recommendations for Future Scope (v2)

To advance process containment safely without introducing regression or security debt,
the v2 specification mandates the following hardening requirements and invariants:

#### 1. Hardening Requirements for Future Shape

- **Containment Scope Enumeration:** Introduce explicit `containment_scope` enum:
  - `direct-child`: certified only for the direct subprocess spawned by supervisor.
  - `process-group`: certified for POSIX process group / Windows Job Object boundary.
  - `process-tree`: certified across the complete transitive process tree.
- **Two-Phase Signal Escalation Protocol:**
  - Phase 1: Graceful `SIGTERM` issued to process group or direct child.
  - Phase 2: Monotonic timer wait (bounded by `CONTAINMENT_TIMEOUT_SECONDS`).
  - Phase 3: Escalation to `SIGKILL` on timeout before final containment evaluation.
- **Structured Telemetry Payload Extensions:**
  - `escalation_stage`: `sigterm` | `sigkill` (records whether escalation was required).
  - `reaped_count`: integer tally of terminated child/grandchild processes.
  - `containment_duration_ms`: monotonic elapsed time spent in containment wait.
- **OS-Level Containment Mechanisms:**
  - *POSIX / Linux / macOS:* Isolate CLI jobs in dedicated process groups using
    `os.setpgid(0, 0)` at spawn, allowing targeted `os.killpg(pgid, signal)` without
    affecting the parent supervisor or unrelated worker tasks. Optional Linux cgroups v2
    (`cgroup.kill`) or `prctl(PR_SET_PDEATHSIG, SIGKILL)` where kernel support exists.
  - *Windows:* Bind worker processes to Win32 Job Objects with
    `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` to ensure automatic tree termination.

#### 2. Security Invariants for v2

- **Zero Process Internals Leak Invariant:** Strict, unconditional exclusion of
  `pid`, `argv`, `cmdline`, `env`, `cwd`, `stdout`, and `stderr` across all external
  interfaces (REST endpoints, SSE streams, GossipBus event lines, Periscope trajectory
  records, and Looking Glass UI). Only redacted semantic metadata may cross boundaries.
- **Fail-Closed Rollback Invariant:** If `containment_state` is unrecognized or evaluates to
  `unresolved`, `unsupported`, or timeout, Orama's `cancellation_allows_restore()` must
  fail closed. The approval claim must remain consumed to prevent concurrent or duplicate
  execution of uncontained work.
- **Signal Boundary Isolation Invariant:** Signal escalation (`os.killpg`) must verify PGID
  ownership before execution to prevent cross-process signal injection or accidental
  termination of sibling tasks.
- **Durable Cancellation Inviolability:** Any failure during grandchild discovery, process-group
  cleanup, or telemetry serialization must never roll back or revoke the durable
  `status: cancelled` state in the supervisor's lifecycle store.
- **Mixed-Deploy Tolerance Invariant:** All new telemetry fields (`containment_scope`,
  `escalation_stage`, `reaped_count`) must remain optional / nullable in JSON envelopes to
  ensure seamless rolling upgrades across heterogeneous cluster nodes.

## Cross-repository rule

**Perpetua** answers: did this job reach terminal cancellation, does it still
hold an admission slot, and (v1) did the direct CLI child exit after cancel?

**Orama** answers: may this swarm approval be reused?

Neither repository answers the other's question in full.
