# Register — traceability, crosswalk and sources

**Status:** approved design register under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Statuses are as of drafting (2026-10-10) and must be refreshed at T0.

## Rev-2 crosswalk

The source draft says rev-2 Tasks 0–11 "map to T0–T11". They do **not** map by number.
Use this table; the mismatch is finding F1 in the [review record](REVIEW-RECORD.md).

| Rev-2 task ([plan](../remaining-capabilities/IMPLEMENTATION-PLAN-REV2-2026-10-10.md)) | R4 plan task | Note |
| --- | --- | --- |
| Task 0 — baseline and deferred inventory | T0 | Same intent, wider scope |
| Task 1 — artifact binding, Phylax admission | T1 | |
| Task 2 — observation delivery, cancellation | T2 | |
| Task 3 — approval and effect store | T3 | |
| Task 4 — foreign-provider transport | T4 | |
| Task 5 — R3 reducers, joins, loops | *(done)* | Merged as D-LG-6; only P0 pin promotion remains |
| Task 6 — R4 durable resume | T5 | |
| Task 7 — full upstream replacement | T6 | |
| Task 8 — Pydantic AI and other bridges | T7 | |
| Task 9 — evaluation, optimization, observability, memory | T8c–T8e | |
| Task 10 — controller, portal, identity, optional transport | T9a–T9d, T10 | |
| Task 11 — pinning, publication, PT closure | T11 | |
| *(new)* bounded R3 pin promotion | P0 | Prerequisite to M1 |
| *(new)* LangGraph.js / dynamic Send / nesting | T8a, T8b | Split out of replacement |
| *(new)* Anamnesis | T8d | Split out of Task 9 |

## Requirement-to-task map

| Requirement / retained decision | Source | Task / evidence gate |
| --- | --- | --- |
| Safety > compatibility > interoperability | Operator | All tasks; ADR arbitration |
| Separate structural/policy authority, complete registry | D-LG-1/5/6, R3 audit | T0/T1/T11 conformance and mutations |
| R3 settle-all, name order, local atomicity | D-LG-6, Core engine | T2/T5 delay permutations, effect crashes |
| Current resume starts at START | R3 audit, Core engine | T5 legacy-vs-durable tests |
| Durable HITL and effect reservations | Refusal/HITL contract, rev-2 plan | T3 contention, restart, revocation |
| Actual provider egress containment | ADR 62 | T4 real socket-path evidence |
| R4 frontier, lineage, fencing | Doc 57 §11, rev-2 plan | T5 process-kill recovery |
| Full replacement and import errors | Doc 57 §17, D-LG-2/3 | T6 versioned matrix |
| Pydantic AI strengths, deferred-tool safety | D-LG-4, rev-2 plan | T7 typed, offline, durable tests |
| Permitted v1 concepts, clean-room boundary | Docs 56/57/62/69, PT memory | T6 concept golden fixtures |
| Evaluation, memory, monitorability | Docs 20/41/55/56/60/67 | T8 independently reviewed slices |
| Controller, principal, envelope authority | Docs 61/68/69 | T9 claims, capability, fencing |
| Portal, MCP, Gateway, security adjacency | Docs 23/24/32/66/70 | T9 narrow acceptance evidence |
| Multi-host under the single-operator model | Docs 45/49/68 | T10 H1/H2 qualification |
| Both lockstep pairs, append-only memory | PT checklist and retrospective | T11 exact-head and production-pin checks |

## Status at drafting

| Item | State |
| --- | --- |
| R3 mechanics | Merged in Core and Oramasys; production Core pin promotion pending |
| Bounded adapters / offline Pydantic bridge | Historically tested; not re-run for this set |
| Durable HITL, R4 continuation, foreign transport, full replacement | Unimplemented, unqualified |
| T8–T10 | Tracked follow-ons with owners and gates, not discarded scope |

Verified for this set on 2026-10-10 against live sources: Orama `main` is the #390 merge
(`10c09ee`); Core `main` is the #9 merge (`4d217f6`); Oramasys `main` is the #25 merge
(`f4dbf33`); Oramasys production Core is still pinned at `04759a5` and its candidate file
at `34e4a8d`; PT #432 is open at `216efff`. Historical test totals (Core 255, candidate lane
333, production lane 307 with one gated skip) are **not** re-run here.

## Source coverage (bounded)

Read for this set: the operator's draft, the rev-2 plan (complete), the R3 audit, D-LG-1/3/4/5/6
indexes, docs 45/57/62/68, errata, and PT working memory cited by the draft. Docs 58/59 and
other adjacent documents referenced through the rev-2 plan are **T0 deep-review inputs**, not
a fresh full audit. T0 must close this gap before claiming the larger platform complete.

## Source index

Pinned Orama base `10c09ee21014ab6be184c3a711fdbccaff6f07af`; PT memory base
`216effff628f1c86baffc3cc17b75f9f36cb318a`.

| Source | Role |
| --- | --- |
| [Doc 57](../../57-minigraph-final-reconciliation.md) | One scheduler, doctrine, R4, compatibility targets |
| [D-LG-6](../loop-graph-compatibility-2026-10-09/ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md) | Exact R3 semantics and registry lifecycle |
| [R3 audit](../remaining-capabilities/R3-AUDIT-REPLAY-AND-COMPATIBILITY-2026-10-10.md) | Resume limits, known gaps |
| [ADR 62](../../62-telos-phylax-authority-gate0-adr.md) | Telos endpoint authority; clean-room boundary |
| [Doc 60](../../60-phylax-monitorability-design-spec.md) | Advisory v1 versus enforced v2; Observed evidence |
| [Doc 55](../../55-oramasys-agent-observability-contract-adr.md) | Observation vocabulary, privacy projections |
| [Doc 68](../../68-orchestrator-controller-satellite.md) | Controller module home, one writer |
| [Doc 69](../../69-agent-envelope-standard.md) | Neutral header, author/actor lineage |
| [Doc 70](../../70-portal-knowledge-hitl-development-ladder.md) | Portal as-built, rollback, public reads |
| [Doc 45](../../45-single-operator-lan-threat-model-descope.md) | Single-operator topology |
| [Doc 56](../../56-anamnesis-runtime-memory-migration.md) | Memory authority, human push boundary |
| [Doc 66](../../66-gate4-and-dedicated-dialer-combined-scope.md) | Historical Gate-4 scope, qualified by ADR 62 |

Upstream orientation (rolling documentation, not evidence for pinned versions):
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts),
[Pydantic AI deferred tools](https://ai.pydantic.dev/deferred-tools/). T0 pins
source-version contracts; no production guarantee is inferred from documentation alone.
