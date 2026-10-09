# Oramasys Remaining Capabilities Implementation Plan (Revision 2)

> **For agentic workers:** After human review, use `superpowers:executing-plans` to implement
> approved workstreams task-by-task. Use `superpowers:subagent-driven-development` only if
> explicitly selected. Checkboxes track work; an unchecked item is not a shipped capability.

**Goal:** Complete the remaining upstream compatibility, durable human-in-the-loop enforcement,
production foreign-provider transport, and associated graph/runtime safeguards without compromising
ownership or making unsupported parity claims.

**Architecture:** Keep one Core scheduler and neutral structural mechanics. Oramasys supplies
compatibility facades, graph policy and orchestration; Phylax admits work, Telos controls endpoint
transport, and Agate determines hardware feasibility. Durable approval, checkpoint and effect
records cooperate through explicit interfaces rather than a second execution engine.

**Tech stack:** Existing Python Core/Oramasys packages, typed contracts, transactional persistence,
pytest, isolated pinned real-framework oracle environments; JavaScript/TypeScript compatibility is a
separately scoped workstream.

**Spec:** Orama `docs/v2/57-minigraph-final-reconciliation.md`, active D-LG-1/D-LG-4/D-LG-5
references, revision-4 reconciliation, and adjacent authority/security/durability designs listed in
§12.

**Status:** Revision 2, 2026-10-10 Asia/Manila (2026-10-09 UTC). Supersedes the earlier draft; see §13
for the decision ledger and §14 for the change log. Human-review draft. This document proposes implementation
decisions; it neither ratifies unapproved ADRs nor authorizes publication, merge, production egress
or execution. It is a master plan with independently reviewable subsystem slices, not a claim that
every upstream API is already implementable.

## 1. Scope, baseline and governing constraints

The reviewed reconciliation records bounded structural/policy lint, import checks, tiered
unsupported-API diagnostics, adversarial batch-order tests and an offline Pydantic AI Phase-1
bridge. It explicitly leaves full replacement, R3 reducers/joins, R4 durable resume, durable
approval, provider deduplication and production foreign egress open. These are the starting
distinctions, not newly asserted test results.

**Baseline (verified 2026-10-10):** Core #8 is merged as `04759a5`. Oramasys #23 is merged as
`fe8d39a`, with the production and candidate Core pin both at `04759a5` and CI green on Python 3.11
and 3.12. Orama #388 and #389 and PT #430 and #431 are merged. Earlier suite counts remain
historical evidence; Task 0 still resolves current immutable heads and reruns affected checks before
any new claim.

### Global constraints

- Core must not import application policy, providers, storage adapters or upper-layer runtime code
  into its engine.
- Native execution remains under `CompiledGraph._run()`. A LangGraph export running under the
  upstream scheduler is an interoperability oracle, not proof of native replacement parity.
- v1 Orama and Perpetua-Tools remain independent of v2 runtime dependencies.
- No default or published-extra LangChain, LangGraph or Pydantic AI dependency. Real-framework
  oracles run in isolated, nonpublished test environments; optional interop imports are explicit,
  lazy and allowlisted.
- D-LG-1 separate policy binding, D-LG-4 Phase 1 and the D-LG-5 amendment have recorded approval.
  D-LG-2/3 broad replacement and new contracts below still require review.
- Human approval never makes invalid authentication, impossible hardware or non-overridable security
  invariants acceptable. Revalidate every applicable gate immediately before the effect.
- Admit feasible permitted calls automatically; record refusals. A supported exception may become a
  narrowly scoped durable approval request, never an automatic approval.
- Treat external success, failure and unknown outcome separately. An audit ledger alone is not an
  idempotency mechanism.
- Retain the single-operator LAN threat model unless explicitly revised; do not import
  multi-principal quorum requirements or speculative conformity deadlines into shipping gates.

### Review focus

1. Installed upstream packages, cached imports and unsupported versions must not silently win over
   an activated replacement namespace — Tasks 0/7.
2. Crash after provider acceptance but before local commit must not cause a duplicate write — Tasks
   3/4/6.
3. Approval revocation between admission and dispatch must block dispatch or produce an explicit
   already-in-flight outcome — Tasks 3/4.
4. Fast later branches, cancellation and partial streams must not change deterministic merge
   semantics or fabricate final success — Tasks 2/5/7.
5. Policy-compatible topology with changed executable code must not reuse stale admission or resume
   authority — Tasks 1/6.

## 2. Ownership and file map

Paths below are relative to the named repository. Existing seams are preserved; proposed new
filenames are decisions for review, not assertions that those files exist. Task 0 maps them to the
current head before implementation and records any justified relocation.

