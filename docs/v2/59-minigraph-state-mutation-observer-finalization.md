# 59 — MiniGraph State, Mutation, and Observer Finalization

**Status:** canonical correction addendum — 2026-08-28  
**Date basis:** Asia/Manila (UTC+08:00)  
**Parent authorities:**
[`57-minigraph-final-reconciliation.md`](57-minigraph-final-reconciliation.md),
[`58-minigraph-observer-pattern-library-reconciliation.md`](58-minigraph-observer-pattern-library-reconciliation.md)

This addendum resolves the remaining state-copy, mutation-boundary, and observer
inconsistencies discovered after the final reconciliation. Where it conflicts
with older MiniGraph prose or examples, this document governs.

## 1. The blanket no-mutation rule is superseded

The actual source of the previously hard-to-locate rule was:

```text
.cursor/rules/common-coding-style.mdc
```

Its former always-applied instruction was:

```text
ALWAYS create new objects, NEVER mutate existing ones
```

That blanket rule is superseded by the boundary-aware policy committed in the
same file.

```text
value / versioned specification
  prefer immutable or persistent updates
  prior generations MUST remain unchanged

builder / workspace / buffer / cache
  intentional local mutation is allowed when it is the documented API
  mutation MUST NOT leak across snapshot/publication boundaries

compiled / published / observed snapshot
  treat as immutable after publication
```

Immutability is a boundary property, not a universal ban on local mutation.

## 2. PerpetuaState generations and caller-owned deltas are isolated

`PerpetuaState.merge(delta)` MUST use both copy layers:

```python
from copy import deepcopy

return self.model_copy(update=deepcopy(delta), deep=True)
```

They close different alias classes:

- `deep=True` isolates nested mutable fields inherited from the existing model;
- `deepcopy(delta)` isolates mutable values supplied through the caller-owned
  update mapping.

Pydantic applies `update` values after copying the existing model. Therefore
`deep=True` alone does not detach nested mutable values supplied in `delta`.

The invariant is:

> Nodes and observers MUST treat received `PerpetuaState` as immutable input.
> `merge()` isolates the prior generation, the caller-owned delta values, and
> the returned generation from one another. It does not make Python containers
> intrinsically frozen.

Regression coverage MUST prove all of these independently:

1. mutating nested fields on a later state cannot mutate the prior state;
2. mutating a caller-held nested value after `merge()` cannot mutate the merged
   state;
3. mutating the merged nested value cannot mutate the caller-held delta object;
4. ordinary delta application still behaves normally.

This correction is merged in `oramasys/perpetua-core` at:

```text
d1c0dfca12fef5df6e6b15c602e765e299279676
```

## 3. MiniGraph remains a mutable construction builder

`MiniGraph.add_node()` and `add_edge()` intentionally mutate the construction
workspace and return `self`.

```text
MiniGraph
  mutable construction workspace
        |
        | compile()
        v
CompiledGraph
  detached execution snapshot
```

This preserves the established LangGraph-style builder contract. Changing these
methods to persistent-value semantics would make ordinary bare builder calls
silently ineffective and is therefore a breaking API change.

The immutable topology boundary is `compile()`: later mutations to the source
builder MUST NOT alter an existing `CompiledGraph`.

## 4. Persistent structural sharing belongs in GraphSpec

The structural-sharing idea is retained, but its natural owner is the future
versioned specification layer.

```text
immutable/versioned GraphSpec
  with_node() / with_edge()
  persistent structural sharing allowed
        |
        | validate + compile
        v
MiniGraph
  mutable realization builder
        |
        v
CompiledGraph
  detached runtime snapshot
```

`GraphSpec` is a versioned value used for identity, diffing, optimization,
review, and promotion, so persistent copy-on-write semantics fit it cleanly.

## 5. One scheduler, two observation projections

The executable core architecture is:

```text
CompiledGraph._run()
  sole scheduler
        |
        v
GraphObservation(event, state, delta?)
        |
        +---------------------+
        |                     |
        v                     v
aobserve()               GraphEvent
rich trusted                  |
in-process pull               v
                        asteps()
                        sanitized pull
```

`GraphPlugin` multicast drains `aobserve()` once and pushes each observation to
registered listeners. Plugins never reimplement traversal.

`GraphEvent` remains control-only. `GraphObservation` is trusted in-process
evidence and may contain state plus the successful `node.end` delta.

