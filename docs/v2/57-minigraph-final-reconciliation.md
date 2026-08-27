<!-- lint-ignore LINT-013 -->
# 57 — MiniGraph Final Reconciliation

**Status:** canonical architecture record — 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Core repo:** `oramasys/perpetua-core`  
**Upper-layer authority:** `diazMelgarejo/orama-system`  
**Core PR:** <https://github.com/oramasys/perpetua-core/pull/1>

**Branch-name exception:** approved for the already-open reconciliation PRs only.

PR #333 and `oramasys/perpetua-core` PR #1 retain
`2026-08-27-minigraph-final-reconciliation`. Any successor branch MUST use
`yyyy-mm-dd-NNN-brief-summary`.

This record resolves the final face-off between the shipped MiniGraph, Kimi's
standalone rewrite, the Kimi/Claude review, and the graph-engineering research.
Future work MUST use this record when an older MiniGraph statement conflicts.

## Supersession map

This document preserves history but supersedes conflicting MiniGraph clauses.

| Earlier authority | Superseded clause | Current rule |
| --- | --- | --- |
| [`00-context-and-decisions.md`](00-context-and-decisions.md) D8 | `~70`/`65` physical-line target | Small/pure/irreducible is the invariant; physical line count is only a review signal. |
| [`01-kernel-spec.md`](01-kernel-spec.md) §4 | old loop and async-function-only invocation | `CompiledGraph` owns one scheduler; returned awaitables are awaited; contracts fail closed. |
| [`01-kernel-spec.md`](01-kernel-spec.md) streaming sketch | adapter may reimplement traversal | Adapters consume canonical `asteps()` events. |
| [`04-build-order.md`](04-build-order.md) Phase 2 | Phase 2 treated as permanently closed | R0–R2 is a correctness/architecture hardening addendum. |
| [`15-phase1-as-built.md`](15-phase1-as-built.md) | historical line counts/topology | Retained as history; this record and current tests define the runtime contract. |
| [`../superpowers/specs/2026-05-17-salvage-translation-design.md`](../superpowers/specs/2026-05-17-salvage-translation-design.md) | `<=80` hard cap and source-builder freeze | No hard cap; builder stays mutable; compiled topology is detached. |

Historical documents remain evidence of why the design evolved. Do not
mechanically restore their superseded constraints.

---

## 1. Control-structure doctrine

Use the least powerful control structure that makes the contract explicit.

```text
Prompt = one inference
Chain  = fixed pipeline
Loop   = bounded repetition
Graph  = explicit state machine
```

Promote to a graph when topology is domain logic: named states, branches,
cycles, multiple exits, interrupts, fan-out/fan-in, subgraphs, or traversal
provenance.

A graph is a state-transition contract, not merely a diagram.

---

## 2. Canonical state

`PerpetuaState` remains the one canonical in-process graph state.

Non-negotiable properties:

- Pydantic v2 `BaseModel`;
- `scratchpad: dict[str, Any]`;
- `nodes_visited: list[str]`;
- nodes return `dict` deltas;
- `PerpetuaState.merge()` applies sequential node deltas;
- graph-run state is neither PT long-term memory nor a durable checkpoint.

Kimi's `GraphState` remains historical design evidence only. Its additive
scratchpad and tuple-visit merge rules are not interchangeable with canonical
`PerpetuaState.merge()` semantics.

---

## 3. Builder and runtime ownership

The builder/runtime split is explicit.

```text
MiniGraph
  mutable topology builder
        |
        | compile()
        v
CompiledGraph
  detached topology snapshot
  sole scheduler owner
```

`MiniGraph.ainvoke(state)` compiles a fresh snapshot and delegates execution to
`CompiledGraph`.

Compilation detaches the topology, not arbitrary Python object internals.
Later builder node/edge changes MUST NOT alter an existing compiled graph.
The source builder remains mutable.

---

## 4. Node invocation

The scheduler invokes first and inspects the returned object.

```python
result = node_fn(state)
if inspect.isawaitable(result):
    result = await result
```

This supports:

- async functions;
- sync functions;
- callable objects with `async __call__`, including `ToolNode`;
- sync functions that return awaitables.

A node result MUST be a `dict` delta. `None` or another type is a contract
error. The engine does not coerce falsey results to `{}`.

---

## 5. Routing and termination

`END = "__end__"` is the only normal terminal route.

Every static or conditional edge MUST resolve to a non-empty string. Invalid
route values fail closed rather than becoming implicit success.

Execution order is invariant.

```text
enter node
-> record visit
-> execute node
-> await returned awaitable if needed
-> validate dict delta
-> merge delta
-> evaluate outgoing edge against UPDATED state
```

Post-merge conditional routing is public graph semantics.

---

## 6. Cycle bounds

Every cycle remains bounded by `max_steps`.

`MaxStepsExceeded` has exact semantics.

```text
steps     = number of completed node executions
last_node = most recently entered node
```

The guard trips before an additional node would exceed the budget. With a
zero-step budget, the diagnostic is `steps=0` and `last_node=START`.

---

## 7. Interrupts

The kernel recognizes `Interrupt` structurally so it never imports plugins.

Required behavior:

- exception type name is `Interrupt`;
- `prompt` is required;
- `payload` is optional and read with `getattr(..., None)`;
- state becomes `interrupted`;
- metadata records node, prompt, and optional payload;
- unrelated exceptions propagate.

The old `interrupt_handler` constructor argument had no execution semantics and
is removed rather than preserved as a misleading no-op API.

This reconciliation does NOT claim durable resume. Durable HITL requires later
checkpoint, replay, and idempotency contracts.

---

## 8. One canonical execution seam

`CompiledGraph` owns one scheduler and exposes two views over it.