| Owner | Existing seam / proposed files | Responsibility |
| --- | --- | --- |
| `oramasys/perpetua-core` | Existing `src/perpetua_core/graph/{engine,spec,lint}.py`; plugins `{observer,parallel,checkpointer}.py` | Neutral mechanics, the one structural GraphSpec schema (including reducer/join declaration fields once R3 ships), `graph_id`, observations, checkpoint protocol |
| Core | Proposed `src/tests/graph/test_reducers_joins.py`, `test_durable_resume.py`, `plugins/test_plugin_delivery.py` | Determinism, recovery and plugin reliability contracts |
| `oramasys/oramasys` | Existing `src/orama/graph/perpetua_graph.py`; proposed `graph/{policy_binding,admission,effects,approvals,recovery}.py` | Application graph definitions (concrete reducer/join declarations), restrict-only `GraphPolicy`, executable artifact binding, durable effects and approvals, ownership-registry conformance tests |
| Oramasys | Proposed `src/orama/compat/{manifest,diagnostics,activation}.py` and framework-family subpackages | Versioned facade and explicit replacement activation, not Core scheduling |
| Oramasys | Existing `src/orama/providers/{contracts,ledger,outbound_ledger}.py`, `gateway/{contracts,dialer}.py`; proposed `providers/foreign_transport.py` | Provider lifecycle/transport adapters and durable outcome integration |
| Oramasys | Proposed `src/tests/test_{graph_admission,durable_approvals,effect_recovery,foreign_transport,compat_activation}.py` | Integration and adversarial gates |
| Telos / Phylax / Agate | Extend their canonical interfaces in their actual owning repositories, discovered at Task 0 | Endpoint authority / admission-monitorability / hardware feasibility; no copied policy engine |
| `diazMelgarejo/orama-system` | `docs/v2/references/remaining-capabilities/` proposed index and subsystem ADRs; amendments to canonical docs | Normative decisions, the machine-readable ownership registry, evidence links and supersession; no runtime schema or code; preserve history |
| `diazMelgarejo/Perpetua-Tools` | Existing `.agent/memory/working/` and `.agent/memory/semantic/`; existing coordination docs | Working status, durable lessons, pin/lockstep evidence; no v2 runtime dependency |

**Single authority (D-LG-1 as amended by D-LG-5).** Exactly one GraphSpec exists in code, in Core.
Reducer and join declarations are fields of that structural GraphSpec and are part of `graph_id`,
because they change what a graph computes. Oramasys authors the concrete declarations for its
graphs. `GraphPolicy` lives beside its application graph as a separately versioned file and can only
restrict: it may require declarations, forbid choices such as `LAST` on audited fields, set a
minimum join failure policy, or set budgets. It may not add, remove or change a declaration. The
application summary links to the policy and digest and is not a second authoritative copy. Orama
`docs/v2` records the decision and the machine-readable [ownership
registry](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/loop-graph-compatibility-2026-10-09/ownership-registry.json);
Oramasys keeps a digest-pinned snapshot and conformance tests
(`src/tests/test_ownership_registry.py`). Core's schema evolves only through a deliberate mechanics
ADR.

## 3. Delivery order and exit gates

| Milestone | Tasks | Exit gate |
| --- | --- | --- |
| M0 — Evidence and decisions | 0 | Immutable baseline, complete deferred-item inventory and version/surface scope approved |
| M1 — Reliable authority seams | 1, 2 | Artifact admission and observation delivery cannot bypass or mutate authority |
| M2 — Durable approval/effect spine | 3 | Restart-safe pending/refused/approved/reserved/outcome records; concurrency and crash tests pass |
| M3 — Transport and graph recovery | 4, 5, 6 | Real egress controlled; deterministic fan-in; recoverable checkpoints and unknown effects |
| M4 — Replacement and bridge expansion | 7, 8 | Declared facade cells pass unchanged upstream cases; production bridge uses M2/M3 gates |
| M5 — Adjacent application capabilities | 9, 10 | Each selected subsystem passes its canonical acceptance criteria, independently |
| M6 — Qualification and durable closure | 11 | Fresh production-pin tests, release scope ledger, docs/memory and coordinated pin evidence |

Tasks 4 and 5 can be developed independently after their inputs are stable. Task 6 depends on
1/2/3/5. Task 7 can build a pure API surface early, but effectful/recovery cells cannot be enabled
until 3/4/6 pass. Task 8's production mode depends on 1/3/4/6. No milestone date is promised before
discovery and measured capacity.

## 4. Shared proposed interfaces

These signatures are proposed contract boundaries; freeze their types in the owning subsystem ADR
before code. Persisted records require versioned schemas and canonical digest encodings.

```python
# Oramasys-owned records; Core consumes only neutral mechanics/protocols.
ArtifactRef(graph_id, implementation_digest, state_schema_version,
            policy_digest, registry_digest, provider_contract_digest)
OperationRef(durable_run_id, logical_operation_id, request_digest, effect_kind)

admit(artifact: ArtifactRef, context: AdmissionContext) -> AdmissionDecision
record_refusal(operation: OperationRef, refusal: Refusal) -> RefusalId
decide(refusal_id: RefusalId, decision: ApprovalDecision) -> GrantId
reserve(operation: OperationRef, grant_id: GrantId | None) -> Reservation
dispatch(operation: OperationRef, reservation: Reservation,
         request: ProviderRequest) -> ProviderOutcome
reconcile(operation: OperationRef) -> ProviderOutcome
resume(checkpoint_id: CheckpointId, context: ResumeContext) -> ResumeDecision
explain(target: str, *, upstream_version: str) -> CompatibilityDiagnostic
```

`AdmissionDecision` and `ResumeDecision` are discriminated allow/refuse/pending results.
`ProviderOutcome` distinguishes confirmed success, confirmed nonapplication/failure and unknown.
`ApprovalDecision` includes authenticated principal, exact request and policy bindings, permitted
exception identifiers, bounded scope, UTC issuance/expiry, use limit and provenance. The operation
key is stable across retries; attempt IDs are separate. Changed request digest under the same
operation key is a conflict, not a retry.

## 5. Tasks 0–4: authority, durable HITL and production transport

### Task 0 — Freeze baseline and enumerate every deferred surface

**Deliverable:** Approved manifest at proposed
`docs/v2/references/remaining-capabilities/SCOPE-MANIFEST.md`, plus machine-readable
`compatibility-matrix.json` in Oramasys.

