# v2 Migration Planning — Consolidated Cross-Reference and Execution Order

**Status:** reconciled cross-reference for PR #351.  
**Current authority:**
[the harmonization guide](migration-harmonization-2026-09-09.md) and
[the integrated plan](integrated-v2-migration-plan-2026-09-09.md).

This document maps the two audit tracks onto one execution order. It does not
turn historical source reports into runtime authority.

## 1. Source layers

### Track A — provenance-pinned Claude F/R material

- `instruction-debt-audit-2026-09-09.md` — F1–F9 evidence;
- `instruction-debt-remediation-plan.md` — R1–R7 proposals;
- `oramasys-migration-execution-plan.md` — original six-wave migration plan;
- `portable-memory-sanitization-runbook.md` — detailed migration-copy process.

These files remain byte-preserved. Corrections live in
`errata-corrections-to-preserved-documents.md`.

### Track B — Codex/second-audit material

- `codex-full-instruction-debt-audit-2026-09-09.md`;
- `instruction-audit-and-migration-plan-part-1-findings-and-edits.md`;
- `instruction-audit-and-migration-plan-part-2-execution-program.md`.

These are audit/planning evidence. Their future-work statements yield to live
successor verification and the integrated plan.

## 2. Track-B accounting

The earlier summary failed to account explicitly for C2 and C3. The complete
26-item disposition is:

| Classification | Count | Items / treatment |
| --- | ---: | --- |
| direct or near-direct duplicates | 20 | carry one canonical wording; retain source provenance |
| folded overlaps requiring standalone carry-forward | 2 | C2 shared-permission policy; C3 hook configuration |
| unique/cross-track actionable items | 3 | A4 regime boundary; C4 argument/effect-scoped shell admission; C5 Oramasys test/setup separation |
| unresolved sub-item | 1 | B2 AFRP/CIDF discovery-shape question; generator must tolerate the settled source shape rather than silently collapsing it |
| **Total** | **26** | every Track-B item accounted for |

This replaces the earlier `20 + 4` summary that accounted for only 24 items.

## 3. High-confidence cross-track convergence

| Finding | Converged rule |
| --- | --- |
| command-prefix allowlists | command names do not prove read-only effects; validate arguments/effects and prefer structured read APIs |
| permission/enforcement claims | static policy text is not runtime enforcement; adapters must be registered and negative-tested in the actual call path |
| legacy Gate-4/PT work | mine intent/tests into v2 owners; legacy PR state is evidence, not a migration dependency |
| skill wrapper synchronization | loading/discovery is read-only; fetch/pull/install/import are separate operations |
| endpoint policy | endpoint authorization/safe transport is reusable and explicit; provider clients consume it rather than redefining it |
| MiniGraph architecture | Core owns realized execution; application/evaluation/policy semantics remain above Core |

## 4. Live-successor reconciliation supersedes the old access gap

The original Track-B prose said the `oramasys/*` organization could not be
independently rechecked. That statement is historical. The current reconciliation
successfully inspected live successor repositories, including:

- `oramasys/perpetua-core` graph engine, state merge, observer fan-out,
  checkpointer, parallel helper and regression tests;
- `oramasys/oramasys` current graph composition.

This live verification establishes the current MiniGraph baseline described in
the harmonization guide. It is **not** an exhaustive re-audit of every file in
Agate, Telos, Phylax, Alexandria, Anamnesis or Claude-Desktop-LLM.

## 5. MiniGraph disposition after live verification

| Earlier planned work | Current disposition |
| --- | --- |
| R0 characterization tests | complete; preserve |
| R1 strict kernel rehabilitation | complete; preserve |
| R2 scheduler/streaming seam | complete, but final form is `_run -> GraphObservation -> aobserve/asteps`, not `asteps` as scheduler |
| unknown-route rejection | present in live Core and covered by regression |
| per-listener observation isolation | present in live Core and covered by regression |
| R3 reducer/join contract | open |
| R4 durable deterministic resume | partial; persistence primitive exists, full lineage/cursor/effect contract does not |
| R5 GraphSpec/lint | target ownership decided; successor implementation not established |

