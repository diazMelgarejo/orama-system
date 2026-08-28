<!-- lint-ignore LINT-013 -->
# MiniGraph Final Reconciliation — Execution Plan

**Date:** 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Status:** in execution  
**Architecture:** [canonical record](../57-minigraph-final-reconciliation.md)  
**Pattern/unbundling addendum:**
[2026-08-29-pattern-backlog-and-pt-unbundling.md](2026-08-29-pattern-backlog-and-pt-unbundling.md)

## Branch isolation

Both reconciliation branches were created from frozen `main` tips before writes.

| Repository | Base main | Working branch |
| --- | --- | --- |
| `oramasys/perpetua-core` | `8c063f41f6b8d31f6a8aa71d6c78155ea9690c90` | `2026-08-27-minigraph-final-reconciliation` |
| `diazMelgarejo/orama-system` | `568b4167edaa25658b3a001b4f2273f774014f9a` | `2026-08-27-minigraph-final-reconciliation` |

The two already-open reconciliation PRs retain this branch name as an approved
one-time exception. Any successor branch MUST use
`yyyy-mm-dd-NNN-brief-summary`.

The sandbox could not create network-backed local Git worktrees because GitHub
DNS was unavailable to the shell. Isolation was therefore preserved with remote
branches pinned to the exact `main` SHAs above. Do not rewrite this history as if
literal local worktree directories existed.

---

## R0 — Characterize contracts

Retain regression coverage for:

- linear traversal and ordered visit provenance;
- conditional routing after state merge;
- bounded cycles and exact `max_steps` diagnostics;
- START/END behavior;
- structural interrupts;
- compile detachment;
- kernel no-plugin/no-optional-import architecture;
- async functions, sync functions, async callable objects, and returned
  awaitables;
- actual `ToolNode` execution inside MiniGraph;
- invalid node deltas and invalid routes;
- optional interrupt payload;
- mutable builder compatibility.

Behavioral bugs are not closed until represented by a regression test.

---

## R1 — Reconcile the kernel

Canonical ownership:

```text
MiniGraph builder
  mutable construction workspace
        |
        | compile()
        v
CompiledGraph
  detached runtime snapshot
  one scheduler implementation
```

Required invariants:

1. keep `PerpetuaState` canonical;
2. call first, then `inspect.isawaitable(result)`;
3. require dict node deltas;
4. preserve `nodes_visited: list[str]`;
5. route on updated state;
6. make END the sole normal terminal route;
7. reject empty/non-string/unknown routes;
8. count completed executions in `MaxStepsExceeded.steps`;
9. report the most recently entered node in `last_node`;
10. support optional structural interrupt payload;
11. remove the dead `interrupt_handler` constructor API;
12. keep the builder mutable and compiled topology detached;
13. do not introduce a physical-line gate.

`PerpetuaState.merge()` additionally MUST isolate both inherited mutable state
and caller-owned mutable delta values:

```python
self.model_copy(update=copy.deepcopy(delta), deep=True)
```

`deep=True` and `deepcopy(delta)` close different aliasing classes.

---

## R2 — One scheduler, rich observations, sanitized events

Canonical execution seam:

```text
CompiledGraph._run()
  sole scheduler implementation
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
```

Public structural event kinds:

```text
edge.selected
node.start
node.end
interrupt
done
```

`GraphEvent` MUST remain control-plane-only. It excludes state snapshots, raw
node deltas, prompts, provider/storage handles, and exporter/persistence policy.

Streaming adapters consume `asteps()` and MUST NOT reimplement traversal.

---

## R2.1–R2.4 — GraphPlugin observer fan-out

The recovered `GraphPlugin` groundwork is live and complementary to the
pull-stream API.

```text
one aobserve() drain
        |
        v
PluginDispatcher
  ├─ Checkpointer
  ├─ Tracer
  ├─ Audit observer
  └─ other trusted listeners
```

Rules:

