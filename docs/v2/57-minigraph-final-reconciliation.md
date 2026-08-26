<!-- lint-ignore LINT-013 -->
# 57 — MiniGraph Final Reconciliation

**Status:** Canonical architecture record — 2026-08-27  
**Applies to:** `oramasys/perpetua-core` graph kernel and `oramasys` graph-spec/runtime planning  
**Implementation branch:** `2026-08-27-minigraph-final-reconciliation`  
**Core implementation PR:** <https://github.com/oramasys/perpetua-core/pull/1>

This record resolves the final face-off between the shipped canonical MiniGraph, Kimi's standalone rewrite, the subsequent Kimi/Claude review, and the current graph-engineering research companion. Future work MUST use this document when an older MiniGraph-specific statement conflicts with it.

## Supersession map

This document is additive history, but it supersedes the following MiniGraph-specific clauses where they conflict:

| Earlier authority | Superseded clause | Current rule |
| --- | --- | --- |
| [`00-context-and-decisions.md`](00-context-and-decisions.md) D8 implementation note | physical `~70`/`65`-line kernel framing as an architectural target | kernel stays small/pure/irreducible; physical line count is a review signal, never a semantic CI gate |
| [`01-kernel-spec.md`](01-kernel-spec.md) §4 | old single-loop engine sketch; async-function-only invocation; implicit falsey termination | `CompiledGraph` owns the sole scheduler; returned awaitables are awaited; node/route contracts fail closed |
| [`01-kernel-spec.md`](01-kernel-spec.md) streaming sketch | streaming may wrap/reimplement traversal | adapters consume the canonical structural `asteps()` seam |
| [`04-build-order.md`](04-build-order.md) Phase 2 | Phase 2 described as completely closed | Phase 2 remains shipped historically, with this R0–R2 reconciliation as a correctness/architecture hardening addendum |
| [`15-phase1-as-built.md`](15-phase1-as-built.md) | historical as-built line counts/topology | retained as history; current runtime contract is defined here and by `perpetua-core` tests |
| [`../superpowers/specs/2026-05-17-salvage-translation-design.md`](../superpowers/specs/2026-05-17-salvage-translation-design.md) | engine `<=80` hard invariant; source-builder freeze expectations | line cap retired; builder stays mutable; compiled topology is detached and has no mutation API |

Historical documents remain useful evidence of why the design evolved. They are not to be mechanically restored over this record.

---

## 1. Locked control-structure doctrine

Use the least powerful control structure that makes the contract explicit:

```text
Prompt = one inference
Chain  = fixed pipeline
Loop   = bounded repetition
Graph  = explicit state machine
```

A workflow graduates to a graph when topology itself is domain logic: named states, conditional routing, legitimate cycles, multiple exits, interruption/resume, fan-out/fan-in, subgraphs, or traversal provenance.

The graph is not merely a diagram. It is a state-transition contract with bounded execution and observable control semantics.

---

## 2. Canonical state contract

`PerpetuaState` remains the one canonical in-process graph state.

Non-negotiable properties:

- Pydantic v2 `BaseModel`, not an alternate dataclass state;
- `scratchpad: dict[str, Any]`;
- `nodes_visited: list[str]`;
- nodes return `dict` deltas;
- `PerpetuaState.merge()` remains the canonical sequential delta application path;
- graph-run state is not long-term PT memory and is not a durable checkpoint format by itself.

Kimi's standalone `GraphState` is preserved only as historical design evidence. Its additive scratchpad/tuple visit merge semantics are not interchangeable with canonical `PerpetuaState.merge()`.

---

## 3. Canonical execution ownership

The builder/runtime split is now explicit:

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

`MiniGraph.ainvoke(state)` is a convenience operation that compiles a fresh snapshot and delegates execution to `CompiledGraph`.

`compile()` freezes the *compiled topology surface*, not the source builder. Later builder node/edge mutations MUST NOT affect an already compiled graph. Arbitrary callable objects are not deep-copied; detached topology is not magical deep immutability.