- [ ] Resolve current heads of the repositories. Core #8, Oramasys #23, Orama #388/#389 and PT
      #430/#431 are merged (see §1); distinguish them from open, superseded and local-only changes,
      including the D-LG-5 pull requests in §15. Compare actual diffs rather than inherited
      merge-order prose.
- [ ] Read active D-LG-1–5, docs 57–59 and adjacent canonical references. Give every deferred
      requirement an ID, source section, owner, dependency and disposition: required now, later
      milestone, explicit non-goal or needs decision. No item disappears under a generic “future.”
- [ ] Build the upstream inventory from pinned source/docs: public modules, symbols, signatures,
      configuration, sync/async behaviors, stream/error contracts, serialization and lifecycle.
      Separate LangChain, LangGraph and Pydantic AI; include older version targets only when named
      and funded.
- [ ] Give each API/version cell a status: implemented, policy-refused, technically unsupported or
      not yet implemented. Record expected diagnostics and tests. Refusals are not counted as
      semantic implementation.
- [ ] Create Oramasys `scripts/compat/run_matrix.py`: consume the manifest, require each declared
      test cell to execute in its named environment, and emit machine-readable results with
      environment/version/artifact identity. A missing required cell exits nonzero; its fixture
      tests must prove missing and skipped cells cannot yield a pass.
- [ ] Select supported Python/platform/version ranges and separate LangGraph.js/oramaclaw scope. Do
      not infer JavaScript parity from Python tests.
- [ ] Run fresh framework-free bootstrap and exact-head suites with required Agate/Telos fixtures.
      Required oracle cells fail when dependencies are missing; never use `importorskip` to hide
      them.
- [ ] Review the manifest and approve subsystem ADRs before implementation. Commit the baseline and
      proposed test commands with their exact environment.

### Task 1 — Bind policy to executable artifacts and enforce Phylax admission

**Files:** Oramasys `graph/policy_binding.py`, `graph/admission.py`; Core structural spec/lint only
where mechanics demand it. **Produces:** `ArtifactRef`, `admit()`.

- [ ] Add failing `test_changed_implementation_requires_new_admission`,
      `test_stale_policy_summary_is_rejected` and
      `test_missing_monitorability_is_pending_or_refused`. Same topology with changed callable
      artifact must not reuse approval.
- [ ] Define canonical policy encoding/schema revision and structural graph binding. Bind executable
      package/image or registry digest separately: content-hash `graph_id` alone does not prove
      callable behavior.
- [ ] Implement admission using real Phylax contracts and timestamped observed evidence. Separate
      claimed capability from measured/observed readiness; specify evidence freshness and
      revalidation triggers.
- [ ] Enforce static reachable-target, bounded-cycle, effect/replay and schema/version checks. Once
      R3 ships, add restrict-only reducer/join lint: policy may require declarations or forbid
      choices, never edit them (D-LG-5). Runtime guards still enforce dynamic routes and budgets.
- [ ] Test substituted provider contracts, stale hardware evidence, absent credentials, denied
      artifact and malformed summary. Refuse before the first effect; don't move Telos endpoint
      policy into this module.
- [ ] Run `pytest src/tests/test_graph_admission.py -v`; require all named cases to execute and
      pass, then review/commit.

### Task 2 — Reliable observation delivery and cancellation taxonomy

**Files:** Core observer plugin and tests; Oramasys orchestration wrapper. **Produces:** one
authoritative observation dispatcher and typed terminal outcomes.

- [ ] Add failing critical-checkpointer, mutating-listener, slow-listener/backpressure and
      cancelled-partial-stream tests.
- [ ] Specify critical versus noncritical listeners, deterministic delivery order, bounded buffering
      and failure propagation. A failed authoritative checkpoint blocks progress; a noncritical
      telemetry sink is isolated and reported.
- [ ] Preserve detached rich observations for trusted listeners and sanitized public events. Do not
      multicast a bare async generator or create a second scheduler.
- [ ] Define completed, interrupted, cancelled, budget-exhausted, refused, failed and effect-unknown
      outcomes above Core where appropriate. Stop/revocation must prevent the next dispatch, not
      merely stop the UI stream.
- [ ] Verify retries/nested runs cannot reset total step/time/cost/effect limits. Test zero-step
      budget, cancellation before start/during tool/after remote acceptance and observer failure
      after node completion.
- [ ] Run the new Core plugin tests and Oramasys terminal-outcome tests, then review/commit.

### Task 3 — Transactional approval and effect store

**Files:** Oramasys `graph/approvals.py`, `effects.py`, `recovery.py`. **Consumes:** Task 1 identity
and Task 2 stop semantics. **Produces:** `record_refusal()`, `decide()`, `reserve()`, recovery
records.

- [ ] Add failing `test_single_use_grant_concurrent_consumers`, `test_restart_preserves_pending`,
      `test_wrong_request_digest_refused`, `test_revoked_before_dispatch` and crash-boundary tests
      before code.
- [ ] Adopt an initial transactional store appropriate to deployment: SQLite/WAL for single-host
      operation, behind a versioned repository interface. Multi-host use requires a tested shared
      transactional backend; no claim that local SQLite synchronizes remote workers.
- [ ] Persist refusal, authenticated decision, grant, reservation, attempt and outcome with unique
      operation keys and compare-and-set transitions. Validate request digest,
      graph/implementation/policy binding, principal, scope, expiry and permitted exception at
      reservation and dispatch.
