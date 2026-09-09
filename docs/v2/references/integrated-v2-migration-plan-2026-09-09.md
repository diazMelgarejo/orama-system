# Integrated v2 migration implementation and execution plan

**Date:** 2026-09-09  
**Status:** current executable planning baseline for PR #351.

Read [the reconciled reading guide](migration-harmonization-2026-09-09.md)
first. Historical audit/source documents are evidence; this plan is the single
M0–M9 execution program.

## 1. Migration invariants

- v1 remains independently usable and is never a runtime/build/test fallback for
  v2;
- implementation belongs in `oramasys/*`;
- unbundle by stable capability and semantic authority, not by copying file
  trees;
- fail closed at policy/admission/route boundaries;
- one decision has one semantic owner even when multiple adapters consume it;
- Core never imports upward into application or specialist policy owners;
- compare decisions where useful, but never shadow-dispatch paid or
  security-sensitive provider requests;
- no completion percentage is assigned before the capability ledger defines
  the denominator.

## 2. Ownership and interfaces

| Repository | Owns | Must not silently absorb |
| --- | --- | --- |
| `oramasys/perpetua-core` | `PerpetuaState`, MiniGraph/CompiledGraph execution, structural events/observations, generic graph plugins and dependency-minimal execution contracts | GraphSpec policy, hardware selection, provider operations, endpoint policy, budgets, private memory |
| `oramasys/oramasys` | application composition, target GraphSpec projection, route/runtime policy, control plane, APIs/UI, budgets/accounting/effects, integration | duplicate copies of specialist semantics |
| `oramasys/agate` | hardware inventory/capability, fit, affinity and placement evidence | provider serving lifecycle or endpoint authorization |
| `oramasys/telos` | endpoint-use authorization plus endpoint/network safe-transport policy and enforcement | provider protocol semantics or application routing |
| `oramasys/phylax` | generic runtime-check engine, admission, provenance/redaction, security/safety policy packs and monitorability | endpoint semantic ownership or application workflow state |
| `oramasys/anamnesis` | private runtime memory, sanitized import, retrieval, provenance and controlled promotion | raw v1 memory or Core fallback storage |
| `oramasys/Claude-Desktop-LLM` | provider-native Ollama/LM Studio operation, health/readiness and provider lifecycle | hardware placement or global orchestration |
| `oramasys/alexandria` | reconciled v2 specifications, ADRs, standards, migration/release evidence | runtime implementation or bulk active copies of v1 archives |

Phylax owns the generic runtime-check mechanism; non-security domain policies
retain their semantic owners. Telos remains independently fail-closed for basic
endpoint safety.

## 3. Successor baseline already implemented

M5 does **not** begin from an unreconciled MiniGraph. Current
`oramasys/perpetua-core` already provides the canonical R0–R2 baseline:

```text
MiniGraph.compile()
  -> detached CompiledGraph

CompiledGraph._run()
  -> sole scheduler
  -> GraphObservation
       -> aobserve() rich/trusted
       -> GraphEvent -> asteps() sanitized

ainvoke()
  -> drains the same scheduler/observation stream
```

Preserve these tested invariants:

- canonical `PerpetuaState` with two-layer state/delta isolation;
- returned-value awaitability;
- strict `dict` node deltas;
- END-only normal termination;
- non-string, empty and unknown route rejection at resolution;
- post-merge conditional routing;
- exact max-step diagnostics;
- structural interrupts with optional payload;
- detached compiled topology;
- generic plugin fan-out with sync/async callback settlement;
- per-listener rich-payload isolation;
- no traversal reimplementation in plugins/adapters.

Do not create a duplicate plugin namespace or reintroduce the removed no-op
`interrupt_handler` API.

## 4. Remaining Core graph work

### R3 — reducers and explicit joins

The current parallel helper's ordered last-writer-wins behavior is not a generic
parallel graph contract. Before richer fan-in ships, define explicit field
reducers and join semantics, for example:

```text
Reducer: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
Join:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Branch completion timing MUST NOT silently determine state semantics.

### R4 — durable deterministic resume

The SQLite checkpointer is a successful-boundary persistence primitive, not a
complete resume contract. R4 must define at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical node/step
execution cursor
replay/effect policy
effect identity
idempotency/deduplication or compensation
```

Choose any narrow resume execution API only after those semantics are frozen.
Restoring graph state cannot undo an external side effect.

### R5 — GraphSpec and validation

Target authority is the Oramasys/application specification layer, not Core.
Implement versioned `GraphSpec`, `NodeSpec`, `EdgeSpec`, lint, version
selection and evaluation with fail-closed validation before realization.
Persistent/immutable structural sharing belongs here rather than in the mutable
MiniGraph builder.

