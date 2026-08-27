# MiniGraph Observer Fan-Out — Execution Addendum

**Date:** 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Status:** in execution  
**Canonical addendum:**
[`../58-minigraph-observer-pattern-library-reconciliation.md`](
../58-minigraph-observer-pattern-library-reconciliation.md)

## Why this addendum exists

The earlier R2 plan correctly removed duplicate graph schedulers, but it treated
`asteps()` as sufficient for every observer. That is incomplete.

`asteps()` is a sanitized pull stream. Multiple simultaneous consumers need one
rich observation drain plus fan-out.

## R2.1 — Rich observation contract

Implement in `oramasys/perpetua-core` PR #1:

```text
GraphObservation
  event: GraphEvent
  state: PerpetuaState
  delta: dict | None
```

Requirements:

- `_run()` remains the sole traversal loop;
- `aobserve()` exposes observations without duplicating scheduling;
- `asteps()` projects observations to `GraphEvent`;
- `ainvoke()` returns final state by draining observations;
- `GraphEvent` remains free of state/delta payloads.

## R2.2 — Plugin multicast adapter

Add a plugin-layer `GraphPlugin` protocol and dispatcher.

```text
one aobserve() drain
        |
        v
run_with_plugins()
  ├─ Checkpointer
  ├─ Tracer
  ├─ Audit
  └─ other trusted observers
```

Default behavior:

- deterministic registration-order delivery;
- sync or async listener callbacks;
- fail-closed on listener failure;
- no detached background tasks by default;
- no plugin traversal through `_nodes` / `_edges`.

## R2.3 — Checkpointer integration

Make `SqliteCheckpointer` observation-compatible.

Initial boundary:

```text
node.end
  -> save successful post-merge state
```

This does NOT complete durable resume. R4 still owns:

- checkpoint lineage;
- graph/version identity;
- state schema identity;
- replay compatibility;
- idempotency / effect dedupe.

## R2.4 — Required regression proof

At minimum, one run MUST prove:

```text
Checkpointer + Tracer
same CompiledGraph execution
both receive every relevant observation
neither races/drains the other
final state unchanged
```

Also verify:

- async plugin callback is awaited;
- delivery order follows registration order;
- plugin exception fails closed;
- `asteps()` event sequence remains unchanged;
- engine still imports no plugin modules.

## R3 and later remain unchanged

```text
R3  explicit reducers + joins
R4  durable checkpoint lineage / replay
R5  locked-evaluator optimizer / trace learning
```

The observer fix does not authorize parallel merge semantics, durable replay,
or optimizer work to leak into the kernel.