- [ ] Make reservation/use accounting atomic. Concurrent resumes consume at most the allowed uses. A
      crash must not release an uncertain reservation unless nonapplication is positively
      established.
- [ ] Persist the approval/pending frontier so restart does not autoapprove deferred tools. Record
      all refusals with redacted evidence; explanations remain actionable without exposing secrets.
- [ ] Use durable dispatch intent/outbox and reconciliation state. Do not pretend a database
      transaction is atomic with a remote provider call.
- [ ] Test replay, changed graph/policy/model/tool, expired grants, revoke race, use exhaustion, two
      workers, corrupt records and operator identity substitution. For an already-in-flight effect
      report the truthful outcome and stop future operations.
- [ ] Run `pytest src/tests/test_durable_approvals.py src/tests/test_effect_recovery.py -v`; require
      restart and contention cases, review schema migration/retention, then commit.

### Task 4 — Production foreign-provider transport

**Files:** Oramasys provider/gateway contracts and `providers/foreign_transport.py`; Telos-owning
repository's approved dialer integration. **Consumes:** Tasks 1–3. **Produces:** `dispatch()` and
`reconcile()`.

- [ ] Add failing tests for DNS rebinding, redirects, proxy inheritance, TLS failure, SDK retry
      bypass, hidden secondary connection, cancelled response and unknown remote acceptance.
- [ ] Inventory actual SDK connection paths, streaming, retries, uploads, WebSockets and spawned
      processes. An approved URL argument is not proof of enforced egress.
- [ ] Use a supported transport injection seam that genuinely delegates every connection to Telos.
      If an SDK cannot support this, use a contained worker with enforceable egress mediation or
      refuse production mode; no global monkeypatch advertised as containment.
- [ ] Let Telos enforce destination/purpose authorization, DNS/IP/socket binding, TLS, redirect and
      proxy policy. Let Phylax enforce untrusted-effect admission and tool/file/process boundaries;
      Agate hardware feasibility remains separate.
- [ ] Bound timeouts, concurrent connections, request size, stream buffering, retries and budgets.
      Hold idempotency key stable across transport retries; honor provider dedupe/reconciliation
      capabilities rather than assuming them.
- [ ] Test credential isolation, secret redaction, cancellation teardown, malformed responses,
      partial streams, retry-after behavior and transport readiness. Disable insecure fallback and
      implicit environment proxies unless explicitly authorized.
- [ ] First pass an entirely local mock-server/socket-policy suite. Then run opt-in sandbox-provider
      tests with explicit credentials, purpose and spend cap; no live spend as a default test.
- [ ] Run `pytest src/tests/test_foreign_transport.py -v` plus canonical Telos/Phylax conformance
      gates. Enable only named provider/version cells that pass; review/commit.

## 6. Tasks 5–8: graph semantics, recovery and upstream replacement

### Task 5 — R3 reducers, joins and bounded loop semantics

**Files:** Core structural spec/lint (reducer and join declaration fields, new schema version only
for graphs that use them), the single `_run()` scheduler, proposed reducer/join tests; Oramasys
graph builders (concrete declarations), restrict-only policy fields, and registry status updates.
**Consumes:** Task 2 delivery semantics. **Gated:** needs its own R3 ADR and a Core PR before code;
the ownership row is already settled by D-LG-5.

- [ ] Pin reducer choices `REJECT_CONFLICT`, `FIRST`, `LAST`, `CONCAT`, `UNION`, `CUSTOM`; join
      choices `ALL`, `ANY`, `FIRST_SUCCESS`, `QUORUM`, `CUSTOM`. Define UNION ordering/equality and
      CUSTOM validation explicitly in the ADR.
- [ ] Add failing tests where the first declared branch finishes last, two branches conflict, one
      fails, quorum is unattainable and cancellation races a join. Declared branch order, not
      completion timing, determines deterministic merging.
- [ ] Define branch read snapshots, causal/superstep boundaries, nested fan-in and dynamic
      dispatch/Send semantics. Late branch results must not silently mutate a committed ANY/quorum
      join.
- [ ] Implement a superstep frontier inside the single `_run()`: run all frontier nodes on one
      snapshot, commit deltas atomically in branch-name order, emit a `superstep.commit` event with
      a provenance map, default reducer `REJECT_CONFLICT`, and end the run `interrupted` if any
      branch interrupts. `Send` stays deferred. Graphs without reducers, joins or fan-out keep
      schema `"1"` and an identical `graph_id`. When a planned field ships, change its registry
      status to `implemented` in the same reviewed step; the conformance test fails otherwise.
- [ ] Keep every reachable cycle bounded. Loop-to-graph promotion remains an explicit topology
      change when branching/domain routing warrants it, not an automatic rewrite of simple loops.
- [ ] Run `pytest src/tests/graph/test_reducers_joins.py -v` and batch-order mutation tests;
      deliberately introduce completion-order merging and require the suite to fail. Review/commit.

### Task 6 — R4 deterministic durable resume

**Files:** Core existing checkpointer plugin and neutral protocol; Oramasys recovery/effect
integration. **Consumes:** Tasks 1–3/5. **Produces:** `resume()` and versioned checkpoint contract.

- [ ] Add failing crash-before/after-checkpoint, interrupted-tool replay, changed executable digest,
      incompatible schema and unknown-effect resume tests.
- [ ] Extend the existing checkpointer, not a parallel subsystem. Persist checkpoint/parent IDs,
      structural and executable identity, schema/version, durable run ID, logical cursor/frontier,
      state, pending interrupts, branch/join state, relevant plugin positions and policy provenance.
