<!-- lint-ignore LINT-013 -->
# 57 — MiniGraph Final Reconciliation

**Status:** canonical architecture record — 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Core repo:** `oramasys/perpetua-core`  
**Upper-layer authority:** `diazMelgarejo/orama-system`  
**Core integration:** `d1c0dfca12fef5df6e6b15c602e765e299279676`

**Branch-name exception:** approved for the already-open reconciliation PRs only.

PR #333 and the historical core reconciliation PR retain
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
| [`01-kernel-spec.md`](01-kernel-spec.md) streaming sketch | adapter may reimplement traversal | Adapters consume canonical observation/event projections and never reimplement traversal. |
| [`04-build-order.md`](04-build-order.md) Phase 2 | Phase 2 treated as permanently closed | R0–R2 is a correctness/architecture hardening addendum. |
| [`15-phase1-as-built.md`](15-phase1-as-built.md) | historical line counts/topology | Retained as history; this record and current tests define the runtime contract. |
| [`../superpowers/specs/2026-05-17-salvage-translation-design.md`](../superpowers/specs/2026-05-17-salvage-translation-design.md) | `<=80` hard cap and source-builder freeze | No hard cap; builder stays mutable; compiled topology is detached. |
| `docs/v2-kimi-minigraph-reconciliation-20260826` branch | Independent Kimi reconciliation and parallel plugin naming | Superseded by this record; retained only as historical convergence evidence. |

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
  mutable construction workspace
        |
        | compile()
        v
CompiledGraph
  detached execution snapshot
  sole scheduler owner
```

`MiniGraph.ainvoke(state)` compiles a fresh snapshot and delegates execution to
`CompiledGraph`.

`MiniGraph.add_node`/`add_edge` mutate `self` and return `self`, matching the
established LangGraph builder pattern. The governing repository rule now uses a
boundary-aware mutation policy: builder/workspace mutation is allowed when it
is the documented API and cannot leak across publication/snapshot boundaries.

The topology immutability boundary is `compile()`. Later builder mutations MUST
NOT alter an existing `CompiledGraph`.

`PerpetuaState.merge()` implements the value-layer isolation boundary with two
independent copy layers:

```python
self.model_copy(update=copy.deepcopy(delta), deep=True)
```

`deep=True` isolates inherited nested mutable state. `copy.deepcopy(delta)`
separately isolates caller-owned mutable values supplied through the update.
Pydantic applies update values after copying the existing model, so neither
layer substitutes for the other.

Persistent structural sharing belongs to the future immutable/versioned
`GraphSpec` layer rather than the mutable MiniGraph construction API.

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

Every static or conditional edge MUST resolve to a non-empty string. A target
other than `END` MUST name a registered node. Invalid routes fail closed at the
routing boundary rather than becoming implicit success or falling through to a
later node lookup error.

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

The merged core originally validated type/emptiness but still allowed unknown
node names to reach a later `KeyError`. Corrective work is preserved on
`oramasys/perpetua-core` branch `2026-08-29-001-post-merge-convergence`, where
unknown routes are rejected explicitly at resolution time with regression
coverage. Do not describe that corrective branch as merged until explicitly
integrated.

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

Structural interrupt recognition and state updates are kernel behavior.
Plugin-specific resume guards, persistence, replay, and durable HITL policy stay
outside `engine.py`.

This reconciliation does NOT claim durable resume. Durable HITL requires later
checkpoint, replay, and idempotency contracts.

---

## 8. One canonical execution seam

`CompiledGraph` owns one private scheduler implementation: `_run()`.
Every execution view projects from that loop.

```text
CompiledGraph._run(state)
  sole scheduler
        |
        v
GraphObservation(event, state, delta?)
        |
        +------------------------+
        |                        |
        v                        v
aobserve()                 GraphEvent
rich trusted                    |
pull                            v
                            asteps()
                            sanitized pull
        |
        +--> ainvoke() drains rich observations -> final PerpetuaState
```

This is the merged core architecture. Earlier prose in this document that said
`asteps()` itself was the scheduler or that `_run()` did not exist is
superseded.

Public event kinds are:

```text
edge.selected
node.start
node.end
interrupt
done
```

`GraphEvent` is the control-plane projection. It contains event kind,
node/target, completed-step count, and terminal reason. It excludes raw prompts,
state snapshots, node deltas, database handles, provider policy, exporter
configuration, and persistence logic.

`GraphObservation` is the trusted in-process projection and may carry the
current `PerpetuaState` plus the successful `node.end` delta.

Streaming/API/UI consumers use `asteps()`. Trusted checkpointer/tracer/plugin
consumers use `aobserve()`. Neither surface may reimplement traversal or reach
into private `_nodes`/`_edges` to schedule the graph.

A bare async generator is single-consumer, not multicast. Concurrent consumers
may either raise `RuntimeError: anext(): asynchronous generator is already
running` or let one consumer receive items the other does not. Multi-observer
runs therefore use one `aobserve()` drain plus deterministic push fan-out.

The canonical plugin callback is generic:

```python
class GraphPlugin(Protocol):
    def on_observation(
        self,
        observation: GraphObservation,
    ) -> object | Awaitable[object]: ...
