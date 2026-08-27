# 59 — MiniGraph State, Mutation, and Observer Finalization

**Status:** canonical correction addendum — 2026-08-28  
**Date basis:** Asia/Manila (UTC+08:00)  
**Parent authorities:**
[`57-minigraph-final-reconciliation.md`](57-minigraph-final-reconciliation.md),
[`58-minigraph-observer-pattern-library-reconciliation.md`](58-minigraph-observer-pattern-library-reconciliation.md)

This addendum resolves the final inconsistencies discovered after PT lesson
`e0ff7f2d6717` caught up with the reconciliation branch. Where this document
conflicts with older MiniGraph prose or examples, this document governs.

## 1. The blanket no-mutation rule is superseded

The actual source of the previously hard-to-locate rule was found at:

```text
.cursor/rules/common-coding-style.mdc
```

Its old always-applied instruction was:

```text
ALWAYS create new objects, NEVER mutate existing ones
```

That blanket rule is superseded by the boundary-aware policy now committed in
the same file.

Canonical rule:

```text
value / versioned specification
  prefer immutable or persistent updates
  prior generations must remain unchanged

builder / workspace / buffer / cache
  intentional local mutation is allowed when it is the documented API
  mutation must not leak across snapshot/publication boundaries

compiled / published / observed snapshot
  treat as immutable after publication
```

Immutability is a boundary property, not a universal ban on local mutation.

## 2. PerpetuaState generations are deeply isolated

`PerpetuaState.merge(delta)` MUST return a new state using:

```python
self.model_copy(update=delta, deep=True)
```

`deep=True` is load-bearing because Pydantic's default copy is shallow. Without
it, untouched nested mutable fields can be aliased between state generations.

The invariant is precise:

> Nodes and observers MUST treat the state they receive as immutable input.
> `merge()` guarantees deep isolation between produced state generations; it
> does not make every nested Python container intrinsically frozen.

Regression coverage MUST prove mutating nested containers on a later merged
state cannot mutate the prior state.

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

This preserves the existing MiniGraph API and the LangGraph-style builder
mental model. Code such as this remains valid:

```python
graph = MiniGraph()
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge("a", "b")
```

Changing `add_node()` or `add_edge()` to persistent-value semantics would make
bare builder calls silently ineffective and is therefore a breaking API change,
not an internal optimization.

The immutable boundary is `compile()`: later mutations to the source builder
MUST NOT alter an existing `CompiledGraph`.

## 4. Persistent structural sharing belongs in GraphSpec

The structural-sharing idea recovered in `e0ff7f2d6717` is useful, but its
natural owner is the future versioned specification layer, not MiniGraph.

Recommended future shape:

```text
immutable/versioned GraphSpec
  with_node() / with_edge()
  structural sharing allowed
        |
        | validate + compile
        v
MiniGraph
  realized construction workspace
        |
        v
CompiledGraph
  detached runtime snapshot
```

`GraphSpec` is a versioned value used for identity, diffing, optimization,
review, and promotion. Persistent copy-on-write semantics therefore fit it
cleanly.

## 5. One scheduler, two observation projections

The actual core execution architecture is:

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
all registered listeners. Plugins never reimplement traversal.

`GraphEvent` remains control-only. `GraphObservation` is trusted in-process
evidence and may contain state plus the node delta at successful `node.end`.

Any older example that describes `asteps()` itself as the sole scheduler, or
claims no `_run()` exists, is superseded.

## 6. Observer delivery symmetry is not action symmetry

The dispatcher contract is:

> Every registered plugin is offered every `GraphObservation` in deterministic
> registration order.

A plugin MAY act only on the subset relevant to its contract.

Therefore this is correct:

```text
Checkpointer
  delivered all observations
  persists only node.end

Tracer
  delivered all observations
  records all structural events
```

The R2.4 proof MUST distinguish:

1. multicast delivery integrity — two spy plugins receive the same complete
   sequence;
2. semantic filtering — heterogeneous plugins may persist/record different
   subsets after receiving the same sequence;
3. observer transparency — plugin-enabled final state equals an equivalent
   no-plugin `ainvoke()` result.

The previous wording requiring all plugins to *record* identical subsets is
superseded.

## 7. Executable core is the field-level authority

`orama-system` owns architecture, GraphSpec policy, lint, evaluation, and the
normative boundary rules above. `oramasys/perpetua-core` owns executable
field-level behavior for:

```text
GraphEvent
GraphObservation
CompiledGraph._run()
aobserve()
asteps()
MiniGraph builder methods
PerpetuaState.merge()
```

Long code samples in `01-kernel-spec.md` are explanatory copies, not an
independent executable source of truth. If an example drifts from tested core
ordering or field semantics, the tested core implementation plus docs 57-59
win and the sample should be repaired.

## 8. GraphSpec validation remains fail-closed

The concurrent GraphSpec correction retained during the earlier merge conflict
is canonical:

> Before execution, a versioned `GraphSpec` MUST pass validation. Execution
> MUST reject specifications that fail the lint/compatibility contract.

This remains upper-layer `orama-system` policy and does not move GraphSpec
validation into the MiniGraph kernel.

## Final state

```text
PerpetuaState
  deep-isolated generations

MiniGraph
  intentionally mutable builder

CompiledGraph
  detached runtime snapshot
  one _run() scheduler

GraphObservation
  rich trusted evidence

GraphEvent
  sanitized structural projection

GraphPlugin dispatcher
  identical delivery to every plugin
  plugin-specific deterministic filtering allowed

GraphSpec (future)
  immutable/versioned persistent value
  fail-closed validation before realization
```

This is the final reconciliation of the state-copy, mutation, observer, and
versioned-specification concerns surfaced by PT lesson `e0ff7f2d6717`.
