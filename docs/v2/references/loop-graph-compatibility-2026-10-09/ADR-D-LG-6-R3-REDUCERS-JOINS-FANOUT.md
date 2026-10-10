# D-LG-6 — R3 mechanics: fan-out regions, reducers and joins


**Status:** approved by the operator on 2026-10-10. Implementation evidence: Perpetua Core
PR #9 (merged as `4d217f6`) and Oramasys PR #25 (merged as `f4dbf33`). Production
Oramasys remains pinned to pre-R3 Core until P0 requalification; approval of these mechanics
does not claim that the production dependency has already been promoted. It builds on
[D-LG-5](ADR-D-LG-5-REDUCER-JOIN-DECLARATIONS.md), which already settled *where* the
declarations live. This ADR settles *what they mean*.


Scope: fan-out, reducers, joins, their schema, their events and their lint. Out of scope and
still deferred: dynamic dispatch (`Send`), nested regions, durable resume (R4), and mapping
regions onto LangGraph channels in the export adapter.


## Context


MiniGraph has one scheduler, `CompiledGraph._run()`, and one outgoing edge per node. It cannot
run two nodes at once. The only fan-out today is the helper `parallel_dispatch`, which merges
branch deltas with "the last branch in the list wins". That rule hides data loss, and the
helper sits outside the scheduler, so no event, lint or hash sees it.


R3 needs three guarantees together:


1. The result of a fan-out never depends on which branch finishes first.
2. Conflicting writes are refused, not silently resolved.
3. What a graph computes is part of its `graph_id` (D-LG-5), and the scheduler stays single.


## Decision


| # | Decision |
| --- | --- |
| 1 | A **fan-out region** is a diamond: one source node, two or more branch nodes, one `then` target. It runs inside the same `_run()` loop. No second scheduler. |
| 2 | All branches run concurrently on **one snapshot** (the state after the source node). Their deltas commit **once, atomically**, in canonical order: ascending branch name. |
| 3 | **Reducers** are declared per state field in the GraphSpec. A field with no reducer uses the default, `reject_conflict`. |
| 4 | A **join** is declared per region in the GraphSpec. It decides which settled branches are admitted. It never decides timing: every branch settles before the join is evaluated. |
| 5 | Specs that use none of this keep schema `"1"` and an identical `graph_id`. Specs that use any of it are schema `"2"`. |
| 6 | Oramasys policy can only restrict reducer and join choices (D-LG-5). |


## The region


```text
source ──fanout──▶ { b1, b2, … bn } ──commit──▶ then
```


- The source is a node. Its outgoing edge is the `fanout` edge. `then` is a node or `END`.
- `fanout` is a new edge kind. `declared_targets` holds the branch names and is
  **authoritative** for this kind (it stays advisory for `conditional`). `target` holds `then`.
- A branch is a node with **no outgoing edge of its own**. A fan-out region ignores branch
  edges, so lint rejects one rather than ignoring it silently.
- v1 limits: at least two branches, no branch is the source or `then`, a node belongs to at
  most one region, and regions do not nest. Cycles through `then` stay bounded by `max_steps`.


## Execution


1. The source node runs and its delta merges as today.
2. `superstep.start` is emitted with the branch names. Each branch gets `node.start`, in name
   order. All branches receive the same snapshot, each as its own deep copy, so a branch that
   mutates its input cannot affect a sibling or the committed state. The branch names are
   appended to `nodes_visited` in name order before they run.
3. `max_steps` is checked once for the whole region: `steps + branches` must not exceed it.
   Each branch that succeeds counts as one step.
4. Branches run concurrently. The scheduler waits for **every** branch to settle.
5. Outcomes are evaluated in name order. An interrupt takes precedence (below). Otherwise the
