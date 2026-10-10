# D-LG-7 — R4 safety, compatibility and platform program


**Status:** approved by the operator on 2026-10-10. This approves the program direction and
the named contract revisions; it does not waive any implementation, evidence, or release gate.
**Number:** D-LG-7 was free in the live index on 2026-10-10 (searched all of `docs/`).
Re-check at T0 before citing it elsewhere.
**Scope:** an umbrella decision. Each subsystem contract is a separate file with its own
status, so one can be accepted, amended or rejected without the others.


## Context


R3 is merged: bounded single-level fan-out, reducers, joins, schema "2"
([D-LG-6](../loop-graph-compatibility-2026-10-09/ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md)).
Doc 57 §10 and §11 still say reducers are deferred and durability comes before resume.
This ADR carries the program past R3: safe durable execution, versioned upstream
replacement and a self-consistent platform, in the operator's priority order.


### R3 guarantees R4 must preserve


1. Fan-out is bounded and single-level, inside the one existing scheduler.
2. Every branch settles before a join selects. `first_success` selects the
   lowest-named successful branch, not the first to finish. `any` admits every success.
3. Reducers fold in ascending branch-name order, never authoring or completion order.
4. Branch inputs and custom-fold arguments are detached. That limits mutation leaks.
   It does not make a callable pure or allow I/O inside it.
5. An interrupt prevents the region delta committing. The merge is atomic for local
   state only; external writes may already have happened and are not undone.
6. Graphs without R3 features keep schema "1" and an unchanged `graph_id`. A callable
   name is a reference, not a code digest.


### What resume and replay do today


| Surface | Actual meaning | Missing durable guarantee |
| --- | --- | --- |
| `GraphSpec.from_dict/from_json` | Validate structure and hash; import no callable | Executable authenticity, authority |
| `SqliteCheckpointer.save/load_latest` | Store and read node-state snapshots | Cursor, lineage, branch receipts, grants, effects |
| `resume_policy(MERGE)` | Merge supplied scratchpad values | Position, human authorization |
| `resume_policy(DROP)` | Update one key, keep others | Clearing traversal/interrupt state, any grant |
| `CompiledGraph.ainvoke(loaded_state)` | **Traverses from `START` with loaded state** | Continuing from the saved node |
| `EffectDeclaration(replay="idempotent")` | States intent, requires an operation ID | Provider dedupe, safe replay |
| Provider/outbound ledger | Evidence under its own contract | Universal effect dedupe |


Verified against Core `main` (`ainvoke` delegates to `_run`, which resolves the edge
out of `START`). A legacy snapshot must never be reinterpreted as a resumable
checkpoint; the START path stays as an explicit compatibility path.


## Decision


| ID | Decision | Status |
| --- | --- | --- |
| P1 | Safety outranks compatibility and platform expansion | Operator confirmed |
| P2 | Forward LC/LG and permitted backward-v1 compatibility outrank expansion | Operator confirmed |
| P3 | Internal consistency and external interoperability remain required | Operator confirmed |
| A1 | One Core scheduler; neutral mechanics separated from authority | Retained |
| A2 | Reducer/join declarations in Core GraphSpec; policy restrict-only | Retained (D-LG-5/6) |
| A3 | Transactional approval/effect spine plus durable continuation | Proposed |
| A4 | Single authoritative host first; remote workers later, no second writer | Proposed |
| A5 | Versioned isolated replacement cohorts; no implicit import takeover | Proposed |
| A6 | Actual Telos-mediated connections or enforceable containment; no fallback | Existing authority, applied |
