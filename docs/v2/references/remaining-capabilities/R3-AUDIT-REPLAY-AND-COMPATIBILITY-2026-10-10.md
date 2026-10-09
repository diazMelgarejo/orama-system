# R3 audit, replay and compatibility qualification

**Date:** 2026-10-09 UTC / 2026-10-10 Asia/Manila. Current qualification of the
[revision-2 plan](IMPLEMENTATION-PLAN-REV2-2026-10-10.md) and
[D-LG-6](../loop-graph-compatibility-2026-10-09/ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md).
Historical evidence remains unchanged. Review fixes are not full upstream replacement.

## Current branch facts

- Oramasys #24 is merged; its duplicate-record and wrong-record ownership fixes
  are present. Oramasys #25 originally lacked those newly merged tests. Integrating
  main exposed five candidate-registry failures, despite its earlier green CI.
- Orama #391 merged into the #390 branch, not directly into main. The D-LG-6 ADR
  is present in #390. At the initial exact-head poll, its skill-scanner was still
  running; pending is not success.
- Core #9 and Oramasys #25 remain candidate implementations. Production Core stays
  `04759a50c748444ff97136ea95c1e1289eac3a1a`; candidate pin promotion is test-only.

## Verified fixes and their contracts

| Gap | Corrected behavior | Proof |
| --- | --- | --- |
| Unknown JSON fields discarded outside graph identity | Graph, node, edge, reducer and join descriptions reject unknown fields; metadata remains the extension location | Five parser regressions fail before the fix and pass afterward |
| Duplicate declarations collapse before policy restriction checks | Structural lint runs before restriction dictionaries are built | Duplicate reducers and joins cannot hide a forbidden choice; GS210/GS208 |
| Faulty custom fold mutates prior observations | Custom reducer receives detached base and contributions | Mutating then raising cannot rewrite the pre-commit snapshot |
| Candidate omitted merged registry tests | Integrate #24 and run full conformance in both lanes | Candidate and production-Core profiles compare exact live fields and literals |
| Ownership test confuses Core owner with GraphSpec record | Requires both exact owner and record; reject duplicates before indexing | Mutations placing computes on NodeSpec/EdgeSpec and conflicting duplicate records are rejected |
| Reducer/join literal drift is invisible | Register producer and consumer unions, require complete inventory and exact values | Independent review reproduced the gap; missing-inventory and consumer-drift mutations now fail |
| Earlier provenance/default-join findings | Existing #9 fixes verified, not reimplemented | Provenance reaches plugins; orphan/duplicate implied defaults survive to lint |

## How replay actually works today

| Function or record | Actual behavior | What it does not establish |
| --- | --- | --- |
| `GraphSpec.from_dict/from_json` | Read structural data and verify its canonical hash; import no callable | Executable artifact authenticity, resume position or authorization |
| `SqliteCheckpointer.save/load_latest` | Append/read session-node-state snapshots | Checkpoint lineage, frontier, graph version, branch outcomes, effect identity or durable resume |
| `resume_policy(MERGE)` | Merge supplied values into scratchpad | Restart traversal or verify human authority |
| `resume_policy(DROP)` | Update only the selected key, retaining other keys | Delete the entire scratchpad, approve an effect or clear interrupt status |
| `CompiledGraph.ainvoke(loaded_state)` | Start at START using the supplied state | Continue from the saved node; it can execute earlier effect nodes again |
| `EffectDeclaration(replay="idempotent")` | Declare intent; binding requires a logical operation ID | Provider deduplication, a grant, or safe automatic replay |
| Provider/outbound ledger | Record evidence according to its existing contract | A universal effect dedupe store or cross-provider exactly-once execution |

Do not call these operations durable replay. A human clicking resume cannot supply
the missing transaction, cursor or provider reconciliation semantics. The existing
Pydantic AI bridge remains offline-only; pending tools are never autoapproved.

## R3 execution and audit flow

1. A trusted builder binds callable objects and creates a structural description.
   `module:qualname` is a reference, not a digest of code; artifact admission must
   additionally bind implementation, registry, policy and provider contracts.
2. Structural validation rejects invalid declarations. Policy binding checks its
   exact graph identity and narrows permitted choices. It does not perform runtime
   Phylax/Telos/Agate admission or grant approval.
3. The source node executes. The one `_run()` scheduler emits a region-start
   snapshot; each branch gets its own deep copy. Every branch settles.