- every plugin is offered the same complete ordered observation stream;
- plugins may deterministically act on different subsets;
- sync and async callbacks are supported by inspecting returned awaitables;
- default delivery is awaited and fail-closed;
- no plugin may traverse private topology or schedule the graph itself;
- plugin-enabled final state MUST equal an equivalent no-plugin run.

A checkpointer persisting only `node.end` while a tracer records every event is
therefore correct.

---

## R2.5 — Exact-head verification and remaining observer policy

Exact PR head is authoritative. CodeRabbit/review, deterministic tests, SAST,
and Actions are separate gates.

The latest Claude/CodeRabbit findings on `oramasys/perpetua-core` PR #1 were:

1. mutable values supplied through `delta` still aliased with the merged state
   when only `model_copy(deep=True)` was used;
2. `actions/checkout@v4` persisted the checkout token into later
   pull-request-controlled test steps.

Both were fixed together on the core reconciliation branch at:

```text
488bc6cc440247ca86811c46ae0dd05869898324
```

The fix adds `deepcopy(delta)`, a caller-held nested mutable delta regression,
and `persist-credentials: false`.

Do not treat the findings as closed until exact-head CI and the current review
threads confirm the commit.

R2.5 also defines the next observer-policy contract:

```text
AUTHORITATIVE
  awaited; failure fails the run

BEST_EFFORT
  failure handling explicitly configurable

BUFFERED_TELEMETRY
  permitted only with declared evidence-loss semantics
```

Checkpoint/authorization/audit evidence MUST NOT be silently detached through
background `create_task()` delivery.

---

## R3 — Typed reducers, joins, and deterministic parallelism

This phase incorporates the LangGraph reducer pattern and the unresolved
parallel portion of Swarm/CrewAI/AutoGen.

```text
reducers: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
joins:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Required properties:

- deterministic under branch completion reordering;
- explicit conflict behavior;
- explicit partial-failure behavior;
- no race-order-defined state;
- provenance of branch contributions where required.

Pattern mapping:

```text
LangGraph reducers -> explicit field reducer contract
Swarm handoff      -> conditional edge / transfer state
CrewAI manager     -> Planning/Delegation/Aggregation subgraph
AutoGen nesting    -> bounded subgraph
parallel agents    -> only after reducers + joins are explicit
```

Generic reducer/join mechanics may live in `perpetua-core`. Concrete
GraphSpec declarations belong to `orama-system`.

---

## R4 — Durable deterministic resume

Resumability is adopted architecture, not rejected scope.

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

Required checkpoint identity includes at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
saved session/graph state
created_at
replay boundary
```

Effect-bearing nodes additionally require effect identity, idempotency/dedupe,
reconciliation status, and compensation/human-policy handling where replay
cannot erase a real-world action that already occurred.

Upgrade the existing checkpointer; do not create a competing durability
subsystem.

---

## R5 — Versioned GraphSpec, compiler, lint, tools, and routing

`GraphSpec`, `NodeSpec`, `EdgeSpec`, graph lint, version selection, and runtime
policy belong to `orama-system`.

```text
immutable/versioned GraphSpec
  stable IDs
  persistent with_node()/with_edge() updates allowed
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

GraphSpec execution MUST fail closed if validation fails.

Required validation includes:

- entry and static-target existence;
- unreachable-node policy;
- termination or bounded-cycle obligation;
- explicit reducers/joins for parallel fan-in;
- stable graph/node IDs;
- schema/version compatibility;
- replay/effect policy for durable or externally mutating nodes;
- declared capability/budget requirements where policy requires them.

### Pydantic AI extraction

Adopt the primitive, not the full runtime:

```text
inspect.signature
+ Pydantic create_model / JSON schema
+ docstring descriptions
+ strict argument validation
+ dependency/state injection
```

Generic ToolNode/tool-schema mechanics may live in `perpetua-core`. Tool effect
authority, approvals, and allowed capabilities remain upper-layer policy.

### Foundry/Magentic routing

Dynamic routing belongs to GraphSpec/runtime policy. Policy produces or validates
a realized route; MiniGraph executes that route without becoming a model or
agent-selection policy engine.

---

## R6 — Independent evaluator and verification layer

Karpathy's March of Nines and Foundry's golden-dataset/evaluator patterns are
explicitly retained above the kernel.

Canonical law:

```text
mutator != evaluator
```

Required components:

- deterministic harnesses when a deterministic oracle exists;
- golden datasets;
- independent Verification/Sentinel nodes;
- versioned/frozen judge prompts, models, and rubrics during comparisons;
- separate quality/cost/latency/safety/reliability metrics;
- explicit promotion thresholds and evaluator versioning.

A Verification node is an ordinary runtime node. The kernel does not define what
"verified" or "acceptable" means.

---

## R7 — Isolation, effect authority, endpoint security, and hardware policy

Foundry sandboxing is retained as a principle, but security policy remains
outside the scheduler.

```text
perpetua-core
  generic tool invocation + validation mechanics

