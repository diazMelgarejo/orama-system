# D-LG-6 — R3 mechanics: fan-out regions, reducers and joins

**Status:** proposed, implementation directed by the operator on 2026-10-10. It becomes
approved when the Core pull request that implements it is reviewed and merged. It builds on
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
   join admits a set of successful branches or fails the region.
6. Reducers fold the admitted deltas into one delta, which merges into state **once**.
   Everything after this point carries the committed state, so a checkpoint taken at any
   branch event is a post-commit checkpoint.
7. `node.end` is emitted for each admitted branch in name order, with that branch's own delta.
8. `superstep.commit` is emitted with the folded delta. Its observation carries a
   **provenance map** from state field to the branches that supplied it. The public
   `GraphEvent` carries only branch names.
9. `edge.selected` runs from the source to `then`, and the loop continues.

**Determinism rule.** For fixed inputs and fixed branch results, the committed state, the
event order and the failure set are identical whatever the completion order. A test that
merges in completion order must fail.

**Interrupts.** If any branch raises an interrupt, the run ends `interrupted` with the
lowest-named interrupting branch recorded. No delta from the region is committed. The state
is the snapshot at region start plus the interrupt metadata. Resuming a region is R4's job.

**Failures.** A branch exception that is not an interrupt is a failure. If the join refuses
the region, the scheduler raises an `ExceptionGroup` of the branch failures, in name order.
Outer cancellation cancels every branch and propagates. No partial commit happens either way.

**Cost.** Waiting for all branches means a losing `first_success` branch still runs to
completion. Early cancellation depends on timing and is deferred. Effect admission still sees
every branch as a possible effect.

## Reducers

A reduced field's branch delta is a **contribution**, not a replacement. Outside regions,
deltas replace state exactly as before. For a field with a declared reducer, the reducer runs
whenever at least one admitted branch wrote it. For an undeclared field the default applies.

| Kind | Fold over contributions in name order | Refuses when |
| --- | --- | --- |
| `reject_conflict` (default) | The single value, or the common value if all writers agree (`==`) | Two writers disagree |
| `first` | The first writer's value | Never |
| `last` | The last writer's value | Never |
| `concat` | `base + c1 + c2 …` for list fields | A value or the base is not a list |
| `union` | Lists: base items, then unseen items in order (equality-based). Dicts: shallow merge | Dict key written with unequal values by two branches; mixed types |
| `custom` | `fn(base, contributions) -> value` with a stable `module:qualname` reference | The function raises |

Disagreement raises `ReducerConflict` (a `ValueError`) naming the field and the branches.
A value of the wrong type raises `TypeError`. Both are raised before anything commits. A
`custom` reducer must be a pure fold. Core records its reference in the spec and never
imports it from a string.

## Joins

A region with no declared join behaves as `all`. A declared `all` with no parameters is
dropped when the spec is built, so the two forms share one `graph_id`. Only the sole join of a
real fan-out source is dropped; orphan or duplicate declarations are kept so lint reports them.

| Kind | Admits | Region fails when |
| --- | --- | --- |
| `all` | Every branch | Any branch failed |
| `any` | Every successful branch | No branch succeeded |
| `first_success` | The lowest-named successful branch only | No branch succeeded |
| `quorum` (`quorum = k`) | Every successful branch | Fewer than `k` succeeded |
| `custom` | The names returned by `fn(outcomes) -> names` | The function raises, returns an unknown or failed name, or returns no name |

`custom` is a pure admission function over a tuple of per-branch outcomes (name, ok, error
type name). It cannot change a delta. Reducers still fold what it admits.

## Schema

`GraphSpec` gains two fields. `EdgeKind` gains `fanout`. Nothing else in schema `"1"` changes.

| Item | Shape |
| --- | --- |
| `GraphSpec.reducers` | Tuple of `ReducerSpec(field, kind, ref)`, sorted by field |
| `GraphSpec.joins` | Tuple of `JoinSpec(source, kind, quorum, ref)`, sorted by source |
| `EdgeSpec.kind = "fanout"` | `target = then`, `declared_targets = branches`, no `router_ref` |
| `schema_version` | `"2"` iff any fan-out edge, reducer or join exists, else `"1"` |