4. Interrupts take precedence. Otherwise, joins select successful branches and
   reducers fold them in ascending branch-name order. Custom folds are isolated.
5. One local state merge commits. Only afterward do branch `node.end` and
   `superstep.commit` observations describe that committed state. Provenance
   reaches each detached plugin payload.
6. The legacy checkpointer stores state on node-end events. It does not persist
   the commit provenance or a resumable frontier. Audit consumers must not infer
   missing causal evidence from those rows.

**Atomicity boundary:** atomic means the local state delta commits once. Branches
may already have performed external effects when an interrupt, conflict or join
refusal occurs. R3 cannot roll those effects back. Name-ordered `first_success`
still waits for every branch; it is not a first-completed cancellation primitive.

## Registry qualification without a premature production flip

The baseline `ownership-registry.json` and its pinned snapshot are preserved.
Two additive, explicitly candidate profiles describe exact test targets:

- `ownership-registry-policy-r3.json`: new policy restrictions on unchanged Core
  schema 1; Core reducer/join fields remain planned and absent.
- `ownership-registry-core-r3.json`: policy restrictions plus candidate Core
  schema 2, reducer/join records and literals, plus the fanout literal. No provisional join edge
  is accepted: joins are spec records.

Oramasys keeps byte-identical snapshots and pins all three digests. Tests select
the profile by the installed Core capability, independently assert its schema,
and fail if any expected field/literal is absent, extra or incorrectly planned.
The required candidate lane still fails when R3 is absent. Both CI lanes check
the canonical profiles at an immutable Orama revision.

These are target contracts, not assertions that candidate code is merged. The
baseline production registry changes only during reviewed Core integration and
consumer-pin promotion. Preserve candidate evidence after promotion.

## Compatibility verdict

Full 100% drop-in LangGraph/LangChain compatibility is **not established**.
Known limitations are explicit: the LangGraph exporter refuses fanout; dynamic
Send, nested regions, durable checkpoint wire formats and native replay remain
deferred; the LangChain adapter is not upstream Runnable type identity, ignores
some configuration and buffers synchronous streams. Offline oracle passes prove
their tested cells, not every public API or version.

Keep current supported adapter behavior and schema-1 hashes unchanged. Absorb
Pydantic AI's typed outputs, explicit dependency mapping, usage limits and pending
tool semantics through the existing lazy bridge. Production effects require the
complete authority, transport and durable-effect vertical slice first.

## Remaining work and measurable closure

| Plan workstream | Current qualification | Next executable gate |
| --- | --- | --- |
| Task 0 inventory | Partial; source-backed bounded audit here | Enumerate pinned API/version cells and adjacent requirement IDs; no untested parity percentage |
| Tasks 1–2 authority/observations | Structural binding and detached provenance tested; executable admission and criticality taxonomy incomplete | Real Phylax artifact admission and critical/noncritical delivery contract |
| Task 3 durable HITL/effects | Not implemented by R3 | Transactional grants/reservations, concurrency, restart/revocation and unknown-outcome tests |
| Task 4 foreign transport | Production Pydantic bridge remains refused | Actual Telos-mediated SDK connections or enforceable worker containment; sandbox qualification |
| Task 5 R3 | Candidate bounded single-level regions | Reviewed Core merge; exact immutable pin promotion and registry step |
| Task 6 R4 | State snapshots only | Lineage/frontier schema, migrations, fencing and effect reconciliation before replay |
| Tasks 7–8 replacement/bridges | Partial protocol adapters and offline bridge | Declared version cohorts, unchanged upstream fixtures and real transport/HITL gates |
| Tasks 9–10 adjacent evaluation/memory/controller | Separate canonical designs | Independently specified and tested slices; no automatic platform-wide enablement |
| Task 11 closure | This audit adds producer/consumer/docs evidence | Exact-head CI, production-pin rerun and PT append-only memory; no merge without authorization |

The broad plan remains a tracked implementation program. This bounded review does
not claim the unimplemented rows are complete or enable their effects implicitly.

## Local verification

Core's complete suite passes 255 tests with 90.96% coverage, including the external
Agate fixture. The real offline oracle environment uses LangGraph 1.0.3,
LangChain Core 1.0.7 and Pydantic AI slim 1.0.18. Exact final consumer totals and
published heads are recorded in the PR verification comments and PT memory.
These counts are evidence for the tested cells, not an upstream parity claim.
