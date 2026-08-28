<!-- lint-ignore LINT-013 -->
# MiniGraph Final Reconciliation — Execution Plan

**Date:** 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Status:** in execution  
**Architecture:** [canonical record](../57-minigraph-final-reconciliation.md)

## Branch isolation

Both branches were created from frozen `main` tips before writes.

| Repository | Base main | Working branch |
| --- | --- | --- |
| `oramasys/perpetua-core` | `8c063f41f6b8d31f6a8aa71d6c78155ea9690c90` | `2026-08-27-minigraph-final-reconciliation` |
| `diazMelgarejo/orama-system` | `568b4167edaa25658b3a001b4f2273f774014f9a` | `2026-08-27-minigraph-final-reconciliation` |

The two already-open reconciliation PRs retain the branch name shown above as
an approved one-time exception. Any successor branch MUST use the repository
format `yyyy-mm-dd-NNN-brief-summary`.

The sandbox could not create network-backed local Git worktrees because GitHub
DNS was unavailable to the shell. Isolation was therefore preserved with fresh
remote branches pinned to the exact `main` SHAs above.

Do not rewrite this history as if literal local worktree directories existed.

---

## R0 — Characterize contracts

Add or retain tests for:

- linear traversal and ordered visit provenance;
- conditional routing after state merge;
- bounded cycles;
- START/END behavior;
- structural interrupts;
- compile detachment;
- kernel no-plugin/no-optional-import architecture;
- async function nodes;
- sync function nodes;
- async callable objects;
- sync functions returning awaitables;
- actual `ToolNode` execution inside MiniGraph;
- invalid node deltas;
- empty/non-string routes;
- optional interrupt payload;
- exact max-step fields.

Behavioral bugs are not closed until represented by a regression test.

---

## R1 — Reconcile the kernel

Target ownership:

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
5. route on updated state;
6. make END the sole normal terminal route;
7. reject empty/non-string routes;
8. count completed executions in `MaxStepsExceeded.steps`;
9. report the most recently entered node in `last_node`;
10. support optional structural interrupt payload;
11. remove the dead `interrupt_handler` constructor API;
12. keep the builder mutable and compiled topology detached;
13. do not introduce a physical-line gate.

Core implementation commit:
`853b9b9243aa6fbab735ff4ae0d980f16281d5d5`.

Current core PR head after adding the test workflow:
`fc59956021e07bac05d4d51dd6452e6ff2ecbf32`.

---

## R2 — One scheduler/event seam

Add a control-only `GraphEvent` stream from the scheduler used by `ainvoke()`.

Required public events:

```text
edge.selected
node.start
node.end
interrupt
done
```

Rewrite the existing streaming plugin as a thin adapter over
`CompiledGraph.asteps()`.

Acceptance:

- no streaming traversal through private `_nodes`/`_edges`;
- no duplicate max-step implementation;
- no duplicate interrupt implementation;
- no provider/exporter/persistence dependency in `GraphEvent`.

Implemented on the same core branch and PR.

---

## R2.5 — Verification

A minimal `.github/workflows/test.yml` was added to `perpetua-core` for the full
package tests on Python 3.11 and 3.12 in future pull requests.

Verification rules:

- the exact PR head is authoritative;
- CodeRabbit/review and deterministic tests are separate gates;
- never claim green CI when GitHub Actions did not run;
- record repository-level verifier limitations explicitly.

Current evidence:

- baseline main recorded 62 passing tests;
- targeted sandbox execution passed the reconciled high-risk paths;
- the targeted sweep included real `ToolNode` execution inside MiniGraph;
- it also covered returned-awaitable, routing, strict contracts, cycle
  accounting, compile detachment, and streaming parity;
- CodeRabbit produced no actionable implementation comments;
- GitHub Actions had not started the new workflow on the current PR.

Core PR: <https://github.com/oramasys/perpetua-core/pull/1>

---

## R3 — Parallel reducers and joins — deferred

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

## R3/R4 — Durable deterministic resume foundation — deferred implementation

Upgrade the existing SQLite checkpointer after the execution seam is stable.

This phase is **ADOPTED architecture**, not rejected scope. The target is durable
deterministic resume from an explicit compatible checkpoint boundary.

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

Required saved identity/state includes at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
saved session/graph state
```

Before automatic retry/resume of effects, define replay boundaries, effect
identity, idempotency, and deduplication.

The target is precise resumability, not total reversibility. Restoring graph
state cannot rewind time or erase an external side effect that already happened.
External effects require idempotency, dedupe, compensation, or explicit
human/policy reconciliation.

---

## R4 — GraphSpec in `orama-system` — deferred

The final face-off resolves ownership as follows.

```text
diazMelgarejo/orama-system
  methodology + canonical design
  GraphSpec / NodeSpec / EdgeSpec authority
  compiler / lint / version selection
  evaluation / runtime policy
        |
        | compiles/targets
        v
oramasys/perpetua-core
  realized graph execution mechanics
```

`perpetua-core` MUST NOT import upward from `orama-system`.

`oramasys/oramasys` may later consume or host an approved GraphSpec projection.
Ownership does not move there implicitly; that requires a new architecture
record.

The GraphSpec phase MUST NOT inflate `perpetua-core/graph/engine.py`.

---

## R5 — Optimizer and trace learning — research only

Do not ship production graph mutation until there is a versioned `GraphSpec`,
trace corpus, locked evaluator, multi-objective metrics, candidate isolation,
and a promotion gate.

Required authority separation:

```text
mutator != evaluator
```

Trace-derived candidates should graduate through governed review/memory, not
direct runtime self-rewrite.

---

## Merge order

1. verify `perpetua-core` R0–R2 with every available deterministic gate;
2. review the exact core PR head and resolve substantive findings;
3. merge the core reconciliation;
4. merge this canonicalization after review and Markdownlint are green;
5. start R3 only from the then-current `main` in a new branch/PR.

Do not bundle R3+ merely because this plan already describes it.

---

## Completion definition

This reconciliation is complete when:

- core R0–R2 changes are merged from the pinned branch;
- this canonical architecture record is merged;
- obsolete MiniGraph line-count/freeze rules are no longer current authority;
- `orama-system` clearly owns GraphSpec/lint/evaluation/runtime-policy authority;
- repository ownership is unambiguous for future agents;
- no duplicate plugin namespace or graph scheduler survives.