- [ ] Commit checkpoint state and local effect/frontier updates transactionally where they share the
      store; otherwise specify a recoverable handshake. Crash between stores must fail closed rather
      than infer completion.
- [ ] Reject incompatible lineage by default. Provide separately reviewed, explicit migrations that
      preserve audit history; verify state serialization and custom reducer compatibility.
- [ ] On recovery, reconcile unknown external effects before replay. Retry only proven safe
      operations; require provider idempotency or operator remediation when reconciliation cannot
      determine application.
- [ ] Test fork/resume semantics, concurrency fencing, expired ownership, subgraph checkpoints and
      restore after partial parallel completion. Promise deterministic recovery under declared
      effect contracts, not universal exactly-once external execution.
- [ ] Run `pytest src/tests/graph/test_durable_resume.py -v` and Oramasys recovery integration tests
      with process termination at each durable boundary; review/commit.

### Task 7 — Versioned full upstream API replacement program

**Files:** Oramasys compatibility manifest, diagnostics, activation and family subpackages; Core
only for missing neutral semantics. **Consumes:** Task 0 surface inventory, Tasks 1–6 for
effectful/recovery APIs.

Recommended approach: an explicit, isolated replacement distribution/activation mode, with a
framework-free default application and caller-installed real-framework interop as a separate mode.
Alternatives are adapter-only compatibility (lower risk, not full replacement) or process-wide
import hooks (broad reach but high collision/identity risk); do not silently choose the latter.

- [ ] Ratify D-LG-2/3 with package/namespace ownership and supported version policy. Require
      explicit activation before imported/cached upstream modules; refuse ambiguous mixed ownership
      instead of changing `sys.modules` mid-run.
- [ ] Implement pure primitives first, then Runnable/LCEL composition, batch/async/config/callbacks,
      prompts/messages/schema/structured output, graph builders/routes/tools/subgraphs, streaming
      and recovery. Inventory loaders, retrieval, stores, agents, integrations and provider-specific
      APIs separately; no “full” claim from only Runnable/StateGraph coverage.
- [ ] Add unchanged version-pinned black-box upstream examples/tests plus native equivalence cases.
      Test signatures, return/exception types, config propagation, per-input batch config,
      cancellation, stream ordering, metadata, schema generation and serialization where public
      contracts require them.
- [ ] Preserve tiered gaps: unsupported module raises a `ModuleNotFoundError` subtype with correct
      `.name`; missing symbol raises `AttributeError` so `hasattr` and defaulted `getattr` remain
      safe. Document generic interpreter `ImportError` for `from m import X` and provide explicit
      `explain()` details. Broken transitive imports propagate, not masquerade as an unsupported
      symbol.
- [ ] Test namespace coexistence, cached imports, reload, `__spec__`, subprocess/spawn behavior,
      pickle/import identity and distribution/version metadata. Do not fabricate an upstream
      distribution/version identity that suggests unverified parity.
- [ ] Retain static import checks for literal concatenations and conservatively evaluable strings;
      unresolved dynamic arguments require explicit review. Combine metadata checks, source lint and
      runtime import tripwires; none alone proves no hidden imports.
- [ ] For every matrix cell run framework-free native tests and separately pinned real oracles.
      Differential traces compare normalized semantics, not nondeterministic timestamps. Real LG
      export tests remain distinguished from native execution tests.
- [ ] Release per approved surface/version cohort with exact implemented/refused/unsupported counts.
      “100% API inventory accounted for” is distinct from “100% behavior replaced”; no skipped,
      stubbed or refusal-only cells counted as successful parity.
- [ ] Run the matrix runner introduced by Task 0, with zero missing required cells, plus full
      app/Core suites. Review each cohort and commit; never use a broad label to erase unresolved
      cells.

### Task 8 — Pydantic AI and other foreign bridges beyond Phase 1

**Files:** Existing Oramasys bridge location mapped at Task 0; bridge tests and provider transport
integration. **Consumes:** Tasks 1/3/4/6.

- [ ] Keep the import-free graph-as-tool path and explicit single lazy allowlisted agent-as-node
      boundary. Inspect pinned real API behavior rather than guessing changing upstream interfaces.
- [ ] Add failing tests for deferred requests, changed tool arguments after approval, mixed
      approved/unapproved batches, streamed tool calls, cancellation, model retry and restart while
      awaiting human action.
- [ ] Treat the model provider as an untrusted-effect node even when the graph tool itself imports
      nothing. Production requests flow through Task 4; refused/pending requests use Task 3.
- [ ] Translate approved durable outcomes into upstream deferred-tool result semantics without
      autoapproval. Approval of one requested tool is not approval of all model/tool/provider
      effects in the run.
- [ ] Verify typed state/context, message/history boundaries, structured output and
      error/cancellation propagation. Isolate real-agent tests with offline TestModel/FunctionModel
      controls and blocked sockets first.
- [ ] Enable opt-in production cells only after transport and durable approval gates pass; retain
      fail-closed behavior for unsupported provider paths. Review/commit.

## 7. Tasks 9–10: adjacent deferred work, without inventing a second roadmap

### Task 9 — Graph evaluation, optimization, observability and memory

- [ ] Implement the remaining GraphSpec/GraphRun/GraphTrace/GraphCheckpoint vocabulary through their
      owners, with stable identifiers and one observed execution trace. Structural/policy lint must
      enforce actual production admission, not merely describe intent.