---

## 4. Node invocation contract

The scheduler MUST invoke a node first and inspect the returned object:

```python
result = node_fn(state)
if inspect.isawaitable(result):
    result = await result
```

This is stronger than `asyncio.iscoroutinefunction(node_fn)` because it correctly supports:

- ordinary async functions;
- ordinary sync functions;
- callable objects implementing `async __call__` (including the canonical `ToolNode`);
- sync functions that return awaitables.

A node result MUST be a `dict` delta. `None` or another value is a contract error; the kernel does not silently coerce falsey results to `{}`.

---

## 5. Routing and termination contract

`END = "__end__"` is the only normal terminal route.

A static or conditional edge MUST resolve to a non-empty string. Invalid route values fail closed rather than being interpreted as successful termination.

Execution order is invariant:

```text
enter node
-> record visit
-> execute node
-> await returned awaitable if necessary
-> validate dict delta
-> merge delta
-> evaluate outgoing edge against UPDATED state
```

This post-merge routing rule is part of the public graph semantics.

---

## 6. Cycle-bound semantics

Every graph cycle remains bounded by `max_steps`.

`MaxStepsExceeded` now has exact semantics:

```text
steps     = number of completed node executions
last_node = most recently entered node
```

The guard trips before an additional node would exceed the budget. A zero-step budget therefore reports `steps=0` and `last_node=START`.

---

## 7. Interrupt semantics

The kernel recognizes `Interrupt` structurally so it does not import the plugin package.

Required fields/behavior:

- exception type name is `Interrupt`;
- `prompt` is required by the structural protocol;
- `payload` is optional and read with `getattr(..., None)`;
- graph status becomes `interrupted`;
- metadata records interrupt node, prompt, and optional payload;
- other exceptions propagate.

The retired `interrupt_handler` constructor argument had no execution semantics and is removed rather than preserved as a misleading no-op API.

Durable resume is NOT introduced by this reconciliation. A later checkpoint/runtime design must define replay and idempotency semantics before claiming durable HITL resume.

---

## 8. One canonical execution seam

The central architectural correction is a single structural execution seam owned by `CompiledGraph`:

```text
CompiledGraph._run(state)
        |
        +--> ainvoke(state)  -> final PerpetuaState
        |
        +--> asteps(state)   -> structural GraphEvent stream
```

Public structural event kinds are:

```text
edge.selected
node.start
node.end
interrupt
done
```

The public `GraphEvent` contract carries only control-plane metadata such as event kind, node/target, completed-step count, and terminal reason.

It does NOT carry raw prompts, state snapshots, node deltas, exporter details, database handles, provider policy, or persistence logic.

This seam exists so streaming, checkpoint, trace, and debugger adapters never need to copy the graph scheduler or read private `_nodes`/`_edges` topology.

---

## 9. Plugin boundary

Keep the existing canonical namespace:

```text
perpetua_core/graph/plugins/
```

Do not create `minigraph_extras/` or another parallel plugin system.

Current generic plugin concepts remain outside `engine.py`:

- checkpointer;
- interrupts / interrupt guard;
- routing;
- validation;
- tools / ToolNode;
- subgraphs;
- streaming;
- structured LLM output;
- parallel dispatch.

The engine MUST NOT import plugins, providers, storage adapters, network clients, telemetry exporters, or upper-layer graph policy.

---

## 10. Parallelism before expansion

The current parallel helper historically used ordered last-writer-wins merging with a scratchpad special case. That is not a sufficient generic fan-in contract.

Before richer parallel graph semantics ship, define explicitly:

```text
Reducer: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
Join:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Branch completion timing MUST NOT silently define state merge semantics.

This is R3 work, not part of the current kernel reconciliation.

---

## 11. Durability before resume claims

Checkpoint evolution must upgrade the existing checkpointer, not create a second subsystem.

A future durable checkpoint identity should include at least:

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

Durable replay requires explicit effect idempotency/deduplication policy. External-write nodes cannot be automatically retried/resumed safely without such a contract.

This is later R3/R4 work.

---

## 12. Upper-layer graph architecture

`perpetua-core` executes a realized graph. `oramasys` owns the richer workflow/specification layer.

Canonical future vocabulary:

```text
GraphSpec       reusable/versioned graph definition
GraphRun        one realized execution identity/configuration
GraphTrace      append-only observed execution evidence
GraphCheckpoint resumable state + compatibility lineage
```

Future `GraphSpec`/`NodeSpec`/`EdgeSpec`, graph lint, topology classification, budgets, runtime outcome taxonomy, effect policy, and workflow evaluation belong in `oramasys`, not in `MiniGraph.engine.py`.

The intended direction remains one-way:

```text
oramasys/oramasys
  graph DSL/spec/compiler/runtime policy
             |
             v
oramasys/perpetua-core
  state + irreducible execution mechanics
```

`perpetua-core` never imports upward from `oramasys`.

---

## 13. Graph lint target

Before executing a versioned `GraphSpec`, the upper layer should eventually validate:

- entry exists;
- all static targets exist;
- unreachable nodes are rejected or explicitly allowed;
- every reachable path terminates or participates in a bounded cycle;
- parallel fan-in declares join/reducer policy;
- durable/external-write nodes declare replay/effect policy;
- stable graph/node IDs are present;
- schema/version compatibility is explicit.

Natural-language graph generation, if introduced, compiles to a typed validated `GraphSpec`; prose is never the runtime authority.

---

## 14. Optimization/evaluation boundary

Automated graph evolution remains a research lane until the following exist:

```text
versioned GraphSpec
+ GraphTrace corpus
+ locked evaluator
+ quality/cost/latency/reliability metrics
+ candidate isolation
+ promotion gate
```

Hard rule:

> The component mutating a prompt, node, strategy, or graph may not alter the acceptance metric during the same experiment.

Trace-derived learning should flow through governed memory/review rather than direct uncontrolled runtime self-rewrite.

---

## 15. Reconciliation implementation status

Implemented in `oramasys/perpetua-core` PR #1:

- canonical `PerpetuaState` retained;
- returned-value awaitability;
- direct `CompiledGraph` scheduler ownership;
- strict dict-delta validation;
- strict route validation / END-only normal termination;
- exact max-step diagnostics;
- safe structural interrupt payload handling;
- removed no-op `interrupt_handler` constructor surface;
- detached compile regression coverage;
- actual ToolNode-inside-MiniGraph regression coverage;
- structural `GraphEvent` + `asteps()` seam;
- streaming rewritten as a scheduler adapter;
- repository-native Python 3.11/3.12 test workflow added for future PR verification.

Deferred intentionally:

- reducer/join redesign;
- checkpoint lineage and durable resume;
- runtime budgets/effect policy;
- `GraphSpec` implementation;
- graph optimizer and trace miner.

---

## 16. Acceptance invariants

Any future change to this subsystem must preserve:

1. one canonical graph state model (`PerpetuaState`);
2. one scheduler implementation;
3. async function/callable/returned-awaitable support;
4. ordered `list[str]` visit provenance;
5. post-merge conditional routing;
6. explicit END-only normal termination;
7. deterministic bounded cycles;
8. detached compiled topology;
9. no plugin/provider/storage imports in the kernel;
10. structural events remain provider/exporter independent;
11. streaming does not traverse `_nodes`/`_edges` itself;
12. dynamic/durable/optimization features stay outside the kernel until their contracts are proven.

The north star is unchanged:

> Keep intelligence flexible inside nodes, keep control semantics explicit in the graph, keep effects auditable at boundaries, keep evaluation independent from mutation, and keep the kernel smaller in responsibility than the ecosystem around it.