```text
CompiledGraph._run(state)
        |
        +--> ainvoke(state)  -> final PerpetuaState
        |
        +--> asteps(state)   -> structural GraphEvent stream
```

Public event kinds are:

```text
edge.selected
node.start
node.end
interrupt
done
```

`GraphEvent` contains control-plane metadata only: event kind, node/target,
completed-step count, and terminal reason.

It does NOT contain raw prompts, state snapshots, node deltas, database handles,
provider policy, exporter configuration, or persistence logic.

Streaming, checkpoint, trace, and debugger adapters MUST consume this seam
instead of copying the scheduler or traversing private `_nodes`/`_edges`.

---

## 9. Plugin boundary

Keep the existing namespace.

```text
perpetua_core/graph/plugins/
```

Do not create `minigraph_extras/` or another parallel plugin system.

Generic plugin concerns remain outside `engine.py`:

- checkpointing;
- interrupts / resume guard;
- routing and validation;
- tools / `ToolNode`;
- subgraphs;
- streaming;
- structured LLM output;
- parallel dispatch.

The engine MUST NOT import plugins, providers, storage adapters, network
clients, telemetry exporters, or upper-layer graph policy.

---

## 10. Parallelism before expansion

The existing parallel helper's ordered last-writer-wins behavior is not a
sufficient generic fan-in contract.

Before richer parallel graph semantics ship, define explicit reducers and
joins.

```text
Reducer: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
Join:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Branch completion timing MUST NOT silently define state merge behavior.
This is deferred R3 work.

---

## 11. Durability before resume

Upgrade the existing checkpointer rather than introducing a second subsystem.
A future durable identity should include at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
created_at
```

Durable replay also requires explicit effect idempotency/deduplication policy.
External-write nodes cannot be retried or resumed safely without that contract.

---

## 12. Upper-layer ownership

`perpetua-core` executes a realized graph. The final face-off assigns the
richer graph-specification and runtime-policy authority to `orama-system`.

Canonical future vocabulary:

```text
GraphSpec       reusable/versioned graph definition
GraphRun        one realized execution identity/configuration
GraphTrace      append-only observed execution evidence
GraphCheckpoint resumable state + compatibility lineage
```

`GraphSpec`, `NodeSpec`, `EdgeSpec`, lint, topology classification, budgets,
runtime outcome policy, effect policy, version selection, and evaluation belong
in `diazMelgarejo/orama-system`, not in `MiniGraph.engine.py`.

```text
diazMelgarejo/orama-system
  methodology + GraphSpec/NodeSpec/EdgeSpec authority
  lint + version selection + evaluation + runtime policy
                  |
                  | compiles/targets realized mechanics
                  v
oramasys/perpetua-core
  PerpetuaState + irreducible graph execution
```

`perpetua-core` MUST NOT import upward from `orama-system`.

`oramasys/oramasys` may later consume or host an approved projection of these
specifications. Ownership does not move there implicitly. Such a move requires
a new explicit architecture decision.

---

## 13. Graph lint target

Before executing a versioned `GraphSpec`, the `orama-system` layer should
validate at least:

- entry exists;
- static targets exist;
- unreachable nodes are rejected or explicitly allowed;
- every reachable path terminates or participates in a bounded cycle;
- parallel fan-in declares join/reducer behavior;
- durable/external-write nodes declare replay/effect policy;
- stable graph/node IDs are present;
- schema/version compatibility is explicit.

Natural-language topology, if introduced, MUST compile to a typed validated
`GraphSpec`. Prose is never runtime authority.

---

## 14. Optimization and evaluation

Automated graph evolution remains research-only until all of these exist:

```text
versioned GraphSpec
+ GraphTrace corpus
+ locked evaluator
+ quality/cost/latency/reliability metrics
+ candidate isolation
+ promotion gate
```

Hard rule:

> The component mutating a prompt, node, strategy, or graph may not alter the
> acceptance metric during the same experiment.

Trace-derived learning should enter governed memory/review, not uncontrolled
runtime self-rewrite.

---

## 15. Implementation status

Implemented in `oramasys/perpetua-core` PR #1:

- canonical `PerpetuaState` retained;
- returned-value awaitability;
- `CompiledGraph` scheduler ownership;
- strict node-delta and route validation;
- END-only normal termination;
- exact max-step diagnostics;
- optional structural interrupt payload;
- removal of the no-op `interrupt_handler` constructor surface;
- compile-detachment regression coverage;
- real `ToolNode`-inside-MiniGraph regression coverage;
- structural `GraphEvent` + `asteps()`;
- streaming as a scheduler adapter;
- a Python 3.11/3.12 test workflow for future PR verification.

Deferred intentionally:

- reducer/join redesign;
- checkpoint lineage and durable resume;
- runtime budgets/effect policy;
- `GraphSpec`/lint/evaluation implementation in `orama-system`;
- graph optimizer and trace miner.

---

## 16. Acceptance invariants

Future changes MUST preserve:

1. one graph-state model: `PerpetuaState`;
2. one scheduler implementation;
3. async function/callable/returned-awaitable support;
4. ordered `list[str]` visit provenance;
5. post-merge conditional routing;
6. explicit END-only normal termination;
7. deterministic bounded cycles;
8. detached compiled topology;
9. no plugin/provider/storage imports in the kernel;
10. provider/exporter-independent structural events;
11. streaming without private topology traversal;
12. durable/dynamic/optimizer features outside the kernel until proven.

The north star remains:

> Keep intelligence flexible inside nodes, control semantics explicit in the
> graph, effects auditable at boundaries, evaluation independent from mutation,
> and the kernel smaller in responsibility than the ecosystem around it.