- [ ] Define a locked evaluator rubric, held-out/regression datasets and cost/safety/quality gates.
      Candidate agents may change graph/prompt/node candidates, never their evaluator, safety policy
      or acceptance tests.
- [ ] Store candidate artifacts immutably; evaluate in contained runs; promotion is an explicit
      versioned decision with rollback. No production topology mutation from a natural-language
      suggestion.
- [ ] Extend doc 55 observability using sanitized projections, freshness, terminal reason,
      correlation IDs, retention and access rules. Test plugin outage, reconnect, redaction and
      metric cardinality without exposing raw state/prompts/process metadata.
- [ ] For retrieval/Anamnesis, extend docs 20/41/56/67: provenance, trust labels, tenant/principal
      boundaries, poisoning defenses, deletion/retention and grounded evaluation. Select a storage
      backend only after measured query/scale needs; do not make vector infrastructure a
      prerequisite for durable approvals.
- [ ] Each subproject gets its own approved interface spec, failing tests, full test cycle and
      independent review/commit before enablement.

### Task 10 — Controller, portal, identity and optional transport slices

| Deferred slice | Canonical source | Required acceptance evidence |
| --- | --- | --- |
| Authoritative controller claims | Docs 68/69 | Atomic claim, lease expiry, heartbeat/recovery, stale-worker fencing, idempotent outcomes; projection cannot become authority |
| Portal approval/cancel hardening | Doc 70 and cancel-rollback reference | Approval restoration only on positively rollback-safe outcome; unknown cancellation remains consumed; malformed mixed-deploy fields fail closed |
| Identity and authenticated delegation | Docs 49/50/61/62 | Principal binding, replay protection, purpose/scope and revocation; no unauthenticated job or approval mutation |
| Emergency stop / renewal | Docs 03/32 and authority ADR | Stop blocks next effect, active-work containment is truthfully reported, renewal cannot expand scope silently |
| Gateway lifecycle and placement | Docs 17/42/66 | Hardware evidence fresh, readiness observed, destination authorized, teardown and unknown launch reconciled |
| Optional MCP transport | `02-modules/mcp-optional-transport.md` | Tool pinning, least privilege, path boundary, authentication for mutations; portal read-only MCP is not proof of kernel transport completion |
| Atomic skill/tool artifacts and supply chain | Security docs 23/24/31/32 and owning artifact design | Version/digest admission, provenance and update rollback; unreviewed artifact cannot inherit old grant |
| JavaScript / oramaclaw parity | Doc 57 §17b | Separately pinned JS API inventory, scheduler/event semantics and independent oracle suite |

- [ ] Task 0 links each row to exact outstanding requirements and as-built evidence. Split
      already-shipped behavior from remaining hardening; do not reimplement portal Class-0
      documentation search as a privileged mutation.
- [ ] For each selected slice, extend its canonical design and create a narrowly scoped
      implementation plan with concrete files/interfaces/tests. This master plan does not ratify the
      non-binding portal ladder or speculative multi-operator requirements.
- [ ] Execute independently testable slices only after required contracts pass. Keep public
      projections redacted; never leak PID, argv, environment, working directory or raw provider
      credentials.

## 8. Task 11 — Pinning, coordinated publication and PT durable closure

The two coordinated pairs are **Core ↔ Oramasys** (runtime producer/consumer) and **Orama ↔ PT**
(normative design/memory/evidence). Cross-pair links connect decisions and verified implementation.
Coordination is a dependency protocol, not a blanket requirement to change four repos for every
edit.

- [ ] Record a batch manifest: touched surfaces, producer/consumer immutable SHAs, policy/schema
      revisions, implementation and artifact digests, test environment/fixtures, approvals and
      negative impact conclusions for unaffected surfaces.
- [ ] For Core changes, exercise Oramasys against the candidate checkout/overlay separately from its
      production pin. Then update its actual dependency pin and all applicable lock/source records
      to the immutable accepted producer revision, and rerun from a clean environment. An overlay
      pass alone never proves the committed production pin.
- [ ] Verify the entire intervening dependency change, not just the visible feature:
      registry/discovery changes, Agate/Telos dependency sources, build requirements, exported
      interfaces and generated metadata. Identify actual manifests/locks at the current head; do not
      maintain invented or unused lock files.
- [ ] For Orama/PT changes, update canonical decision/current-status references, working memory and
      semantic lessons with exact evidence links. Preserve historical decisions and explain
      supersession instead of rewriting archived narrative to claim newer results.
- [ ] Run bootstrap, full relevant suites, isolated real oracle matrix, import lint/tripwire,
      security/crash/mutation gates, dependency consistency and built-artifact smoke tests. Record
      exact-head CI as pass/fail/pending; pending is not pass.
- [ ] Publish only through existing authorized PRs when they still match the scope; use successor
      PRs when needed. Do not reuse merged PR numbers or push unrelated changes. Re-read remote
      heads after publication; merge only with explicit authorization and valid dependency order.
- [ ] Update PT working memory at the start and end of each approved slice. Distill semantic
      lessons: stable operation keys, audit-versus-dedupe, single scheduler, declared-order fan-in,
      truthful support matrix, optional imports, exact-head evidence and post-merge pin
      verification.
- [ ] Finish with a requirement-to-test-to-artifact closure table. Keep unknown/unimplemented cells
      visible with owner and next gate. Do not mark the saga done because documents or selected
      tests are complete.

## 9. Test strategy and definition of done

