# Approved migration planning: reconciled reading guide

**Status:** current reconciliation authority for PR #351 — 2026-09-09.

This document reconciles the provenance-pinned Claude inputs, the two audit
tracks, PT `.agent` memory, canonical Orama `docs/v2`, and the current
`oramasys/*` implementations. Historical inputs remain evidence; they do not
override the current executable state or this reconciliation.

## Authority and preservation

Both legacy repositories remain independent v1 systems. New v2 implementation
belongs in `oramasys/*`. PR #351 is the explicitly authorized exception that
publishes migration/audit material under this legacy repository's
`docs/v2/references/` tree.

The following remain provenance-pinned historical inputs and MUST NOT be edited
merely to make their old proposals look current:

- `instruction-debt-audit-2026-09-09.md`;
- `instruction-debt-remediation-plan.md`;
- `oramasys-migration-execution-plan.md`;
- `portable-memory-sanitization-runbook.md`;
- the quoted handoff and `claude-input-provenance-2026-09-09.json`.

Use the errata and synthesized documents when those sources conflict with later
review findings, PT memory, canonical `docs/v2`, or live successor code.

## Current executable reconciliation

The earlier MiniGraph rehabilitation plan is no longer a future R0–R2 program.
Live `oramasys/perpetua-core` now implements the reconciled execution contract:

```text
MiniGraph
  mutable realization builder
        |
        | compile()
        v
CompiledGraph
  detached topology snapshot
        |
        v
_run(state)
  sole scheduler
        |
        v
GraphObservation(event, state, delta?)
        |
        +-------------------------+
        |                         |
        v                         v
   aobserve()                 GraphEvent
   rich/trusted                   |
                                  v
                               asteps()
                          sanitized/control-plane

ainvoke()
  drains aobserve()
  returns final PerpetuaState
```

Already implemented and regression-covered in Core:

- canonical Pydantic `PerpetuaState`;
- `merge(update=deepcopy(delta), deep=True)` generation/caller isolation;
- mutable `MiniGraph` plus detached `CompiledGraph` snapshots;
- returned-object awaitability for sync, async, callable-object, and
  sync-returned-awaitable nodes;
- strict `dict` node deltas; `None` is a visible contract error;
- `END` as sole normal termination;
- non-string, empty, and unknown routes rejected at the route boundary;
- conditional routing against the updated state;
- exact completed-step and `last_node` semantics;
- structural interrupts with optional payload;
- one scheduler with rich and sanitized observation projections;
- deterministic plugin fan-out with detached per-listener rich payloads;
- no provider, storage, exporter, or application-policy imports in the graph
  scheduler.

Therefore future planning MUST NOT reopen R0, R1, or R2 as unimplemented work.

## Remaining graph/runtime work

The open work begins after that baseline:

| Phase | Current state | Required next contract |
| --- | --- | --- |
| R0 characterization | complete | preserve tests |
| R1 kernel correction | complete | no redesign |
| R2 scheduler/observer seam | complete | preserve `_run -> aobserve -> asteps` |
| R3 reducers and joins | open | explicit reducer conflict policy and join semantics before generic parallel fan-in |
| R4 durable deterministic resume | partial | checkpoint lineage, graph/run/schema identity, execution cursor, replay/effect identity, idempotency/dedupe |
| R5 GraphSpec/lint | designed, implementation not established | versioned `GraphSpec`/`NodeSpec`/`EdgeSpec`, fail-closed validation, version selection and evaluation above Core |
| Optimizer/trace learning | research | only after versioned specs, traces and an independent evaluator exist |

The existing SQLite checkpointer is a useful successful-boundary persistence
primitive, not proof of deterministic resume. Do not add an isolated
`start_node` API before R4 defines checkpoint compatibility, cursor semantics,
and effect replay.

## Canonical ownership

The migration uses the authority model already captured in PT memory and Orama
architecture records:

| Owner | Canonical responsibility |
| --- | --- |
| `oramasys/perpetua-core` | irreducible execution mechanics and generic graph primitives |
| `oramasys/oramasys` | application composition; target owner for approved GraphSpec projection, routing policy, budgets/effects, control plane, APIs/UI |
| `oramasys/agate` | hardware capability, fit, affinity, readiness inputs for placement |
| `oramasys/telos` | endpoint-use semantics plus endpoint/network safe-transport enforcement |
| `oramasys/phylax` | generic runtime-check mechanism plus security/safety policy packs; domain semantics stay with their owners |
| `oramasys/anamnesis` | private runtime memory, provenance-preserving migration, retrieval and sanitized promotion |
| `oramasys/Claude-Desktop-LLM` | Ollama/LM Studio provider operation and provider-native readiness/health |
| `oramasys/alexandria` | reconciled v2 specifications, ADRs, standards, migration/release evidence |

`perpetua-core` MUST NOT regain provider, hardware, endpoint, application,
evaluation, budget, or policy authority merely because transitional helpers
remain there.

## Core policy/LLM/discovery strangler rule

Current Core `policy.py`, `llm.py`, and `discovery/` are transitional mixed
compatibility surfaces. Reconcile them by contract and caller, not by broad file
moves:

```text
Agate capability evidence
  -> provider readiness evidence
  -> Oramasys route policy
  -> ResolvedRoute
  -> Core execution adapter
```

A new caller supplies a resolved route; Core executes it without re-selecting a
provider or reinterpreting hardware policy. Existing public surfaces become
explicit compatibility facades only after parity is proven. Do not shadow
-dispatch paid/provider requests while comparing decisions.

## Current Oramasys application drift

The current `oramasys/oramasys/src/orama/graph/perpetua_graph.py` directly uses
Core hardware-policy/discovery/provider-selection helpers. Treat that as
transitional salvage code, not the future authority map. M6 must migrate the
composition to Agate capability evidence plus provider readiness and an
Oramasys-owned route decision before Core execution.

No live `GraphSpec` implementation was established in the inspected
`oramasys/oramasys` graph package. The ownership decision is settled; the
implementation/authority handoff is not complete until the successor artifact,
validation and consumer tests exist.

## Endpoint-policy convergence

Endpoint work follows the same strangler discipline:

- Telos owns endpoint-specific authorization, classification, DNS/connection
  safety, redirect/proxy/TLS destination enforcement and endpoint smoke checks;
- provider adapters own provider protocol semantics and provider-specific
  retries/auth construction;
- Phylax may execute generic admission/runtime checks but does not absorb
  Telos's endpoint meaning;
- Oramasys owns route/budget/application policy;
- Core executes an already-resolved route.

Private model endpoints, public fetches, telemetry/export destinations and mesh
peer endpoints remain distinct policy profiles. Do not collapse them into one
ambiguous allowlist.

## Review-remediation corrections incorporated here

The current execution documents also adopt the active PR #351 review findings:

1. all Track-B item counts must sum explicitly rather than hiding C2/C3 as
   uncounted overlaps;
2. memory snapshot commands fail closed when `PERPETUA_TOOLS_ROOT` is unset or
   does not contain `.agent`;
3. tracked docs use `$SUPERPOWERS_ROOT`, never a workstation-specific absolute
   plugin-cache path;
4. the release dependency check forbids legacy-runtime shell/subprocess use,
   not legitimate target-owned provider/platform subprocesses.

## Reading order

1. this reconciliation;
2. `integrated-v2-migration-plan-2026-09-09.md` — one executable M0–M9 program;
3. `consolidated-cross-reference-and-execution-order.md` — audit-item mapping;
4. `errata-corrections-to-preserved-documents.md` — corrections without
   altering pinned sources;
5. Part 1 / Part 2 and the Codex report for audit evidence and proposed text;
6. preserved Claude sources for provenance only.

## Governing execution rule

Do not estimate migration completion from file counts. For every capability,
record its source evidence, semantic owner, target contract, implementation
status, tests, consumer migration and authority-transfer evidence. A historical
plan saying something is open cannot override live tested successor code; a
live implementation also cannot silently transfer semantic ownership without
the corresponding contract and handoff.