Do not reopen R0–R2 merely because preserved planning text predates their
integration.

## 6. Ownership mapping

```text
oramasys/perpetua-core
  realized execution only

oramasys/agate
  hardware capability / fit / affinity

provider owner
  provider operation / readiness / protocol

oramasys/telos
  endpoint-use meaning + endpoint/network safe transport

oramasys/phylax
  generic runtime-check substrate + security/safety packs

oramasys/oramasys
  GraphSpec target projection + route/budget/effect/application policy

oramasys/anamnesis
  private runtime memory and migration

oramasys/alexandria
  v2 documentation authority after explicit handoff
```

The current Oramasys `perpetua_graph.py` directly consumes Core hardware and
provider selection helpers. Treat that path as transitional salvage to migrate,
not as evidence that those semantic owners belong permanently in Core.

## 7. Audit-item mapping to the authoritative M0–M9 plan

| Wave | Items / work |
| --- | --- |
| M0 | A4 regime/source-freeze boundary; pin current successor evidence and access |
| M1 | capability/instruction/contract/document ledgers; resolve B2 discovery shape without blocking unrelated work |
| M2 | A1–A3 authority docs, B1–B4 skill/memory-loading discipline, C5 Oramasys test/setup separation, concise owner guides |
| M3 | C1 security-admission contract plus route/endpoint/hardware/provider/memory/event contracts |
| M4 | C1 real Phylax adapters, C4 argument/effect-scoped admission, Agate/Telos/Phylax/Anamnesis/provider implementation |
| M5 | preserve Core R0–R2; implement accepted R3/R4; strangle Core policy/LLM/discovery through typed delegation |
| M6 | GraphSpec/application composition, route resolution, gateway/control-plane, budgets/effects, APIs/UI; migrate transitional `perpetua_graph.py` ownership |
| M7 | C2/C3 governance/hook policy, E-series skill/plugin migration, memory sanitation/import, Alexandria handoff |
| M8 | release assembly and dependency-boundary proof |
| M9 | concrete approved rollout/recovery |

C5 belongs to M2/Oramasys build foundations, **not** M5/Core.

## 8. Explicit prerequisite chains

1. M0 regime/source evidence precedes mutation-bearing migration work.
2. M1 defines the capability denominator; no completion percentage precedes it.
3. Shared M3 contracts precede M4/M6 consumers that depend on them.
4. Core R0–R2 are an input baseline, not a prerequisite implementation project.
5. R3 must define reducers/joins before generic parallel fan-in is expanded.
6. R4 must define lineage/cursor/effect semantics before a resume execution API
   is added.
7. GraphSpec implementation belongs above Core and must pass fail-closed lint
   before realization.
8. Anamnesis access gates private memory import, not unrelated documentation or
   contract work.
9. Endpoint/DNS remediation remains independently reviewable from MiniGraph
   correctness.
10. Core policy/LLM/discovery retirement follows a strangler vertical slice and
    consumer parity; it is not a broad file deletion.

## 9. Release dependency-boundary rule

M8 rejects:

- imports or dynamic loads of legacy v1 runtime packages;
- legacy installation URLs;
- implicit sibling-checkout lookup/fallback;
- shell/subprocess calls whose purpose is to invoke legacy v1 scripts,
  binaries, memory writers or policy/provider authorities.

It does **not** ban all subprocesses. Target-owned provider/platform/tool
subprocesses are permitted when explicitly modeled through approved adapters,
validated for their arguments/effects/lifecycle, and independent of v1.

## 10. Remaining open decisions

- the exact first consumer for the Core policy/LLM/discovery strangler slice;
- the concrete `ResolvedRoute` schema after M3 contract review;
- R3 reducer/join vocabulary and conflict semantics;
- R4 checkpoint cursor/effect/replay contract;
- the successor GraphSpec package/module location inside the approved Oramasys
  application authority;
- Anamnesis access/provisioning;
- any specialist contract gap found by the M1 inventory.

Everything else in the audit set is either preserved historical evidence,
reconciled into the integrated plan, or already implemented and therefore not
to be restarted.