## 5. Core policy/LLM/discovery strangler migration

The remaining `perpetua_core/policy.py`, `llm.py` and `discovery/` surfaces are
mixed compatibility/salvage layers. Do not move them wholesale.

Target flow:

```text
Agate CapabilityEvidence
        |
        v
ProviderReadiness
        |
        v
Oramasys route/effect/budget policy
        |
        v
ResolvedRoute
        |
        v
Core execution adapter
```

Minimum contracts:

| Contract | Producer | Consumer | Required meaning |
| --- | --- | --- | --- |
| `CapabilityEvidence` | Agate | Oramasys route policy | hardware/model fit and provenance |
| `ProviderReadiness` | provider owner | Oramasys route policy | provider/model endpoint availability and freshness |
| `ResolvedRoute` | Oramasys | Core execution | selected provider/model plus decision evidence; no re-selection in Core |
| provider transport | provider owner | executing node/adapter | request/response/cancel semantics, not route selection |

Retain old Core APIs only as explicit compatibility facades while consumers are
migrated and parity-tested. Retirement requires proof that no production caller
still depends on an independent old decision path.

## 6. Endpoint-policy strangler migration

Endpoint-policy work stays independently reviewable from MiniGraph correctness.

Telos owns endpoint-specific concerns including:

- destination classification and endpoint-use authorization;
- SSRF/metadata protections;
- DNS pinning/rebinding defenses;
- redirect/proxy/TLS destination rules;
- endpoint/network egress enforcement and operational smoke verification.

Provider adapters own protocol semantics, parsing, provider-specific retries,
rate limits, model listing and authentication construction. Phylax owns generic
security/safety admission and can execute Telos/Agate/Oramasys checks through a
shared runtime-check substrate without taking their semantic ownership.

Keep distinct profiles for private model endpoints, public fetches,
telemetry/export destinations and mesh peers.

## 7. Required coverage ledger

Every in-scope capability receives an explicit row containing:

```text
source_repo
source_commit
source_path_or_symbol
capability/observable contract
source tests
semantic owner
target contract/path
disposition
dependencies
acceptance cases
target evidence
status
decision reference
reviewer
```

Allowed dispositions include extract/adapt, reimplement, consume specialist,
compatibility facade, historical-only and accepted exclusion. No row disappears
because a file move or scaffold makes the migration look complete.

## 8. Execution waves

| Wave | Work | Exit evidence |
| --- | --- | --- |
| M0 baseline | pin source/target revisions, current PRs/access, source-freeze and regime authority | evidence manifest and unresolved-decision ledger |
| M1 coverage | build capability/instruction/contract/document lineage ledgers | no unexplained in-scope omission |
| M2 foundations | successor owner guides, reproducible setup/build/test commands, versions, CI and adapter discovery | targets build/test without v1; setup does not hide installation in tests |
| M3 contracts | freeze execution, route, endpoint, admission, hardware, provider, memory, event/accounting contracts | one owner per contract; malformed/unknown/version failures explicit |
| M4 specialists | implement/verify Agate, Telos, Phylax, Anamnesis and provider slices | real call-path enforcement and negative cases, not schema-only evidence |
| M5 Core | preserve R0–R2; implement R3/R4 as accepted; strangle policy/LLM/discovery through typed delegation | Core contains no independent application/hardware/provider/endpoint decision engine |
| M6 Oramasys | GraphSpec, route/control-plane composition, budgets/effects, gateway/API/UI and specialist integration | full v2 workflow with real adapters and fail-closed effects |
| M7 knowledge | sanitize/import memory, regenerate derived indexes, migrate skills/docs with lineage | provenance preserved; no unresolved leak; no automatic v1 writeback |
| M8 assembly | build/test coherent v2 release with v1 repos absent | tested version/digest manifest and supported-environment evidence |
| M9 release | reviewed publication/deployment/data-migration packet and rollback | authorized rollout matches manifest and recovery is proven |

M0 precedes M1. M2/M3 enable M4–M6. Documentation classification can proceed
before memory import; Anamnesis access gates memory import only.

## 9. M2 governance and instruction cleanup

- keep root successor `AGENTS.md` files concise and owner-specific;
- skill discovery/loading is read-only and performs no fetch/pull/install or
  memory import;
- use `$SUPERPOWERS_ROOT` or another documented neutral locator in tracked
  reports, never workstation-specific cache paths;
- test commands do not install dependencies as hidden side effects;
- permission/admission rules classify operations by validated args/effects,
  not command-family prefixes;