**Hash compatibility.** The schema `"1"` canonical payload is byte-identical to today's. The
schema `"2"` payload adds `reducers` and `joins`. `GraphSpec.create` chooses the version
itself. Asking for `"1"` with R3 features is an error. `from_dict` accepts `"1"` and `"2"`. A
Core release without this change rejects `"2"`, which is the intended fail-closed behaviour.

**Construction checks.** `EdgeSpec`, `ReducerSpec` and `JoinSpec` reject impossible shapes
when built: fan-out needs a target and two or more unique branches, a quorum join needs
`quorum >= 1`, and only `custom` kinds carry a reference.

**Lint.** Deterministic, execution-free codes GS201 to GS214: fan-out source is a node (201),
branch is a node (202), branch is not the source, target or a sentinel (203), branch has no
own edge (204), target is a node (205), no node in two regions (206), join source is a
fan-out source (207), one join per source (208), quorum within the branch count (209), one
reducer per field (210), R3 features need schema `"2"` (211), schema `"2"` needs R3
features (212). Warnings: a `custom` join or reducer without a stable reference (213), and
reducers declared without any region (214).

## Policy

Oramasys adds two restrict-only objects to `GraphPolicy` (policy schema `"2"`):

- `reducer_restrictions`: fields that must have a declared reducer, and (field, kind) pairs
  that are forbidden. Field `"*"` means any field.
- `join_restrictions`: an allow-list of join kinds and a minimum `quorum`.

`bind_policy` checks them against the GraphSpec and refuses on violation. A policy with default
restrictions keeps its `policy_id`, so existing policies and bindings stay valid. A policy
cannot add, change or remove a declaration, and an unknown key still fails closed.

## Registry and lockstep

The ownership registry changes in **one reviewed step**, after Core merges and Oramasys
promotes its production pin: GraphSpec `reducers` and `joins`, the two GraphPolicy fields,
and the `fanout` edge kind become `implemented`; new records `ReducerSpec`, `JoinSpec`,
`ReducerRestrictions` and `JoinRestrictions` are added; the provisional `join` edge kind is
**dropped** because a join is a spec entry, not an edge. The registry and its Oramasys
snapshot change together and the pinned digest changes with them.

Until then the registry keeps those entries `planned`, which the conformance tests require.

Sequence: this ADR, then the Core pull request, then the Oramasys policy pull request (tested
against a candidate Core), then the pin promotion with the registry step.

## Alternatives

| Option | Assessment |
| --- | --- |
| Extend `parallel_dispatch` with a merge rule | Rejected: outside the scheduler, invisible to events, lint and `graph_id` |
| General multi-edge frontier (Pregel style) | Rejected for v1: needs dynamic frontier semantics and resume design first |
| Merge in completion order | Rejected: not deterministic |
| First-completed wins for `any` | Rejected: depends on timing; `first_success` is name-ordered |
| Reducer applied to full replacement values | Rejected: forces every branch to repeat the base for `concat` |
| Reducers and joins as runtime arguments | Rejected by D-LG-5 |
| Cancel losing branches early | Deferred: timing-dependent, needs effect semantics from R4 |

## Acceptance and rollback

- Core tests cover: completion-order independence, conflict refusal, each reducer and join
  kind, interrupt precedence, failure grouping, step accounting, `graph_id` stability for
  schema `"1"` graphs, lint codes, and a deliberately broken completion-order merge that the
  suite must reject.
- Oramasys tests cover restrictions, `policy_id` stability and the registry step.
- No Core release carries this change until its pull request is reviewed and merged.

Rollback reverts the Core pull request. Schema `"1"` graphs never changed, so they are
unaffected. Schema `"2"` documents become unreadable by design.

## Supersession

| Earlier statement | Status |
| --- | --- |
| Plan Task 5, "declared branch order determines merging" | Read as canonical ascending branch name; authoring order is not hashed |
| Plan Task 5, `ANY` as a join | `any` admits all successes; `first_success` is the single-winner form |
| Registry planned `join` edge kind | Dropped in the registry step; a join is a `JoinSpec` |
| `parallel_dispatch` last-wins merge | Unchanged for existing callers; superseded for new graphs by regions |