Any older example that describes `asteps()` itself as the scheduler, or claims
no `_run()` exists, is superseded.

## 6. Observer delivery symmetry is not action symmetry

The canonical plugin callback is generic:

```python
class GraphPlugin(Protocol):
    def on_observation(
        self,
        observation: GraphObservation,
    ) -> object | Awaitable[object]: ...
```

This single callback exposes the complete observation vocabulary:

```text
edge.selected
node.start
node.end
interrupt
done
```

The dispatcher contract is:

> Every registered plugin is offered every `GraphObservation` in deterministic
> registration order. Each callback result is inspected and awaited when it is
> awaitable. Default authoritative delivery is fail-closed.

A plugin MAY act only on the subset relevant to its contract.

```text
Checkpointer
  delivered all observations
  persists only node.end

Tracer
  delivered all observations
  records all structural events
```

Delivery payloads must also be isolated. `GraphObservation` is frozen only at
the top level; nested `PerpetuaState` collections and `delta` are mutable Python
objects. Therefore each plugin receives a detached rich payload so a mutating
listener cannot affect later listeners or the scheduler's live state.

The R2.4 proof distinguishes:

1. multicast delivery integrity;
2. deterministic semantic filtering by heterogeneous plugins;
3. callback settlement for both sync and async plugins;
4. listener payload isolation;
5. observer transparency: equivalent plugin/no-plugin runs produce equal final
   state.

The previous wording requiring heterogeneous plugins to *record* identical
subsets is superseded.

## 7. Executable core is the field-level authority

`orama-system` owns architecture, GraphSpec policy, lint, evaluation, and the
normative boundary rules. `oramasys/perpetua-core` owns executable field-level
behavior for:

```text
PerpetuaState.merge()
GraphEvent
GraphObservation
CompiledGraph._run()
aobserve()
asteps()
MiniGraph builder methods
```

Long code samples in `01-kernel-spec.md` are explanatory copies. If a sample
drifts from tested core ordering or field semantics, the tested core plus docs
57–59 win and the sample MUST be repaired.

## 8. Core integration and post-merge corrective findings

Core PR #1 merged as:

```text
d1c0dfca12fef5df6e6b15c602e765e299279676
```

That integration closes the earlier review findings for:

- caller-owned mutable values supplied through `delta`;
- nested state-generation isolation;
- checkout credential persistence;
- one private `_run()` scheduler plus rich/sanitized projections;
- generic `on_observation(...)` fan-out with awaited callbacks.

A fresh post-merge contract sweep found two additional executable gaps that a
green test suite had not covered:

1. unknown routes could pass `_resolve_edge()` and fail later as `KeyError`;
2. all plugins received the same rich mutable payload, so one mutating listener
   could affect later listeners or the live run.

Corrective work is preserved on:

```text
2026-08-29-001-post-merge-convergence
```

The branch adds explicit unknown-route rejection at route resolution, detached
per-listener observation payloads, and regression tests for both invariants.
Those corrective changes are **not merged merely because they are documented
here**; integration requires an explicit merge instruction and exact-head
verification.

## 9. GraphSpec validation remains fail-closed

Before execution, a versioned `GraphSpec` MUST pass validation. Execution MUST
reject any specification that fails the lint/compatibility contract.

This is upper-layer `orama-system` policy and does not move GraphSpec validation
into the MiniGraph kernel.

## Final state

```text
PerpetuaState
  prior generation isolated
  caller-owned delta isolated

MiniGraph
  intentionally mutable builder

CompiledGraph
  detached runtime snapshot
  one _run() scheduler
  unknown routes rejected at resolution boundary

GraphObservation
  rich trusted evidence

GraphEvent
  sanitized structural projection

GraphPlugin dispatcher
  complete generic on_observation delivery
  sync/async callback settlement awaited
  plugin-specific deterministic filtering allowed
  detached per-listener payloads
  fail-closed authoritative delivery

GraphSpec (future)
  immutable/versioned persistent value
  fail-closed validation before realization
```

This is the final state/mutation/observer correction. The wider pending pattern
and PT-unbundling phases are tracked in
[`plans/2026-08-29-pattern-backlog-and-pt-unbundling.md`](plans/2026-08-29-pattern-backlog-and-pt-unbundling.md).
