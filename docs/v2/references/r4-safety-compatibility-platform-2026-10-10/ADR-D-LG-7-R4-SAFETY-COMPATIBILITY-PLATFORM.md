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
| A7 | R3 settle-all and name order unchanged; early-winner timing is a later feature | Proposed |

### Arbitration rule

Identify the conflict, name the higher-priority invariant, record the affected cell in
the compatibility matrix. A safety refusal is never presented as implemented upstream
behaviour. When exact parity needs missing neutral mechanics, add a reviewed Core
capability; never embed a second scheduler in a facade. An incompatibility required for
safety is explicit, versioned and visible in the support matrix.

The full replacement target is retained. Releases may qualify bounded cohorts, but every
unimplemented inventory cell stays visible with an owner and next gate. Scope accounting
is not semantic compatibility.

## Alternatives

| Approach | Benefit | Disposition |
| --- | --- | --- |
| Safety-first versioned platform | Authority precedes effectful expansion; one recoverable path | **Selected**; larger initial contract work |
| Compatibility-first wrappers | Earlier API surface | Rejected as governing order: wrappers cannot supply approval or replay safety |
| Multi-host/platform-first | Earlier reach | Deferred: adds distributed failure modes before recovery is qualified |

Pure facade work may proceed after inventory approval; effectful and recovery cells stay
disabled until their authority prerequisites pass. Universal exactly-once external
execution is not promised: where a provider cannot dedupe or reconcile, an uncertain
operation stops for remediation.

## Ownership

| Owner | Executable responsibility | Must not absorb |
| --- | --- | --- |
| Perpetua Core | Graph mechanics, structural identity/lint, neutral cursor/checkpoint protocol, scheduler observations | Policy engines, approval authority, provider/storage SDK imports in the engine |
| Oramasys application | Concrete graph, policy binding, budgets, workflow effects/approvals, compatibility and provider composition | Telos/Phylax/Agate authority; traversal |
| Oramasys controller module | Claims, leases, claim idempotency, claim outbox; one writer | Workflow-effect keys/tables; gossip as authority |
| Telos | Endpoint identity, purpose authorization, DNS/rebinding, sockets, proxy/TLS/redirects | Generic approval; graph policy |
| Phylax | Principal/capability admission, artifact/provenance, safety policy, monitorability | Endpoint classification; workflow decisions |
| Agate | Measured fit/placement; forbidden/impossible hardware | Approval; queue mutation |
| Provider owner | Protocol, readiness/lifecycle, outcome/reconciliation adapter | A separate endpoint-security connector |
| Orama docs/v2 | Normative decisions, registry, supersession and evidence links | A runtime GraphSpec or second roadmap |
| PT `.agent` | Portable working/episodic/semantic memory, parity evidence | A v2 runtime service or hidden production authorization |

[Doc 68](../../68-orchestrator-controller-satellite.md) fixes the controller home at
`src/orama/orchestrator_controller/` in Oramasys; its standalone-repository row is a
placeholder. No new controller repository is created here.

Three idempotency domains stay distinct: controller **claim requests**, application
**logical workflow effects**, and **provider-native dedupe keys**. Link receipts between
them; never reuse a key or let one domain own another's tables. Approval and transport
stay separate: a human approval permits only a supported exception and cannot make
invalid authentication, impossible hardware, an unsafe endpoint or an uncontained SDK
acceptable.

## Per-contract status

| Contract | Section of the source draft | Status |
| --- | --- | --- |
| [Artifact admission](CONTRACT-ARTIFACT-ADMISSION.md) | §5 | Approved design contract |
| [Durable HITL and effects](CONTRACT-DURABLE-HITL-EFFECTS.md) | §6 | Approved design contract |
| [Foreign-provider transport](CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md) | §7 | Approved design contract |
| [Durable continuation](CONTRACT-DURABLE-CONTINUATION.md) | §8 | Approved design contract |
| [Compatibility and replacement](CONTRACT-COMPATIBILITY-REPLACEMENT.md) | §9 | Approved design contract |
| [Retained v1 concepts](REGISTER-RETAINED-V1-CONCEPTS.md) | §10 | Approved design register |
| [Multi-host stages](CONTRACT-MULTI-HOST-STAGES.md) | §11 | Approved design contract |

## Amendments proposed to existing records

All additive; archived files are never rewritten.

| Record | Qualification |
| --- | --- |
| Doc 57 §10 | R3 shipped per D-LG-6; reducers/joins are no longer deferred |
| Doc 57 §11 | Durability contract is [CONTRACT-DURABLE-CONTINUATION](CONTRACT-DURABLE-CONTINUATION.md) once ratified |
| Doc 57 §12 | Already qualified by D-LG-1/5; ownership here follows them |
| Docs 58/59 | Extend only where observer criticality or value isolation changes (T2) |
| Docs 60/62 | Extend only for actual new enforcement evidence |
| Docs 68/69 | Controller and continuation interfaces link here; they are not redefined |
| Errata | [E13](../errata-corrections-to-preserved-documents.md#e13--r4-draft-scope-labels-and-task-numbering) |

## Non-goals

No new git doctrine, no new controller repository, no universal provider exactly-once,
no implicit framework import interception, no automatic production graph optimization,
no BFT or quorum requirement, no compliance deadline. Each remains separately scoped.

## Decisions the reviewer must make

1. Dispatch/revocation linearization and unknown-outcome handling (HITL contract §3–§4).
2. Legacy snapshot versus durable continuation (continuation contract §1).
3. Versioned isolated facade packaging (compatibility contract §2).
4. The retained-v1 concept rubric (register).
5. The H0 → H1 → H2 sequence (multi-host contract).
6. Which T8/T9 follow-ons belong to the first release, and the first provider/API cohorts
   chosen from the T0 inventory.

Approval of the direction is not a runtime grant for tools, model calls or effects.
Publication and merge follow the operator's actual instructions.