orama-system
  effect classification, approvals, sandbox requirement, runtime policy

oramasys/agate
  hardware capability, affinity, and routing contract

PT security/endpoint modules during migration
  concrete network authorization and transport hardening
```

Network/endpoint policy, telemetry exporters, provider clients, and hardware
routing MUST NOT migrate into `engine.py` merely because graph nodes use them.

---

## R8 — Perpetua-Tools capability unbundling

PT is currently an integration-rich monorepo. Unbundle it through contract-first
strangler migration, not bulk copying.

Classify each feature before movement:

```text
universal execution mechanic
  -> perpetua-core candidate

spec / methodology / evaluator / effect policy
  -> orama-system

application/service composition
  -> oramasys/oramasys

hardware capability / affinity contract
  -> oramasys/agate

memory / observability / coordination / security / provider adapter
  -> satellite module boundary; repository split only when justified
```

Existing PT package boundaries such as `packages/endpoint-policy`,
`packages/net_utils`, `packages/local-agents`, `packages/alphaclaw-adapter`, and
`packages/alphaclaw-mcp` are migration inputs, not automatic final ownership.

Detailed feature-cluster mapping and the strangler procedure live in:

[2026-08-29-pattern-backlog-and-pt-unbundling.md](2026-08-29-pattern-backlog-and-pt-unbundling.md)

A migration is not complete while two writable sources of truth silently
coexist. Transitional mirrors MUST declare authority and a sunset condition.

---

## R9 — Optimizer and trace learning

Production graph mutation remains after the foundations above.

Required prerequisites:

```text
versioned GraphSpec
+ deterministic reducers/joins
+ durable deterministic resume
+ explicit effect policy
+ trace corpus
+ frozen independent evaluator
+ candidate isolation
+ promotion gate
```

Trace-derived candidates graduate through governed review/memory; runtime does
not silently self-rewrite.

---

## Merge order

1. verify core PR #1 at its exact current head;
2. resolve every still-valid core review finding by evidence, not assumption;
3. merge the core reconciliation;
4. verify orama-system PR #333 at its exact current head;
5. merge the architecture/pattern/unbundling plan;
6. start R2.5/R3 from then-current `main` in a correctly numbered dated branch;
7. keep R4/R5/R6/R7 as explicit contracts rather than inflating `engine.py`;
8. unbundle PT cluster-by-cluster with parity evidence;
9. start R9 only after durability and independent evaluation are operational.

Do not bundle R3+ merely because this plan describes them.

---

## Completion definition

This reconciliation phase is complete when:

- core R0–R2.4 changes are merged from the reviewed branch;
- both latest core findings are closed on exact-head evidence;
- this canonical architecture record and pattern placement are merged;
- old line-count/freeze/blanket-immutability rules are not current authority;
- `orama-system` clearly owns GraphSpec/lint/evaluation/runtime-policy authority;
- PT unbundling has one explicit destination/authority classification per
  capability cluster;
- no duplicate plugin namespace, graph scheduler, or silent writable mirror
  survives.
