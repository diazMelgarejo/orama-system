# 58 — MiniGraph Observer + Pattern-Library Reconciliation

**Status:** canonical addendum — 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Parent authority:** [57 — MiniGraph Final Reconciliation](57-minigraph-final-reconciliation.md)  
**Core integration:** `oramasys/perpetua-core@d1c0dfca12fef5df6e6b15c602e765e299279676`

This addendum preserves doc 57 as the overall MiniGraph authority but supersedes
its §8 observer-mechanism description where that text conflicts with the merged
`perpetua-core` implementation and the recovered `GraphPlugin` groundwork.

It also makes the pre-existing
[`references/patterns/`](references/patterns/) library an explicit evidence layer
beneath the canonical v2 design rather than discarded historical scaffolding.

## 1. One scheduler, two observation projections

The current core implementation has one private scheduler:

```text
CompiledGraph._run()
  sole traversal/scheduling loop
        |
        v
GraphObservation
  event + PerpetuaState + optional node delta
        |
        +--------------------------+
        |                          |
        v                          v
plugin fan-out                 GraphEvent
checkpointer/tracer/audit          |
                                  v
                               asteps()
                                  |
                                  v
                         streaming / API / UI
```

Rules:

1. `_run()` is the sole scheduler implementation.
2. `ainvoke()` drains the rich observation stream and returns final state.
3. `aobserve()` exposes trusted in-process `GraphObservation` values.
4. `asteps()` projects observations to sanitized `GraphEvent` values.
5. `GraphEvent` stays control-only and excludes state/node deltas.
6. `GraphObservation` may carry state and the successful `node.end` delta.
7. No plugin may reimplement traversal or read private `_nodes` / `_edges`.

This corrects stale prose that claimed `asteps()` itself was the scheduler and
that `_run()` did not exist.

## 2. Why `asteps()` alone is not multicast

An async generator is a pull stream. One consumer drains each yielded item.
Concurrent consumers may raise `RuntimeError: anext(): asynchronous generator is
already running` or allow one consumer to consume observations the other never
receives. Neither behavior is broadcast semantics.

Therefore this is insufficient for one run that needs simultaneous observers:

```text
asteps()
  ├─ Checkpointer
  └─ Tracer
```

The correct pattern is one rich observation drain plus deterministic push fan-out:

```text
GraphObservation stream
        |
        v
PluginDispatcher
  ├─ GraphPlugin A
  ├─ GraphPlugin B
  └─ GraphPlugin C
```

The dispatcher delivers observations in plugin registration order and is
fail-closed by default. A failed durability/audit observer must not silently
lose evidence while graph execution continues.

Richer per-plugin failure/backpressure policy is future upper-layer work.

## 3. `GraphPlugin` groundwork is live, not historical

`05-feasibility-review.md` anticipated the exact multi-consumer need before the
current scheduler existed. It called for documented plugin callbacks so the
checkpointer and HITL machinery would not monkey-patch `ainvoke()` or reach into
MiniGraph internals.

`08-technical-architecture-review.md` and the later `01-kernel-spec.md`
materialized that recommendation.

The final synthesis is therefore not "GraphPlugin versus asteps".

```text
GraphPlugin groundwork
  multicast / push requirement
          +
_run / aobserve / asteps
  one-scheduler requirement
          =
GraphObservation + plugin fan-out
```

Both lines of work survive.

## 4. Checkpointer and resumability boundary

The existing `SqliteCheckpointer` becomes a `GraphPlugin`-compatible observer.
It checkpoints successful `node.end` observations and does not schedule the
graph itself.

That implementation is the first persistence primitive toward R4. It does not
yet complete the R4 contract, but **durable resumability is explicitly retained
and adopted as the R4 target**.

Canonical framing:

```text
LangGraph checkpoint/thread identity
    ADOPT

Atomic successful-boundary checkpoints
    ADOPT / ADAPT

Durable resumability
    ADOPT — R4 target

"perfect resumption"
    REJECT WORDING ONLY

durable deterministic resume
    ADOPT TARGET
```

"Perfect" is not a promise that the system can reverse time. The intended
engineering guarantee is narrower and useful: save enough session/graph state,
identity, and replay metadata to resume predictably from an explicit compatible
checkpoint boundary.

Durable deterministic resume requires:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical node/step
replay policy
effect identity
idempotency / effect dedupe
```

If an external side effect already happened, graph-state restoration does not
make that event unhappen. The runtime must reconcile it through idempotency,
deduplication, compensation, or explicit human/policy handling.

That is realistic resumability, not total reversibility.

## 5. Recovered pattern-library authority

The v2 pattern-mining library predates this reconciliation and remains useful
engineering evidence. It is not runtime authority and does not override docs
57/58, but its mined primitives should be reconciled rather than discarded.

Canonical status is recorded in:

[`references/patterns/RECONCILIATION-2026-08-27.md`](
references/patterns/RECONCILIATION-2026-08-27.md)

Summary:

- LangGraph checkpoint/session identity and reducer lessons survive into R3/R4.
- Pydantic AI tool-schema extraction survives without its runtime dependency.
- Karpathy March-of-Nines becomes verification/evaluator doctrine above kernel.
- Swarm handoffs map to conditional edges.
- CrewAI manager patterns map to GraphSpec/subgraphs.
- AutoGen nested work maps to bounded subgraphs.
- Foundry evaluation, isolation, and routing split across their proper layers.

## 6. Correct state-reducer interpretation

The pattern-library README previously described future reducer behavior as if it
were current `PerpetuaState.merge()` semantics.

Current sequential semantics are the same two-layer isolation contract as the
merged core implementation:

```text
PerpetuaState.merge(delta)
  -> model_copy(update=deepcopy(delta), deep=True)
```

`deep=True` isolates inherited nested mutable state. `deepcopy(delta)` separately
isolates caller-owned mutable values supplied through the update. Neither layer
substitutes for the other.

The scheduler explicitly appends `nodes_visited` before node execution.

Generic parallel fan-in still requires explicit field reducers and join policy.
That remains R3 and MUST NOT be smuggled into ordinary sequential merge.

## 7. Ownership after reconciliation

```text
diazMelgarejo/orama-system
  methodology + pattern evidence
  GraphSpec / NodeSpec / EdgeSpec
  lint + evaluation + runtime/effect policy
                    |
                    v
oramasys/perpetua-core
  PerpetuaState + one realized-graph scheduler
  GraphObservation + GraphEvent
  generic graph plugins / observer fan-out
                    |
                    v
Perpetua-Tools
  runtime telemetry + memory governance
```

`perpetua-core` never imports upward from `orama-system`.

## 8. Implementation phases

```text
R0/R1  canonical kernel reconciliation       merged in core at d1c0dfc
R2     GraphEvent structural projection      merged in core at d1c0dfc
R2.1   GraphObservation + plugin fan-out      merged in core at d1c0dfc
R3     reducers + explicit joins             deferred
R4     durable deterministic resume          adopted target; implementation deferred
R5     optimizer / trace learning            research only
```

R4 being deferred means "not implemented in this integration", not "rejected".
The capability remains part of the intended architecture.

The implementation plan addendum is:

[`plans/2026-08-27-minigraph-observer-fanout-addendum.md`](
plans/2026-08-27-minigraph-observer-fanout-addendum.md)