Use five separate test tiers: framework-free native contracts; isolated pinned offline upstream
oracles; crash/concurrency/fault injection; local controlled transport/security integration; opt-in
sandbox-provider end-to-end qualification. Keep environments and evidence distinct.

Each implementation task follows the same cycle: write named failing tests; run and confirm the
intended failure; implement the smallest approved contract; run focused and affected regression
tests; review the diff and commit a logical batch. Commit messages and exact commands are recorded
in the subsystem plan after Task 0 resolves repository tooling.

Release completion requires:

- [ ] Every scoped requirement maps to an implemented contract and executed test, or an explicit
      approved exclusion/refusal with accurate user-facing behavior.
- [ ] Fresh bootstrap succeeds using committed production pins, required fixtures and built
      distributions; no hidden local checkout is needed.
- [ ] Approval consumption, crash recovery and revocation races pass under restart and concurrent
      workers.
- [ ] Unknown external outcomes cannot trigger unguarded replay; provider-specific guarantees are
      documented.
- [ ] Actual provider socket paths are controlled; unsupported SDK paths remain disabled.
- [ ] Native schedule, fan-in, interrupt, stream and resume semantics pass the declared version
      cohorts.
- [ ] Evidence, docs and PT memory agree on what is shipped, gated and unsupported.

## 10. Human decisions to review

Recommended defaults are proposals, not already-approved choices.

1. **Compatibility claim:** Approve a versioned full-inventory program with honest per-cell status,
   not an unconditional all-versions/all-integrations parity promise.
2. **Namespace activation:** Approve explicit isolated replacement packaging; no implicit
   process-wide interception. Decide whether unchanged upstream import paths are required for the
   first cohort.
3. **Persistence:** Approve transactional single-host initial deployment, with multi-host backend
   qualification as a separate gate.
4. **Effects:** Approve unknown-outcome reconciliation and operator remediation where provider
   idempotency is unavailable; do not promise universal exactly-once effects.
5. **Human exceptions:** Approve narrowly scoped, revocable, expiring grants with atomic use
   accounting; security/hardware impossibilities remain non-overridable.
6. **Foreign transport:** Approve genuine Telos-mediated transport injection or contained workers;
   refuse SDKs with uncontained network paths.
7. **R3 mechanics:** Declaration placement is decided (D-LG-5: Core GraphSpec, restrict-only
   policy). Still to approve: deterministic declared-order merge and explicit join/superstep
   semantics, before facade parity expansion.
8. **Adjacent scope:** Select which Task 9/10 slices are release requirements now. Keep
   literature/conformity and multi-operator expansion outside this release unless the threat model
   changes.
9. **Execution:** Review subsystem ADRs first, then choose native or explicitly delegated execution.
   This downloadable draft does not begin implementation.

## 11. Risks and fallback policy

| Risk | Containment / truthful fallback |
| --- | --- |
| Upstream API churn or huge integration surface | Freeze supported cohorts; generate inventory diffs; unsupported version diagnostic rather than silent drift |
| Compatibility requires missing Core mechanics | Implement reviewed neutral mechanics; do not hide a second scheduler in the facade |
| Provider lacks idempotency/reconciliation | Unknown outcome remains blocked for remediation; never blindly retry external writes |
| SDK cannot route all traffic through authority | Disable production mode or qualify contained worker transport |
| Artifact/policy update invalidates pending work | Explicit re-admission and lineage migration; old grant cannot authorize changed work |
| Current docs or memory overstate closure | Append corrective current-status evidence and preserve history |
| Master scope too large for one release | Ship independently qualified cohorts; keep unshipped ledger visible without reducing the long-term target |

## 12. Source index and provenance

