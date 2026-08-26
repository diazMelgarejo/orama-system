<!-- lint-ignore LINT-013 -->
# MiniGraph Final Reconciliation — Execution Plan

**Date:** 2026-08-27  
**Status:** In execution  
**Canonical architecture:** [`../57-minigraph-final-reconciliation.md`](../57-minigraph-final-reconciliation.md)

## Branch isolation

Both branches were created from frozen `main` tips before writes:

| Repository | Base main | Working branch |
| --- | --- | --- |
| `oramasys/perpetua-core` | `8c063f41f6b8d31f6a8aa71d6c78155ea9690c90` | `2026-08-27-minigraph-final-reconciliation` |
| `diazMelgarejo/orama-system` | `568b4167edaa25658b3a001b4f2273f774014f9a` | `2026-08-27-minigraph-final-reconciliation` |

The execution environment could not create network-backed local Git worktrees because GitHub DNS was unavailable to the sandbox. Isolation was therefore preserved with fresh remote branches pinned to the exact main SHAs above. Do not rewrite this history as if literal local worktree directories existed.

---

## R0 — Characterize the contracts

Add/retain tests for:

- linear traversal and ordered visit provenance;
- conditional routing after state merge;
- bounded cycles;
- START/END behavior;
- structural interrupts;
- compile detachment;
- kernel no-plugin/no-optional-import architecture;
- async function node;
- sync function node;
- async callable object;
- sync function returning an awaitable;
- actual `ToolNode` installed in a real MiniGraph;
- invalid node delta;
- empty/non-string route;
- optional interrupt payload;
- exact max-step fields.

Gate: behavioral bugs are represented as tests before being considered closed.

---

## R1 — Reconcile the kernel

Target runtime ownership:

```text
MiniGraph builder
      |
      v
compile()
      |
      v
CompiledGraph scheduler
```

Required changes:

1. keep `PerpetuaState` canonical;
2. call first, then `inspect.isawaitable(result)`;
3. require dict node deltas;
4. preserve `nodes_visited: list[str]`;
5. evaluate conditional edges on updated state;
6. make END the sole normal terminal route;
7. reject empty/non-string routes;
8. define `MaxStepsExceeded.steps` as completed executions;
9. define `last_node` as most recently entered node;
10. use optional structural interrupt payload;
11. remove dead `interrupt_handler` constructor API;
12. make `CompiledGraph` the runtime and keep source builder mutable;
13. do not introduce an arbitrary physical-line gate.

Current implementation commit: `oramasys/perpetua-core@853b9b9243aa6fbab735ff4ae0d980f16281d5d5`.

---

## R2 — Establish one scheduler/event seam

Add a control-only `GraphEvent` stream from the same scheduler used by `ainvoke()`.

Required public events:

```text
edge.selected
node.start
node.end
interrupt
done
```

Rewrite the existing streaming plugin as a thin adapter over `CompiledGraph.asteps()`.

Acceptance:

- no traversal through streaming's own `_nodes`/`_edges` loop;
- no duplicate max-step implementation;
- no duplicate interrupt implementation;
- no provider/exporter/persistence dependency in `GraphEvent`.

Implemented on the same core branch/PR.

---

## R2.5 — Exact-head verification

A minimal `.github/workflows/test.yml` was added to `perpetua-core` to run the full package tests on Python 3.11 and 3.12 for future pull requests.

Verification rules:

- exact PR head, not an earlier local checkout, is authoritative;
- CodeRabbit/review status is independent from deterministic tests;
- if GitHub Actions does not run, report that fact rather than asserting green CI;
- merge only after the available deterministic verifier is green or the absence of repository Actions is explicitly accepted as a repository limitation.

Core PR: <https://github.com/oramasys/perpetua-core/pull/1>

---

## R3 — Parallel reducer/join contract — deferred

Upgrade the existing `parallel.py`; do not create a competing subsystem.

Design before implementation:

```text
reducers: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
joins:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Required properties:

- deterministic under branch completion reordering;
- explicit conflict behavior;
- explicit partial-failure behavior;
- no race-order-defined state.

---

## R3/R4 — Durable checkpoint lineage — deferred

Upgrade the existing SQLite checkpointer after the execution seam is stable.

Required identity:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
```

Before automatic retry/resume of effectful nodes, define idempotency/dedupe semantics.

---

## R4 — GraphSpec/compiler/linter in `oramasys` — deferred

Ownership is now resolved:

```text
orama-system
  methodology / canonical design

oramasys/oramasys
  GraphSpec / NodeSpec / EdgeSpec
  compiler / lint / runtime policy
        |
        v
oramasys/perpetua-core
  realized graph execution
```

The GraphSpec phase must not inflate `perpetua-core/graph/engine.py`.

---

## R5 — Optimizer/trace learning — research only

Do not ship production graph mutation until there is a versioned GraphSpec, trace corpus, locked evaluator, multi-objective metrics, candidate isolation, and promotion gate.

Required authority separation:

```text
mutator != evaluator
```

Trace-derived candidates should graduate through governed review/memory, not direct runtime self-rewrite.

---

## Merge order

1. make `perpetua-core` R0–R2 deterministic tests green;
2. review exact core PR head and resolve substantive findings;
3. merge `perpetua-core` reconciliation;
4. merge this `orama-system` canonicalization after its docs/lint checks are green;
5. start R3 only as a new branch/PR from the then-current main.

Do not bundle R3+ into the R0–R2 merge merely because the architecture record already describes them.

---

## Completion definition

This reconciliation is complete when:

- core R0–R2 changes are merged from the pinned branch;
- the canonical architecture record is merged;
- historical MiniGraph line-count/freeze rules are no longer treated as current authority;
- future agents can identify exactly which repository owns kernel execution, graph specification, runtime policy, and PT telemetry/memory concerns;
- no duplicate plugin namespace or scheduler survives.