```

This callback represents all event kinds. Each returned value is inspected and
awaited when awaitable. Authoritative delivery is fail-closed by default.

The merged fan-out initially passed the same rich observation to every plugin.
Because nested state collections and `delta` are mutable, that allowed a
mutating plugin to affect later listeners. The corrective core branch
`2026-08-29-001-post-merge-convergence` supplies a detached state/delta payload
per listener and adds a mutating-listener regression. Again, that branch is
preserved but not merged merely by being documented here.

Per-kind field behavior belongs to the tested `oramasys/perpetua-core`
implementation. Current source paths include:

```text
src/perpetua_core/graph/engine.py
src/perpetua_core/graph/plugins/observer.py
src/tests/graph/test_engine_reconciliation.py
src/tests/graph/plugins/
```

---

## 9. Plugin boundary

Keep the existing namespace.

```text
perpetua_core/graph/plugins/
```

Do not create `minigraph_extras/` or another parallel plugin system.

Generic plugin concerns remain outside `engine.py`:

- checkpoint persistence and durable resume;
- plugin-specific interrupt/resume guards;
- higher-level routing/validation helpers;
- tools / `ToolNode`;
- subgraphs;
- streaming adapters;
- structured LLM output;
- parallel dispatch;
- observer fan-out policy beyond the kernel's observation seam.

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

Before executing a versioned `GraphSpec`, the `orama-system` layer MUST
validate at least:

- entry exists;
- static targets exist;
- unreachable nodes are rejected or explicitly allowed;
- every reachable path terminates or participates in a bounded cycle;
- parallel fan-in declares join/reducer behavior;
- durable/external-write nodes declare replay/effect policy;
- stable graph/node IDs are present;
- schema/version compatibility is explicit.

None of these checks are advisory. Execution MUST reject any specification that
fails validation.

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

The reconciliation merged into `oramasys/perpetua-core` as:

```text
d1c0dfca12fef5df6e6b15c602e765e299279676
```

Merged behavior includes:

- canonical `PerpetuaState` retained;
- two-layer state/delta isolation;
- returned-value awaitability;
- one private `_run()` scheduler;
- rich `GraphObservation` and sanitized `GraphEvent` projections;
- END-only normal termination;
- exact max-step diagnostics;
- optional structural interrupt payload;
- removal of the no-op `interrupt_handler` constructor surface;
- compile-detachment regression coverage;
- real `ToolNode`-inside-MiniGraph regression coverage;
- generic plugin observation fan-out with awaited sync/async settlement;
- Python 3.11/3.12 test workflow with checkout credentials disabled.

The actual merged tree uses the documented `src/` layout, including
`src/perpetua_core/` and `src/tests/`, so the old unconfirmed layout action item
is closed.

Post-merge corrective branch:

```text
2026-08-29-001-post-merge-convergence
```

That branch adds explicit unknown-route rejection and per-listener observation
payload isolation with regressions. It remains unmerged until explicitly
integrated.

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
12. complete awaited plugin observation delivery;
13. listener payload isolation;
14. unknown-route rejection at the routing boundary once the corrective branch
    is integrated;
15. durable/dynamic/optimizer features outside the kernel until proven.

---

## 17. LangGraph / LangGraph.js compatibility target

Internal implementation stays ours. At the API surface, the standing target is
compatibility for the supported builder/topology API and invoke/stream surface.
Do not claim full drop-in compatibility across unimplemented subsystems.

The explicitly excluded or future surfaces include exact
`astream_events(version="v2")` fidelity and full `BaseCheckpointSaver`
serialization compatibility.

### 17a. Python surface

Legacy wrapper aliases may map onto the canonical builder:

```python
# perpetua_core/graph/plugins/langgraph_compat.py -- a plugin, never kernel code
def set_entry_point(self, key: str) -> "MiniGraph":
    return self.set_start(key)


def set_finish_point(self, key: str) -> "MiniGraph":
    return self.add_edge(key, END)
```

Current-surface targets include `START`/`END`, `add_conditional_edges`, and later
compatibility primitives such as `Command` and `Send` when their prerequisites
exist.

`Command(update=..., goto=...)` routing is **not yet proven**. A compatibility
wrapper may translate the state update, but `goto` support MUST NOT be claimed
until a real route-selection hook and compatibility test demonstrate the
selected node through the canonical scheduler.

`Send(node, arg)` depends on the deferred R3 reducer/join contract.

Full `interrupt(value)` parity depends on durable checkpoint/resume semantics;
do not implement a partial API that only raises without real persistence and
resume.

### 17b. JavaScript/TypeScript — `oramaclaw`

A separate JS-facing `oramaclaw` module may target LangGraph.js naming such as
`StateGraph`, `Annotation`, `START`, `END`, `Command`, `addNode`, and `addEdge`.
That compatibility surface remains outside the Python kernel.

Runtime steering of AlphaClaw/OpenClaw processes does not imply repository-level
ownership or modification of those repositories.

### 17c. Compatibility remains outside the kernel

Compatibility aliases and translation layers live outside `engine.py`.
The kernel retains only universal execution mechanics already required for its
own correctness.

---

The north star remains:

> Keep intelligence flexible inside nodes, control semantics explicit in the
> graph, effects auditable at boundaries, evaluation independent from mutation,
> and the kernel smaller in responsibility than the ecosystem around it.