Base URL: [Orama docs/v2](https://github.com/diazMelgarejo/orama-system/tree/main/docs/v2). Branch
links are navigational; Task 0 replaces execution references with immutable commits.

| Source | Role in this plan |
| --- | --- |
| [57 — MiniGraph reconciliation](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/57-minigraph-final-reconciliation.md) | Single scheduler; R3/R4; structural versus policy ownership; lint/evaluation; Python/JS target |
| [Active loop/graph reference set](https://github.com/diazMelgarejo/orama-system/tree/main/docs/v2/references/loop-graph-compatibility-2026-10-09) | D-LG-1–5, policy contract, corrected gap register and historical evidence |
| [D-LG-5 ADR](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/loop-graph-compatibility-2026-10-09/ADR-D-LG-5-REDUCER-JOIN-DECLARATIONS.md) | Reducer and join declarations live in the Core GraphSpec; policy restrict-only |
| [Ownership registry](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/loop-graph-compatibility-2026-10-09/ownership-registry.json) | Machine-readable one-owner-per-field registry; checked by Oramasys conformance tests |
| [Erratum E12](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/errata-corrections-to-preserved-documents.md) | "GraphSpec authority" wording and reducer/join placement |
| [Compatibility refusal/HITL contract](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/2026-10-09-compatibility-refusal-hitl-contract.md) | Refusal, grant, atomic reservation and revalidation proposal |
| [60 — Phylax monitorability](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/60-phylax-monitorability-design-spec.md) | Claimed versus observed evidence; admission preconditions |
| [62 — Authority Gate-0 ADR](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/62-telos-phylax-authority-gate0-adr.md) | Telos/Phylax authority split |
| [68 — Controller satellite](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/68-orchestrator-controller-satellite.md) | Authoritative claims, leases, durable outcomes and projection limits |
| [69 — Agent envelope](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/69-agent-envelope-standard.md) | Work identity and provenance |
| [70 — Portal HITL ladder](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/70-portal-knowledge-hitl-development-ladder.md) | As-built versus non-binding ladder, cancellation finality and adjacent pointers |
| Docs 03, 17, 20, 23, 24, 31, 32, 41, 42, 45, 47, 49, 50, 55, 56, 61, 66, 67 | Safety, hardware, security, privacy, identity, transport, observability and memory; Task 0 establishes exact sections/status |
| [Core repository](https://github.com/oramasys/perpetua-core), [Oramasys repository](https://github.com/oramasys/oramasys), [PT repository](https://github.com/diazMelgarejo/Perpetua-Tools) | Implementation, consumer-pin qualification and durable lessons |

Live main contents reviewed for docs 57/60/62/68/70 had these Git blob identities respectively:
`eeccee819cae8a1edb11a33ab9673c03e1f5d714`, `0eb424b537996b96408c7bfddd1b79dd20ad2cbd`,
`3d254c826aaa31ff557303499c0f68e6f61f0d12`, `9454406c1f53826a3e51924a7749c961545a4c66`,
`e637e368634d950c8c5d8d0d345c292514314155`. These identify file contents, not repository commit
SHAs. Additional reconciliation/contract material came from the prior-session local snapshot;
adjacent references not fully audited remain explicit Task-0 discovery inputs.

**Coverage boundary:** This draft covers the identified deferred
graph/compatibility/approval/transport capabilities and named adjacent designs. It does not certify
that every deferred requirement anywhere in all repositories has been discovered. The required scope
manifest closes that inventory gap before an exhaustive completion claim.

## 13. Decision ledger and conflict resolution

Each fact has one authoritative place. Where two earlier statements disagreed, the rule is:
a field that changes what a graph computes belongs to Core; a field that only narrows who may
run it or how far belongs to Oramasys policy; a field that only explains belongs to Orama docs.

| ID | Decision | Status | Resolves |
| --- | --- | --- | --- |
| D-LG-1 | Core keeps structural GraphSpec, `graph_id` and lint; Oramasys owns a separate `GraphPolicy` bound by `graph_id` | Approved 2026-10-09; one row amended by D-LG-5 | Policy outside Core schema |
| D-LG-4 | Pydantic AI Phase-1 offline bridge | Approved 2026-10-09 | Bridge scope |
| D-LG-5 | Reducer and join declarations live in Core's structural GraphSpec and `graph_id`; Oramasys authors them; policy is restrict-only; Orama records the registry | Directed by the operator 2026-10-10 | D-LG-1 table row vs rubric on reducers/joins |
| E12 | "GraphSpec/NodeSpec/EdgeSpec authority" in older docs means normative text, not schema code | Recorded 2026-10-10 | Two-GraphSpec confusion (only Core has one) |
| D-LG-2/3 | Broad upstream replacement and new contracts | Still requires review | Task 7 |
| R3 mechanics | Superstep frontier, reducer and join semantics, final field names | Gated: own ADR and Core PR | Task 5 |
| R4 | Durable resume and effect identity `(durable_run_id, logical_operation_id)` plus kind and request digest | Gated; after R3 | Task 6 |

Conflicts found while integrating, and how each was resolved:

- **Plan text vs D-LG-1 row.** The 2026-10-09 plan put reducers/joins in Core files (Task 5) while
  D-LG-1's table put them in Oramasys policy. Resolved by D-LG-5; the plan now follows it.
- **Task 1 vs Task 5.** Task 1 enforced reducer/join checks in admission; it now enforces only
  restrict-only lint once R3 ships.
- **"orama-system authority" wording.** Superseded by E12 in reading; historical files are not
  edited.
- **Decision 7.** Split into a settled placement and an open mechanics approval.

## 14. Change log (Revision 2 vs 2026-10-09 draft)

- Status, baseline and Task 0 head-resolution text updated for the merged pull requests.
- §2 file map and the ownership paragraph replaced by the D-LG-5 single-authority statement.
- Task 1 reducer/join check made restrict-only; Task 5 files and approach follow D-LG-5 and the
  superstep design; human decision 7 updated.
- §12 sources extended with D-LG-5, the registry and E12.
- Added §13 (decision ledger), §14 (this log) and §15 (evidence).
- Long lines wrapped for the markdown linter; no other task text changed.

## 15. Evidence

| Item | Result |
| --- | --- |
| Registry file | `docs/v2/references/loop-graph-compatibility-2026-10-09/ownership-registry.json`, sha256 `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f` |
| Oramasys snapshot | `src/tests/fixtures/graph-ownership-registry.json`, byte-identical, digest pinned in the test |
| Conformance tests | 16 passed in `src/tests/test_ownership_registry.py`, including byte identity against the Orama checkout |
| Full Oramasys suite, oracle lane | 286 passed, 1 skipped, Core `04759a5` |
| Full Oramasys suite, framework-free lane | 286 passed, 1 skipped, Core `04759a5` |
| Core pin | Production and candidate pin unchanged at `04759a5`; no Core change in this batch |
| Branches | Orama `docs/d-lg-5-ownership-registry`; Oramasys `test/ownership-registry-conformance` |
| Pull requests and CI | Recorded in the delivered copy of this document and in each PR body; not merged by the agent |

Not changed by this batch: Core code, Oramasys runtime, policy schema, any `graph_id`. Both pull
requests are cross-referenced and await operator review and merge.

**Security invariant observed:** no private identity, address, credential, device or workstation
literal appears in this document, the registry, the ADR or the tests; categories only.