- expected red tests are evidence to diagnose, not automatic stop conditions;
- UI correctness uses both programmatic and rendered evidence when appearance
  is part of the contract.

## 10. M4 specialist acceptance

### Agate

Test forbidden placement, unavailable/stale capability evidence, model fit and
supported fallback. Do not turn Agate into provider-runtime health.

### Telos

Test allow/deny/unknown purpose, policy version/expiry/revocation, DNS pinning,
redirect/proxy/TLS rules, and fail-closed endpoint evidence.

### Phylax

Test that the actual invocation path registers admission adapters and rejects
unknown/malformed/missing-evidence operations before effects. A verifier file
that is never invoked is not enforcement.

### Anamnesis

Test private defaults, namespace isolation, lossless/repeat-safe migration,
sanitation, provenance, retrieval and HITL-controlled publication.

### Provider owner

Test readiness freshness, timeout, cancellation, unavailable provider,
duplicate-start prevention and repeat-run idempotency.

## 11. M6 Oramasys composition

The current `src/orama/graph/perpetua_graph.py` directly calls Core
hardware-policy/discovery/provider-selection helpers. Treat it as transitional
salvage. Replace the semantic ownership in vertical slices:

1. obtain Agate capability evidence;
2. obtain provider readiness;
3. authorize endpoint use through Telos and required admission through Phylax;
4. resolve route/budget/effect policy in Oramasys;
5. pass one `ResolvedRoute` to Core execution;
6. emit/persist evidence through the approved observation/monitorability
   boundaries.

Do not connect v1 PT as a runtime dependency. Mine legacy dialer/endpoint tests
as evidence and port the accepted behavior to the selected v2 owner.

## 12. M7 memory procedure

1. pin PT source revision and snapshot `.agent` outside git;
2. require `PERPETUA_TOOLS_ROOT` and verify its `.agent` directory before copy;
3. inventory IDs, dates, status, provenance, supersession and references;
4. sanitize the migration copy with generic guards plus private registries;
5. regenerate embeddings/indexes/materialized views from sanitized source;
6. verify identity/reference integrity and representative retrieval, not row
   count alone;
7. repeat to prove idempotency;
8. import only through the reviewed Anamnesis contract after provisioning;
9. keep promotion/push human-gated unless explicitly configured otherwise.

## 13. M8 dependency-boundary check

Reject:

- runtime imports from legacy v1 packages;
- installation URLs or dynamic loads that make a v1 checkout a dependency;
- implicit sibling-checkout discovery/fallback;
- runtime shell/subprocess calls whose purpose is to invoke legacy v1 scripts,
  binaries, memory writers, policy authorities or provider paths.

Permit target-owned provider/platform subprocesses only when they are explicit
adapters with validated arguments/effects, documented lifecycle/cancellation,
and no legacy fallback. Examples can include approved local provider process
management or tool execution. Historical citations and sanitized fixture
provenance are not runtime dependencies.

## 14. Release completion

Migration is complete only when:

- the capability/authority ledgers contain no unexplained omissions;
- selected workflows run solely on v2 artifacts;
- Core R0–R2 remain intact and any accepted R3/R4 work is verified;
- GraphSpec/application policy executes above Core;
- specialist semantic owners are used in the real call path;
- endpoint/admission denials produce zero unauthorized effect;
- memory/document provenance survives migration;
- the release candidate is tested without v1 repos/services/writers present;
- package versions and artifact digests form one reviewed manifest;
- remaining exclusions are explicit decisions, not unfinished work labelled
  complete.

## 15. Execution ledger at this reconciliation

| Item | Status | Next evidence |
| --- | --- | --- |
| provenance-pinned Claude inputs | preserved | keep hashes stable |
| PT `.agent` MiniGraph/unbundling decisions | reconciled | maintain lineage in successor ADRs |
| Core MiniGraph R0/R1/R2 | implemented in live successor | preserve exact-head regression coverage |
| Core unknown-route and plugin-payload corrections | present in live successor | repair stale legacy docs that still call them unmerged |
| R3 reducers/joins | open | typed reducer/join spec and tests |
| R4 deterministic resume | partial | lineage/cursor/effect contract plus implementation |
| GraphSpec target ownership | decided | implement/version/validate in successor application authority |
| Core policy/LLM/discovery ownership | transitional | inventory and first `ResolvedRoute` vertical slice |
| Oramasys graph composition | transitional | remove direct semantic dependence on Core hardware/provider selection |
| endpoint/Telos/Phylax split | decided | continue contract/implementation conformance and real call-path wiring |
| Anamnesis | access/provisioning still a gate for import | verify/provision target |
| release completion | not established | close capability ledger and M8/M9 gates |

No global completion percentage is assigned.
