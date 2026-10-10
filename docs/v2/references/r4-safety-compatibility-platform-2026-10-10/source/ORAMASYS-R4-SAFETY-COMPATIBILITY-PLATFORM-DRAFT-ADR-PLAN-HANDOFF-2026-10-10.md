# Oramasys R4 Safety, Compatibility and Platform Implementation Plan

> **Review-only hybrid ADR + /PLAN + next-agent handoff.** No implementation,
> repository commit, push, merge, production egress or provider spend is authorized
> by this document. The operator explicitly requires human review before code.
> After that review, use `superpowers:executing-plans` for approved tasks;
> delegate only if the operator explicitly selects delegation.

**Draft identity:** R4 architecture program, revision 1, 2026-10-10 UTC.
**ADR identity:** proposed D-LG-7; reserve the number only after checking the live index.
**Goal:** deliver safe durable execution, versioned upstream replacement and a
self-consistent interoperable platform without breaking permitted legacy concepts.
**Architecture:** one Core scheduler with neutral execution/recovery protocols;
Oramasys coordinates separately owned admission, approvals, effect transactions,
provider transport and compatibility facades. Begin with one authoritative host;
qualify remote workers and larger multi-host deployment as explicit later slices.
**Tech stack:** Python >=3.11 under existing repository constraints, transactional
SQLite initially, typed versioned records, pytest/fault injection, isolated pinned
upstream oracle environments. JS/TS compatibility is a separately qualified cohort.
**Spec:** the draft ADR in Part I of this file; Part II is its proposed execution plan.
**Audience:** human reviewer and the next implementer, including agents unfamiliar
with the preceding saga.

## Review boundary and reading guide

The operator has confirmed the priority order and architectural direction. The
detailed persistence, approval, transport and recovery contracts below are proposed
for review, not already implemented or ratified. Read §1–§12 for decisions, §13–§20
for execution and continuity, and §21–§24 for evidence and the handoff.

Approval of this document must state the approved revision and any exceptions.
Approval of the direction is not a durable runtime grant for tools, model calls or
future effects. Publication and merge follow the operator's actual instructions;
neither is inferred from an architectural approval.

## Global constraints

- Priority 1: **safety**. Priority 2: **compatibility**, forward to LangChain and
  LangGraph and backward to broad inclusion of v1 concepts and terms still allowed
  under v2. Priority 3: **platform self-consistency and interoperability**, internally
  across Oramasys parts and externally with target frameworks.
- A lower priority cannot weaken an invariant of a higher priority. An incompatibility
  required for safety must be explicit, versioned and visible in the support matrix.
- Core owns the structural GraphSpec, `graph_id`, structural lint and one scheduler,
  `CompiledGraph._run()`. Facades, plugins and transport workers do not own traversal.
- Oramasys authors concrete graphs and owns a separate restrict-only GraphPolicy.
  Reducer/join declarations belong to Core GraphSpec and graph identity.
- Orama `docs/v2` is normative design authority, not a second executable schema.
- Telos owns all endpoint-specific security, including actual DNS/socket/TLS paths.
  Phylax owns generic admission/safety/monitorability; Agate owns hardware evidence.
- v1 PT and Orama remain independent of v2 runtime dependencies. v2 is clean-room;
  v1 supplies read-only behavioral evidence, not code imported at runtime.
- No default or published-extra LangChain/LangGraph/Pydantic AI dependency. Real
  framework oracles are isolated test dependencies; optional interop imports remain
  explicit, lazy and allowlisted.
- Preserve historical memory, archives and prior decisions; correct them additively.
  Never force-push, delete history or close an existing PR to simplify coordination.
- Preserve the single-operator LAN threat model. Multiple hosts do not imply multiple
  principals, witness quorums or BFT. Reassess trust boundaries before adding those.
- Project coverage floor is 80%; stricter existing component thresholds remain.
  Coverage alone does not satisfy safety, crash or compatibility acceptance gates.

## Review focus

| Failure class | Expected behavior | Owning task |
| --- | --- | --- |
| Remote acceptance followed by local crash | Preserve unknown outcome; reconcile before retry | T3/T4/T5 |
| Revocation or lease expiry racing dispatch | No new dispatch after the authoritative boundary; identify in-flight work truthfully | T3/T4 |
| Fast branches, partial streams or observer failure | Preserve canonical order and durable progress; no fabricated success | T2/T5/T6 |
| Same topology with changed code, policy or provider | Refuse stale admission, grants and continuation lineage | T1/T3/T5 |
| Cached upstream imports or mixed namespace ownership | Refuse ambiguous activation before executing application code | T6 |

---

# Part I — Draft ADR

## 1. Context and source-qualified baseline

This draft reconciles the latest remaining-capabilities revision, PT working memory,
the R3 ADR/audit and adjacent authority/controller/memory designs. It is a new
qualification of those records, not an edit to their preserved historical claims.

Live PR metadata inspected in this turn:

| Repository / PR | Observed state | Reviewed head / merge commit |
| --- | --- | --- |
| Core #9 | Merged | `34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68` / `4d217f6b9e94e36554a9427198b8c2c4b7febc47` |
| Oramasys #25 | Merged | `48715ff237f72235d31f75238239c8f491c9951b` / `f4dbf338138ede5967b4d3456e940750467e9b1f` |
| Orama #390 | Merged; contains #391 | `7b7f9d84e43f0709115588a95b13a78badb8369f` / `10c09ee21014ab6be184c3a711fdbccaff6f07af` |
| PT #432 | Open | `216effff628f1c86baffc3cc17b75f9f36cb318a`; branch `docs/r3-lockstep-memory` |

Current Oramasys `main` dependency manifest was read separately. Production Core
still pins `04759a50c748444ff97136ea95c1e1289eac3a1a`; the candidate file still pins
`34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68`. Merged producer code and production
consumer promotion are distinct states. No pin is changed in this task.

The PT record reports historical verification: Core 255 tests, candidate application
and offline oracles 333 tests, production-Core application 307 tests with one gated R3
skip. These were not rerun in this document-only turn. No fresh CI-green or full
compatibility claim is made here. Re-poll exact heads and run fresh tests at T0.

### 1.1 R3 guarantees and limitations that R4 must preserve

1. R3 is bounded, single-level fan-out in the existing scheduler.
2. **Every branch settles before the join selects results.** `first_success` selects
   the lowest-named successful branch, not the first completed branch. `any` admits
   every successful branch. Quorum checks success count after settlement.
3. Reducer contributions fold in **ascending branch-name order**, not authoring order
   or completion order. Fixed branch results produce deterministic local state.
4. Branch inputs and custom-fold arguments are detached. This limits mutation leaks;
   it does not establish purity or authorize I/O in a custom callable.
5. Interrupts prevent a region delta from committing. The committed merge is atomic
   only for local state. External writes may already have occurred and are not undone.
6. Graphs without R3 features preserve schema-1 graph identity. R3 features require
   schema 2. Custom callable names are references, not code digests.

### 1.2 What current resume and replay functions actually do

| Existing surface | Current meaning | Missing durable guarantee |
| --- | --- | --- |
| `GraphSpec.from_dict/from_json` | Validate structural description/hash; import no callable | Executable authenticity and authority |
| `SqliteCheckpointer.save/load_latest` | Store/read node-state snapshots | Cursor/frontier, lineage, branch receipts, grants, effects |
| `resume_policy(MERGE)` | Merge supplied scratchpad values | Continuation position and human authorization |
| `resume_policy(DROP)` | Update selected key while retaining other keys | Clearing traversal/interrupt state or granting effects |
| `CompiledGraph.ainvoke(loaded_state)` | **Traverse from START with loaded state** | Continuing from the saved node |
| `EffectDeclaration(replay="idempotent")` | Express intent and require operation identity | Provider dedupe or safe replay |
| Provider/outbound ledger | Evidence under its own existing contract | Universal durable effect deduplication |

R4 must not silently reinterpret a legacy snapshot as a resumable checkpoint.
The old START behavior remains an explicit compatibility path. A new durable
continuation API requires a new validated checkpoint contract and capability.

## 2. Decision record and priority arbitration

| ID | Decision | Status |
| --- | --- | --- |
| P1 | Safety outranks compatibility and platform expansion | Operator confirmed |
| P2 | Forward LC/LG and permitted backward-v1 compatibility outrank expansion | Operator confirmed |
| P3 | Internal consistency and external interoperability remain required targets | Operator confirmed |
| A1 | One Core scheduler; neutral mechanics separated from authority | Existing architecture, retained |
| A2 | Structural reducer/join declarations in Core; policy restrict-only | D-LG-5/6, retained |
| A3 | Transactional approval/effect spine plus durable continuation | Proposed detailed contract |
| A4 | Single authoritative host first; remote workers later without a second writer | Proposed, consistent with docs 45/68 |
| A5 | Versioned isolated replacement cohorts, with no implicit import takeover | Proposed detailed compatibility contract |
| A6 | Actual Telos-mediated connections or enforceable containment; no fallback | Existing authority applied to new transport |
| A7 | R3 settlement/name order unchanged; early-winner timing is a distinct later feature | Proposed explicit preservation rule |

Arbitration rule: identify the conflict, name the higher-priority invariant and record
the affected compatibility cell. Do not disguise a safety refusal as implemented
upstream behavior. When exact parity needs missing neutral mechanics, add a reviewed
Core capability rather than embedding a second scheduler in a facade.

The full upstream replacement target is retained. Releases may qualify bounded
cohorts, but every unimplemented inventory cell remains visible with an owner and
next gate. Scope accounting is not semantic compatibility.

## 3. Alternatives and consequences

| Approach | Benefit | Cost / disposition |
| --- | --- | --- |
| Safety-first versioned platform | Durable authority precedes effectful expansion; one recoverable execution path | Selected direction; larger initial contract work |
| Compatibility-first wrappers | Earlier API surface | Rejected as governing order: wrappers cannot supply missing approval/replay safety |
| Multi-host/platform-first | Earlier deployment reach | Deferred: introduces distributed failure modes before recovery is qualified |

Within the selected approach, pure facade work may proceed after inventory approval.
Effectful and recovery API cells stay disabled until their authority prerequisites
pass. This avoids making the entire compatibility program wait for unrelated platform
work while preserving the operator's priority order.

Costs include migrations, fault-injection infrastructure and provider-specific
qualification. Universal exactly-once external execution is not promised. Where a
provider cannot dedupe or reconcile, an uncertain operation stops for remediation.

## 4. Ownership, boundaries and dependencies

| Owner | Executable responsibility | Must not absorb |
| --- | --- | --- |
| Perpetua Core | Graph mechanics, structural identities/lint, neutral cursor/checkpoint protocol, scheduler observations | Policy engines, approval authority, provider/storage SDK imports in engine |
| Oramasys application | Concrete graph, policy binding, budgets, workflow effects/approvals, compatibility and provider composition | Duplicate Telos/Phylax/Agate authority or traversal |
| Oramasys controller module | Claims, leases, claim idempotency and claim-state outbox; one writer | Workflow-effect key/table or gossip as authority |
| Telos | Endpoint identity, purpose authorization, DNS/rebinding, sockets, proxy/TLS/redirect security | Generic approval or graph policy |
| Phylax | Principal/capability admission, artifact/provenance, safety policy and monitorability | Endpoint classification or workflow decisions |
| Agate | Measured fit/placement and forbidden/impossible hardware decisions | Approval or queue mutation |
| Provider owner | Protocol, readiness/lifecycle, outcome/reconciliation adapter | Independent endpoint-security connector |
| Orama docs/v2 | Normative decisions, registry and supersession/evidence links | A runtime GraphSpec or second roadmap authority |
| PT .agent | Portable working/episodic/semantic memory and parity evidence | v2 runtime service or hidden production authorization |

Doc 68's accepted home is `src/orama/orchestrator_controller/` inside Oramasys.
Its earlier standalone-repository row is a placeholder, not the current packaging
decision. This draft does not create a new controller repository.

Keep three idempotency domains distinct: controller claim requests; application
logical workflow effects; provider-native dedupe keys. Link receipts between them
without reusing a key or creating a second authority over another domain's tables.

Keep approval and transport separate. Human approval permits only a supported
exception; it cannot make invalid authentication, impossible hardware, unsafe
endpoints or an uncontained SDK acceptable.

## 5. Artifact identity, admission and trust

Proposed immutable `ArtifactBinding` includes structural `graph_id`, implementation
artifact digest, state-schema version, policy digest, registry profile digest,
provider-contract digest and execution-semantics version. Use canonical encoding with
an explicit domain and schema version for each digest. Unknown fields fail closed;
extension metadata has an explicit location and cannot carry hidden authority.

Graph identity proves structural content. It does not prove what a bound callable
does. Admission verifies its built artifact/code registry separately, plus actual
Phylax decisions, fresh observed evidence and Agate feasibility where applicable.
Derived/reconstructed evidence cannot satisfy a requirement for Observed sources.

Each run binds one immutable artifact set. Hot reload cannot mutate it. A changed
implementation/policy/provider contract requires re-admission and an explicit
continuation migration or refusal. Linked application policy summaries are generated
projections with digest checks; the separate policy file remains authoritative.

Permitted feasible operations need not ask a human repeatedly. Gate results are
`allow`, `refuse` or `pending`; only explicitly overridable, valid requests may
enter the human-exception path. Every refusal has an actionable redacted reason.

## 6. Durable HITL and effect protocol

### 6.1 Records and identities

Initial storage: one host-local transactional SQLite store, owned by Oramasys and
accessed through a versioned interface. It holds immutable events and transactional
current-state projections. CAS version transitions, constraints and audit/outbox
entries commit together. An append-only event file alone does not provide CAS.

| Record | Required binding |
| --- | --- |
| Approval request | Principal/audience, logical operation, exact request digest, artifact set, exception IDs, requested scope |
| Decision/grant | Request ID, authenticated decision maker, decision, UTC issuance/expiry, use limit, revocation version |
| Reservation | Operation/grant references, attempt ID, expected versions, fencing epoch, deadline |
| Effect intent | Durable run + logical operation ID, effect kind, provider identity/key, request digest, dispatch status |
| Effect receipt | Confirmed success, confirmed nonapplication/failure, or unknown; provider evidence and reconciliation disposition |

Logical operation IDs remain stable across transport retries. Distinct loop
iterations and branch activations receive distinct IDs; restarting the same
activation reuses its ID. Attempt IDs are separate. Reusing an operation ID with
changed content is a conflict, not a retry. Forked runs have new run identities;
old effect receipts cannot authorize new external writes.

Grant state and effect state are separate machines. A used grant is not proof of
provider success; provider success is not proof of local graph-state commit.

### 6.2 State transitions and dispatch boundary

1. Admit the exact artifact/request. Refuse non-overridable failures; persist an
   eligible pending exception request before exposing it to the operator.
2. Authenticate the human decision. Store approve/deny and a narrowly scoped grant;
   no UI Boolean or framework resume value becomes a grant by itself.
3. Reserve atomically: validate scope, request/artifact digests, expiry, use count,
   current authority versions and worker ownership. Competing consumers conflict.
4. Revalidate mandatory gates at durable dispatch authorization. Atomically record
   dispatch intent/use consumption and an outbox item. This transaction is the
   linearization boundary for revocation versus dispatch.
5. Send only the recorded intent through qualified transport. Revocation before
   this boundary blocks it. Revocation afterward marks authorized in-flight work,
   requests cancellation where supported and blocks subsequent operations.
6. Persist provider outcome separately from applying its result to graph state.
   Commit the result/checkpoint once, or retain a recoverable handshake record.
7. Retry only after proof of nonapplication or qualified provider dedupe. Unknown
   outcome remains blocked until reconciliation or explicit incident disposition.

Immediately before I/O, transport rechecks current permit, cancellation, fencing
and endpoint admission. A revoked queued intent that has not been handed off is
suppressed, not labelled remotely in flight. Persist separate authorized, handed-off
and provider-accepted milestones. The last local check cannot be atomic with a
remote socket write: a concurrent revocation after handoff is an in-flight race,
with cancellation/reconciliation and no claim that an accepted effect was undone.

Expiry never releases an uncertain reservation for automatic reuse. A timed-out
request is not evidence that the provider did nothing. A denial/expiry/revocation
never becomes approval after restart. Renewal creates an audited version and cannot
expand scope silently. Operator remediation records evidence; it cannot invent
nonapplication or permit a non-overridable security bypass.

### 6.3 Crash windows

| Crash boundary | Recovery action |
| --- | --- |
| Before durable reservation | No dispatch authority exists |
| After reservation, before dispatch intent | Revalidate reservation; prove no dispatch before restoring uses |
| After dispatch intent, before known send | Treat as uncertain unless transport evidence proves nonapplication |
| After remote acceptance, before receipt | Reconcile stable provider key; never blindly resend |
| After receipt, before state commit | Apply recorded result once; do not call provider again |
| After state/checkpoint commit, before event publication | Redeliver outbox projection; do not rerun node |

An application database and a remote provider do not share a transaction. A hash
chain can aid tamper detection but cannot turn those writes into distributed atomicity.

## 7. Production foreign-provider transport

Start with one named provider/version capability cell and a manifest that states
effect classes, endpoint purposes, credential requirements, deadlines, stream/error
semantics, idempotency scope/retention and reconciliation support. Do not enable an
entire framework family because one provider path passes.

All SDK network paths must be enumerated: model calls, tool calls, retries,
redirects, authentication refresh, discovery and telemetry. Prefer injectable
Telos-backed transport. If injection cannot contain every path, use a worker whose
OS/network boundary permits only the authorized Telos-mediated channel. A Python
socket monkeypatch is a test tripwire, not production containment.

The worker executes a declared provider operation, not the graph scheduler. It
receives only required credentials/data, a scoped capability and a fencing epoch.
Provider adapters own serialization and provider-specific outcomes; Telos owns
destination security, peer pinning and credential handling across redirects.

Cancellation is a request, not proof of rollback. Record confirmed nonapplication,
confirmed application or unknown. Partial model streams may have incurred cost
and cannot be treated as no effect. Retry budgets and total run cost survive
restart. Paid egress has explicit opt-in and spend limits; tests default offline.

No semantic-only precheck followed by a raw SDK connection qualifies. Unavailable
Telos/admission/containment fails closed with no direct-network fallback.

## 8. R4 durable continuation

### 8.1 Neutral checkpoint contract

Extend the existing checkpointer seam; Core engine imports no storage backend.
The proposed `DurableCheckpointV1` carries:

- Checkpoint ID, parent ID, durable run ID, lineage/fork identity and record version.
- Structural graph identity, executable binding, semantics and state-schema versions.
- Detached serialized state plus committed logical cursor/frontier and activation IDs.
- Region activation, branch outcomes/receipts, join/reducer identities and commit status.
- Pending interrupts and their stable IDs; resume-input bindings and consumption status.
- Effect/approval references, controller lease/fencing epoch and remaining budgets.
- Critical-observer offsets, durable event sequence and integrity/provenance references.

Core consumes neutral continuation data and an admission result through protocols.
Application-owned policy/provider/grant details remain opaque references validated
by Oramasys. Do not add an application policy schema to GraphSpec.

Legacy node/state snapshots are marked non-resumable. Migration may reconstruct
state but cannot reconstruct missing cursor or external outcomes by assumption.
They support explicit new traversal only, with effect safeguards and a new run ID.

### 8.2 Recovery algorithm

1. Authenticate the resume request, resolve authoritative run ownership and acquire
   a new fencing epoch through CAS. Stale workers cannot commit or dispatch.
2. Verify checkpoint integrity, parent lineage, version support and artifact binding.
   Reject changed code/policy unless a separately approved migration supplies proof.
3. Reconcile all unknown effects reachable before further progress. Replay pure
   computation only under its declared deterministic contract; do not replay writes.
4. Validate pending grants/interrupt decisions against current authority and expiry.
   An upstream resume value supplies data only; it supplies no effect authority.
5. Rebuild the neutral cursor and unfinished activations. Reuse stored successful
   branch outcomes; do not rerun a completed effect branch simply to rebuild fan-in.
6. Continue through the same `_run()` scheduler, then persist state/frontier/effect
   application receipts atomically when co-located. Otherwise use a versioned
   prepare/commit handshake with explicit recovery; never infer a cross-store commit.
7. Emit redacted post-commit projections. Duplicate delivery is allowed and deduped
   by sequence/identity; it cannot mutate execution authority.

R3 branches still all settle before selection. Partial branch receipts during a
crash enable recovery, not a change to join timing. Interrupt precedence remains.
Early cancellation, dynamic Send and nested frontiers need their own mechanics ADR
and compatibility tests; this draft does not activate them by renaming R3.

Checkpoint retention must preserve unresolved-effect and pending-approval evidence.
Backups and restore tests cover the authoritative database and referenced artifacts.
Migration is explicit, reversible where feasible and keeps original lineage.

## 9. Forward compatibility and upstream replacement

### 9.1 Inventory and packaging

Maintain a machine-readable API/version matrix: modules, symbols, signatures, type
identity, config propagation, synchronous/asynchronous invocation, batch order,
streaming/callbacks, errors, serialization, graph topology and persistence behavior.
Include loaders, retrieval, agents, integrations and provider APIs; Runnable and
StateGraph alone are not the full inventory.

Use separate explicit modes: native API, real-framework interoperability and isolated
replacement packaging. Replacement may supply unchanged import paths only within a
declared isolated environment. Refuse mixed/cached ownership; never replace
`sys.modules` mid-run or falsify upstream distribution/version metadata.

Cells are `implemented`, `policy-refused`, `technically-unsupported` or
`not-yet-implemented`. Only executed semantic conformance earns implementation.
Count missing/skipped/refusal cells separately; no global drop-in percentage from
selected oracle passes. Keep the target broad while publishing truthful cohorts.

### 9.2 Required semantics and intentional differences

| Surface | Qualification required |
| --- | --- |
| LC Runnable/LCEL | Type/protocol identity where public behavior requires it; sync/async/config/callback propagation; ordered batch and streaming |
| LG builders/routes | START/END, Command routing, dynamic Send, subgraphs/nesting and state/reducer behavior through neutral Core mechanics |
| LG interrupts/resume | Stable interrupt identity, thread/config handling, node re-entry semantics, persistence and safe effects |
| Persistence/wire formats | Explicit serializers/version migrations; upstream saver/store contracts separately inventoried |
| Integrations/providers | Provider-specific API/error/streaming contracts plus qualified transport and effects |
| Python / JS | Separate inventories, environments and evidence; Python passes establish no JS parity |

Upstream interrupt behavior may re-enter node code. A compatible facade must preserve
the observable contract for qualified pure cases while requiring effect wrappers
or refusing unsafe re-entry for writes. A blanket ban or silent dedupe is not full
parity. Native R3 name-ordered settlement must not be advertised as every upstream
parallelism semantic; add a reviewed execution-semantics version where needed.

Current known gaps remain tracked: fanout export is refused; dynamic Send/nesting,
upstream Runnable identity, some config, unbuffered sync streams, checkpoint wire
parity and durable continuation are not established by historical oracle passes.

### 9.3 Tiered diagnostics and import contracts

Unsupported whole module: `ModuleNotFoundError` subtype with correct `.name` and
actionable details. Unsupported symbol through `__getattr__`: `AttributeError`
subtype so `hasattr` and `getattr(default)` work. `from m import X` may expose
Python's generic ImportError; explicit `explain()` supplies the richer gap record.
Broken transitive dependencies propagate their real exception rather than being
relabelled as a missing optional framework.

Static lint evaluates conservative literal strings, concatenation and literal-only
f-strings. Unresolved dynamic import arguments require explicit review. Runtime
tripwires block eager imports; lazy calls are statically checked too. Require exact
TYPE_CHECKING branches and reject stale allowlist entries. Test finder-returning-None,
module errors and pytest `importorskip` behavior; required oracle cells fail rather
than silently skip when an environment is missing.

## 10. Permitted backward-v1 concepts and migration

Broad inclusion means retaining useful vocabulary and behavior where it satisfies
v2 ownership and safety. It does not authorize runtime coupling or resurrect
superseded authority. Create a concept register with source, intended meaning,
owner, disposition and acceptance fixture for every retained term.

| v1 concept / term | v2 disposition |
| --- | --- |
| Prompt → Chain → Loop → Graph | Retain least-powerful-control doctrine; promote only when topology is domain logic |
| PerpetuaState, scratchpad, node delta | Retain canonical semantics with explicit facade conversion; no competing GraphState |
| GraphSpec / Run / Trace / Checkpoint | Retain distinctions; state and trace are not durable continuation or long-term memory |
| Gateway, model server, provider lifecycle | Retain provider-facing names and thin facades; Telos executes endpoint security |
| Task, job, claim, lease, heartbeat, board | Retain concepts with separate authority; liveness/gossip never mutates v2 claims |
| Envelope, author/actor, lineage, source_ref | Follow doc 69 additive neutral header and each panel's canonical owner |
| Monitorability evidence | Preserve v1 advisory meaning; migrate through explicit Phylax adapter, never reinterpret in place |
| PT .agent / capture_lesson / legacy lessons | PT remains v1 development-memory authority; preserve explicit legacy path and provisioning rules |
| Approval preview, cancel, rollback | Preserve observed rollback-safe conditions; unknown outcomes remain consumed |
| Historical endpoints/security implementations | Read-only golden evidence for clean-room v2; no imports or silent fallback |

Use additive compatibility aliases when their semantics are honest. A historical
no-op argument must not claim enforcement. Retire or explicitly refuse concepts
that require dual authority, unverified replay, silent fallback or authentication
by self-declared name/topology. Keep supersession pointers for every such decision.

Anamnesis remains separately provisioned future work. Private runtime evidence is
not automatically tracked or pushed. Preserve weekly sanitized promotion,
append-only semantic corrections and human push control; recheck the approved
legacy initialization/automatic post-provision migration rules before implementation.

## 11. Internal consistency and later multi-host interoperability

One contract owner per field/record. Registry conformance checks complete producer
and consumer inventories, exact owners/records, schema versions and literals.
Validate duplicates/unknown keys before normalization or dictionary indexing can
erase a violation. A generated policy summary, dashboard or event is a projection.

Multi-host follows three explicit deployment stages:

| Stage | Authority and deployment | Required proof |
| --- | --- | --- |
| H0 | Single authoritative host; local durable store | Restart/crash/CAS/backup qualification |
| H1 | Same single authority plus authenticated remote contained workers | Leases, fencing, partition/cancel/reconciliation, capability/transport checks |
| H2 | Larger fleet and qualified authority backend or failover | Transactional backend, migration, stale-leader fencing, recovery/RPO/RTO evidence |

H1 may use a narrow authority API backed by host-local SQLite. Do not share the
SQLite file over LAN or infer distributed locking from gossip. H2 persistence/backend
and failover need a separate ADR after measured needs; PostgreSQL is a candidate,
not an already approved mandatory dependency. Split-brain prevention requires one
valid writer epoch; a lease alone cannot fence an external provider that ignores it.
Such providers still require dedupe/containment/reconciliation guarantees.

Doc 45's single-operator model remains. H2 does not automatically enable
multi-principal co-signature; reassess real witnesses, trust boundaries and observed
failure modes first. Mesh/MCP/A2A provide transport/projections, not job authority.

## 12. Proposed amendments, non-goals and review decisions

After human review, add an active reference rather than rewriting archived files.
Qualify doc 57 §10 with D-LG-6's merged R3 semantics and §11 with the reviewed R4
contract. Qualify §12 using D-LG-5 ownership. Extend docs 58/59 only where observer
criticality/value isolation changes; extend docs 60/62 for actual new enforcement
evidence and docs 68/69 for controller/continuation interfaces without redefining them.

This draft does not introduce a new git doctrine, a new controller repository,
universal provider exactly-once, implicit framework import interception, automatic
production graph optimization, BFT/quorum requirements or compliance deadlines.
Those remain separately scoped decisions.

Human review should explicitly accept or amend: the state machines and dispatch
linearization (§6); legacy snapshot versus durable continuation (§8); versioned
isolated facade packaging (§9); retained-v1 concept rubric (§10); H0→H1→H2 sequence
(§11); and the first enabled provider/API cohorts after T0 inventory.

---

# Part II — /PLAN for preparation and execution

## 13. Preparation protocol and proposed file map

Paths listed as **proposed** are design decisions to review, not existing files.
At T0 map them to current instructions/layout; preserve the established `src`
execution standard. Record justified relocations before implementation rather than
creating duplicate subsystems. Do not edit repositories during this review-only turn.

| Repository | Existing seam | Proposed focused additions |
| --- | --- | --- |
| Core | `src/perpetua_core/graph/{engine,spec,lint}.py`, `graph/plugins/` | Neutral continuation records/protocols beside existing checkpointer; durable-resume tests in `src/tests/graph/` |
| Oramasys | `src/orama/graph/perpetua_graph.py`, provider and gateway contracts | `src/orama/graph/{admission,approvals,effects,recovery}.py` where no equivalent exists; transaction adapter outside engine |
| Oramasys | Framework bridges and compatibility tests | `src/orama/compat/{manifest,diagnostics,activation}.py`; `src/scripts/compat/run_matrix.py` proposed |
| Oramasys | Provider contracts/ledgers | `src/orama/providers/foreign_transport.py` and focused provider adapters |
| Oramasys | Accepted controller home | Extend `src/orama/orchestrator_controller/`; no duplicate claim writer |
| Orama | `docs/v2/references/remaining-capabilities/` | Reviewed ADR, scope/compatibility/concept register, closure index; amendments link rather than duplicate authority |
| PT | `.agent/tools/learn.py`, working/episodic/semantic memory | Additive per-slice evidence/lessons through tooling, on active #432 if still open |
| Telos / Phylax / Agate | Canonical owning interfaces | Only verified missing contracts in their actual repos, with consumer qualification |

### Proposed interface vocabulary

Freeze fully typed models in owning subsystem specs before code. All durable models
are schema-versioned; functions return discriminated outcomes, never truthy Booleans.

| Interface | Consumes | Produces / owner |
| --- | --- | --- |
| `admit_artifact(binding, context)` | ArtifactBinding + authenticated AdmissionContext | AdmissionDecision; Oramasys consuming Phylax/Agate |
| `request_exception(operation, refusal)` | OperationKey + eligible refusal | ApprovalRequestId; Oramasys |
| `decide_exception(request_id, decision)` | Authenticated ApprovalDecision | GrantReceipt; Oramasys |
| `reserve_effect(intent, grant_ref, expected_version)` | EffectIntent + optional grant + CAS version | ReservationOutcome; Oramasys |
| `authorize_dispatch(reservation_id, epoch)` | Valid reservation + live gates/epoch | DispatchPermit or refusal; Oramasys |
| `dispatch_effect(permit, request)` | Bound ProviderRequest + permit | ProviderOutcome; provider adapter through Telos |
| `reconcile_effect(operation_key)` | Stable logical identity + stored evidence | ProviderOutcome; Oramasys/provider adapter |
| `prepare_continuation(checkpoint_id, context)` | Durable checkpoint + ResumeContext | ResumeDecision + neutral cursor; Oramasys |
| Core continuation entry | Validated neutral cursor + state + protocols | Same scheduler observations; signature fixed in R4 subsystem spec |

Core's continuation entry must not accept an Oramasys approval model. Treat ordinary
`ainvoke(state)` and durable continuation as distinct until facade semantics are
qualified. No execution task may rely on an undefined record or an unapproved seam.

## 14. Task T0 — meticulous inventory and contract freeze

**Deliverable:** immutable source/evidence manifest and subsystem specs. **Dependencies:**
human review of this draft; no production feature enabled by T0.

- [ ] Read root/nested instructions and active PR inventory; resolve merged baselines
  and surviving branches. Do not revive merged PRs or recreate PT memory PRs.
- [ ] Reserve the ADR number and capture exact source versions, tree/fixture digests,
  dependency manifests, workflow pins, environment locks and current import locations.
- [ ] Enumerate all deferred requirements from docs 57–59, D-LG-1–6, the rev-2 plan
  and named adjacent designs. Give each an ID, owner, disposition, dependency and test.
- [ ] Inventory Python and JS API/version cohorts and retained-v1 concepts. Historical
  oracle versions (LG 1.0.3, LC Core 1.0.7, Pydantic AI slim 1.0.18) are evidence,
  not an automatic choice of new release versions; pin new targets after review.
- [ ] Check production/candidate pins, complete registry profiles and combined branch
  behavior. Plan R3 pin promotion as a bounded prerequisite with fresh consumer tests.
- [ ] Freeze T1–T5 typed records, schema migrations, failure taxonomy, clock/expiry
  policy and exact file/test commands in subsystem specs. Review those contracts.
- [ ] Run clean bootstrap/build/import and affected exact-head suites; missing required
  owner fixtures/oracle cells fail. Record environment failures separately from bugs.

**Gate:** every known requirement has a disposition, no competing owner, and no stale
pin/status claim. Attach a source-coverage map; do not assert every repository-wide
deferred item was found if its source was not reviewed.

## 15. Tasks T1–T2 — admission and reliable progress

### T1: artifact admission and policy binding

**Consumes:** T0 ArtifactBinding/AdmissionContext. **Produces:** executable admission
receipts and restrict-only policy enforcement. **Owner:** Oramasys, Phylax interfaces.

- [ ] Write/run failing `test_same_graph_changed_code_invalidates_admission`,
  `test_stale_policy_summary_refused`, `test_nonobserved_source_cannot_admit`,
  `test_missing_hardware_or_principal_refused` and unknown/duplicate-input tests.
- [ ] Implement canonical artifact binding and actual owner decisions; validate before
  indexing. Custom callable reference strings never import or authenticate code.
- [ ] Add runtime route/budget checks and revalidation triggers; declarations are not
  runtime authority. Test stale provider contracts and absent enforcement services.
- [ ] Run focused tests, complete owner/consumer regressions and conformance; review
  and commit one logical batch after approval permits implementation.

### T2: observation criticality, budgets and cancellation

**Consumes:** one scheduler seam. **Produces:** durable progress delivery contract.
**Owner:** Core neutral delivery; Oramasys terminal policy and accounting.

- [ ] Write/run failing tests for critical-checkpoint outage, mutation by listeners,
  slow telemetry/backpressure, cancellation with partial streams and repeated restarts.
- [ ] Use one rich-observation drain with detached listener payloads. Critical persistence
  failure blocks further progress; noncritical telemetry fails visibly and separately.
- [ ] Preserve deterministic ordering and post-commit provenance; no observer schedules
  nodes. Bound buffering and specify consumer disconnect/cancel behavior.
- [ ] Persist run-wide step/time/cost/effect budgets. Neither retries, nested runs nor
  restart resets them. Distinguish completed/interrupted/cancelled/refused/budget/unknown.
- [ ] Run Core plugin and Oramasys lifecycle suites; test stop prevents next dispatch,
  rather than merely hiding the stream. Review/commit with exact evidence.

## 16. Tasks T3–T5 — durable safety vertical slice

### T3: approval/effect transaction spine

**Consumes:** T1 admission, T2 stop/budget semantics. **Produces:** records and CAS
interfaces in §13. **Owner:** Oramasys; reuse controller ownership, not its key space.

- [ ] Write/run failing single-use concurrent-consumer, wrong-digest, restart-pending,
  denied/expired/revoked, changed-artifact and crash-window tests before code.
- [ ] Implement versioned SQLite schema/migrations, unique logical operation keys,
  immutable events, CAS projections, scoped grants/reservations and dispatch outbox.
- [ ] Test revocation on both sides of dispatch authorization; an in-flight receipt
  cannot become a false rollback or silently free a consumed grant.
- [ ] Test operation-key reuse with different requests, corrupt records, UTC expiry
  after restart, uncertain reservation retention and atomic use limits.
- [ ] Qualify backup/restore and redaction. Run focused and complete application suites,
  review schemas/security and commit. Grants alone do not enable production transport.

### T4: one qualified foreign-provider transport

**Consumes:** T3 permits/intents; Telos actual transport; Phylax/Agate gates.
**Produces:** manifest, dispatcher and reconciler for one approved provider cohort.

- [ ] Write/run failing bypass-socket, mixed-DNS, redirect credential, proxy, retry,
  partial-stream, cancellation, stale-epoch and acceptance-before-crash tests.
- [ ] Implement real transport injection or contained worker. Enumerate SDK side paths;
  refuse any uncontained path. Never copy Telos security semantics into the adapter.
- [ ] Implement request deadlines, stable provider keys, dedupe retention limits,
  usage receipts and confirmed/unknown outcomes. Test reconciliation independently.
- [ ] Run local controlled-server integration first. Then use explicitly authorized
  sandbox credentials/spend for named production cells; default CI remains offline.
- [ ] Review actual network evidence and provider limitations before opt-in enablement;
  publish contract/evidence and commit the bounded slice.

### T5: R4 cursor/frontier and effect-aware continuation

**Consumes:** T1–T4, merged R3 mechanics. **Produces:** DurableCheckpointV1, recovery
handshake and neutral continuation entry through the same Core scheduler.

- [ ] Write/run failing `test_resume_does_not_restart_at_start`,
  `test_receipt_before_checkpoint_does_not_redispatch`,
  `test_partial_region_reuses_finished_branch`,
  `test_legacy_snapshot_is_not_continuation` and lineage-tamper tests.
- [ ] Add neutral cursor/checkpoint protocols at the existing seam, storage adapter
  outside engine, and application effect/approval references. Preserve ordinary invoke.
- [ ] Persist cursor/state/receipt application together or implement tested prepare/commit
  recovery. Kill/restart real subprocesses at every durable boundary, not just mocks.
- [ ] Test deterministic branch-name settlement/folds under every delay permutation,
  interrupt precedence, unknown-effect blocking, stale-worker fencing and exhausted budgets.
- [ ] Test explicit migrations, fork identities, custom reducer binding, retained causal
  provenance and backup restore. Dynamic/nested semantics remain separately scoped.
- [ ] Run Core + consumer + fault suites and mutated unsafe variants; review/commit only
  after failures are meaningfully detected. Do not promise provider exactly-once.

## 17. Tasks T6–T7 — compatibility and Pydantic AI expansion

### T6: versioned replacement cohorts and retained-v1 register

**Consumes:** T0 inventory; T1–T5 for effectful/recovery cells. **Produces:** explicit
activation distribution, truthful matrix and concept mappings. **Owner:** Oramasys;
missing neutral execution mechanics require a Core ADR.

- [ ] Build matrix runner tests that fail for missing required cells, silent skips,
  unsupported versions, stale artifacts and incomplete inventories.
- [ ] Implement pure facade primitives first, then Runnable/config/callback/stream
  contracts. Run unchanged pinned upstream fixtures alongside native equivalence tests.
- [ ] Qualify namespace/type/pickle/metadata/subprocess identity and cached-import
  refusal. Test tiered errors, finder-returning-None, `importorskip`, computed imports
  in lazy functions and unresolved-argument review.
- [ ] For Command/Send/nesting/checkpoint parity, first specify any missing neutral
  mechanics and execution version. Do not claim R3 fanout already supplies them.
- [ ] Add golden fixtures for retained-v1 concept translations and prohibited ownership
  leakage; v1 builds must remain independent of v2 dependencies.
- [ ] Compare normalized state/event/error traces, input-order batch results and actual
  streaming/cancel behavior; serial batching is a control, not proof of order invariance.
- [ ] Publish exact per-cohort implemented/refused/unsupported counts, drift tests and
  rollback compatibility. Review/commit independently testable cohorts.

### T7: Pydantic AI through the same effect boundary

**Consumes:** T3/T4/T5. **Produces:** opted-in provider/tool cells with typed outputs,
dependencies, usage and deferred requests. **Owner:** existing Oramasys bridge.

- [ ] Preserve import-free graph-as-tool and one explicit lazy allowlisted agent import.
  The agent provider remains an untrusted effect source even when its graph tool is pure.
- [ ] Write/run failing mixed-approved tools, edited arguments, pending restart,
  provider retries, usage exhaustion and streamed-tool cancellation tests.
- [ ] Map authenticated durable outcomes into pinned deferred-tool results; approve
  only exact individual requests. New arguments invalidate the old grant.
- [ ] Test typed state/output/history/dependency mapping with blocked-socket offline
  TestModel/FunctionModel oracles, then qualified sandbox transport cells.
- [ ] Keep unsupported production cells refused; API approval and import allowlisting
  do not contain a provider connection. Review/commit with explicit enablement scope.

## 18. Tasks T8–T10 — follow-on continuity and larger platform scope

These are required tracked follow-ons, not one implicit platform-wide implementation.
Each gets its own source-backed subsystem spec and approval before code.

| Task | Scope | Canonical sources / gate |
| --- | --- | --- |
| T8a | Dynamic Send, nested regions/subgraphs, optional early-cancel joins | Docs 57–59 + D-LG-6; reviewed mechanics/version semantics and new oracles |
| T8b | Full LC/LG integration inventory; LangGraph.js/oramaclaw | T6 matrix; separately pinned runtimes and type/stream/checkpoint qualification |
| T8c | Evaluation/autoresearch/graph optimization | Doc 57 §14; fixed evaluator, held-out data, safety/cost/quality gates and explicit promotion |
| T8d | Anamnesis, retrieval and private memory | Docs 20/41/56/67; provisioned backend, provenance, poisoning/privacy/deletion and sanitized HITL promotion |
| T8e | Observability and monitorability hardening | Docs 55/60; sanitized projections, freshness/Observed checks, outage/retention/access controls |
| T9a | Controller claims, identity/envelopes, renewal/emergency stop | Docs 49/50/61/68/69; one writer, authenticated capability and stop/fencing tests |
| T9b | Portal cancel/approval rollback and mixed deploy | Doc 70 + cancel contract; only positively safe rollback restores a claim |
| T9c | Gateway placement and provider readiness/lifecycle | Docs 17/42/62/66; observed readiness, actual transport and unknown-launch reconciliation |
| T9d | Optional MCP/A2A/mesh, skill/tool supply chain | Module plan + docs 23/24/32/43/50; least privilege, pinning and no projection authority |
| T10 | H1 remote workers then H2 larger multi-host | Docs 45/49/68; partitions/fencing/backup/backend/failover ADR; no new threat model by implication |

T8c researchers may mutate candidates, not the evaluator, safety policy or acceptance
tests. Promotion is versioned and reversible; no live topology rewrite from a
natural-language suggestion. Retrieval infrastructure is not a prerequisite for the
approval store. Public Class-0 documentation search remains its shipped read surface;
it does not become privileged simply because durable approvals are introduced.

T10 tests controller restart, delayed/replayed messages, duplicate delivery,
clock jumps, stale principal state, expired leases, lost worker receipts, interrupted
streams, network partition and split-brain attempts. Safety may sacrifice availability;
the system reports blocked/unknown work rather than duplicate-dispatch success.

## 19. Dependency order and acceptance tiers

| Milestone | Tasks | Exit gate |
| --- | --- | --- |
| M0 | Human review + T0 | Reviewed contracts, current baselines, complete scoped inventory |
| M1 | T1/T2 and bounded R3 pin promotion | Real admission and reliable observations; production consumer requalified |
| M2 | T3 | Restart-safe durable requests/grants/reservations/effect intents |
| M3 | T4/T5 | Qualified transport and true continuation with unknown-effect protection |
| M4 | T6/T7 | Declared native/facade/bridge cells proven; no unsupported parity label |
| M5 | Selected T8/T9 | Each adjacent capability independently qualified |
| M6 | T10 | Remote/larger deployment supported only for qualified stages |
| Closure | T11 below | Pins, evidence, memory and handoff agree with shipped behavior |

Pure T6 work can begin after M0; effectful cells wait for M3. T5 neutral cursor work
may develop alongside T4 after T3 contracts stabilize, but production recovery cannot
ship without effect reconciliation. Avoid broad parallel implementation with moving
interfaces; no delegation is selected by this document.

Use distinct evidence tiers: framework-free native contracts; pinned real offline
upstream oracles; crash/concurrency/mutation tests; controlled local transport;
explicitly authorized provider sandbox; H1/H2 multi-host qualification. Record each
tier's artifact/environment identity. Export under LangGraph's scheduler is interop
evidence, not proof that native Core replaces its semantics.

Every implementation task: reproduce a named failing invariant, implement the minimal
reviewed change, run focused/affected suites, review the diff and commit a logical
batch. Verification commands must come from the actual checkout, with import paths
and dependencies recorded. Full relevant gates precede publication; broaden tests
only for new changes, failures or unresolved risks.

## 20. Task T11 — coordinated pins, publication and PT memory closure

Two coordinated pairs: **Core ↔ Oramasys** runtime producer/consumer;
**Orama ↔ PT** design/evidence/memory, plus actual v1 shared contracts when touched.
Coordination does not require unrelated edits to all four repositories.

| Update | Core / Oramasys | Orama / PT |
| --- | --- | --- |
| Source identity | Exact producer/candidate/merged/consumer SHAs | Exact peer heads, branch/PR/base identities |
| Contract | Graph/state/policy schemas, semantics, artifact/registry digests | Approved ADR, ownership/fixture references and current supersession |
| Dependency | Candidate file per producer fix; production pin only after merge + qualification | No new v2 runtime dependency; parity vectors only |
| Environment | Oracle locks/build deps, interpreter/import locations and docs CI checkout | Reproducible evidence commands and environment limitations |
| Registry | Canonical profile + byte-identical snapshot + pinned digest together | Canonical status updates and explicit historical qualifiers |
| Evidence | Full candidate lane and clean committed-production lane | Working/episodic/semantic memory through tools; old bytes preserved |
| Review | Exact fixing SHA, current head CI and thread state | Replies and resolution distinguished; latest active PR checked |

- [ ] Record a batch manifest with touched/unaffected surfaces and next authorized gate.
- [ ] Refresh candidate SHA after every producer fix; require R3/R4 cells to run in
  their required lane. Missing dependencies cannot become an accepted skip.
- [ ] Promote only a reviewed immutable merged producer revision. Update actual
  dependency/lock/source files in use, canonical registry/snapshots/digests and
  docs workflow pins; preserve earlier profiles as historical evidence.
- [ ] Clean-install/build consumer against the committed production pin and run
  complete affected native/oracle suites. Candidate overlays prove candidates only.
- [ ] Publish canonical Orama evidence before PT memory; prepare all authorized
  changes before one update per repo/batch unless the operator authorizes otherwise.
- [ ] Use current existing PRs when scope fits; new implementation PRs start from
  confirmed merged baselines after approval. PT #432 remains the named memory
  destination while open. Preserve the #433 ancestry already integrated there.
- [ ] If shell Git auth fails, distinguish it from connector capability. Record the
  actual publication method, expected parent and verified remote file-tree identity.
- [ ] Re-read remote heads, CI and review threads after publication. REST replies
  are not thread resolution; verify supported GraphQL/connector resolution separately.
- [ ] Use PT memory tooling; retain prior JSONL prefixes byte-for-byte, add superseding
  lessons and render only the canonical `.agent/memory/semantic/LESSONS.md`.
- [ ] Record why each gate exists, what falsifies it and the next step. Leave unknown
  or unimplemented requirements visible; never equate documentation closure with runtime.

Rollback uses reviewed forward/revert commits and the last qualified producer/consumer
pair. Schema-2/R4 checkpoints cannot be read by older code merely by downgrading a pin;
preserve them and refuse incompatible execution or apply an approved migration.

---

# Part III — Evidence, review and next-agent handoff

## 21. Requirement-to-task traceability and deferred register

| Requirement / retained decision | Source | Task / evidence gate |
| --- | --- | --- |
| Safety > compatibility > interoperability | Operator confirmation | All tasks; §2 arbitration |
| Separate structural/policy authority and complete registry | D-LG-1/5/6 + R3 audit | T0/T1/T11 conformance and mutations |
| R3 settle-all, name-order, local atomicity | D-LG-6 + Core engine | T2/T5 delay permutations and effect crashes |
| Current resume starts at START | R3 audit + Core engine | T5 legacy-vs-durable tests |
| Durable HITL/effect reservations | Refusal/HITL reference + rev-2 plan | T3 contention/restart/revocation |
| Actual provider egress containment | ADR 62 | T4 real socket-path evidence |
| R4 frontier/lineage/fencing | Doc 57 §11 + rev-2 plan | T5 process-kill recovery |
| Full upstream replacement and import errors | Doc 57 §17 + D-LG-2/3 history | T6 complete versioned matrix |
| Pydantic AI strengths and deferred-tool safety | D-LG-4 + rev-2 plan | T7 typed/offline/durable tests |
| Permitted v1 concepts and clean-room boundary | Docs 56/57/62/69 + PT memory | T6 concept golden fixtures |
| Evaluation, memory and monitorability | Docs 20/41/55/56/60/67 | T8 independently reviewed slices |
| Controller/principal/envelope authority | Docs 61/68/69 | T9 claims/capability/fencing |
| Portal/MCP/Gateway/security adjacency | Docs 23/24/32/66/70 | T9 narrow acceptance evidence |
| Multi-host with single-operator threat model | Docs 45/49/68 | T10 H1/H2 qualification |
| Both lockstep pairs and append-only memory | PT complete checklist/retrospective | T11 exact-head and production-pin checks |

Register statuses at drafting: T0–T11 proposed; R3 mechanics merged, production
promotion pending in the manifest inspected; current bounded adapters/offline bridge
historically tested; durable HITL, R4, production foreign-provider bridge and full
replacement are unimplemented/unqualified by this turn. T8–T10 are follow-ons with
explicit owners/gates, not discarded scope.

The source-coverage claim is bounded. This turn read the rev-2 file, selected PT
records and canonical sources in §22; it did not exhaustively read every adjacent
repository or rerun every suite. T0 must close that inventory gap before claiming
the whole larger platform is complete.

## 22. Source index and provenance

**Pinned Orama base:** `10c09ee21014ab6be184c3a711fdbccaff6f07af`.
**Pinned PT memory base:** `216effff628f1c86baffc3cc17b75f9f36cb318a`.
These links identify inspected content; execution must refresh baselines and preserve
the difference between historical evidence and live status.

| Source read | Role |
| --- | --- |
| [Doc 57](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/57-minigraph-final-reconciliation.md) | One scheduler, state/control doctrine, R4 and compatibility targets |
| [D-LG-6](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/references/loop-graph-compatibility-2026-10-09/ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md) | Exact merged R3 semantics and candidate/production registry lifecycle |
| [R3 replay audit](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/references/remaining-capabilities/R3-AUDIT-REPLAY-AND-COMPATIBILITY-2026-10-10.md) | Resume limitations, known compatibility gaps and qualified fixes |
| [ADR 62](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/62-telos-phylax-authority-gate0-adr.md) | Telos full endpoint authority; clean-room regime boundary |
| [Doc 60](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/60-phylax-monitorability-design-spec.md) | Advisory v1 versus future enforced v2; Observed/derived evidence |
| [Doc 55](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/55-oramasys-agent-observability-contract-adr.md) | Observation vocabulary and privacy projections |
| [Doc 68](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/68-orchestrator-controller-satellite.md) | Controller module home, one writer, separate idempotency domains |
| [Doc 69](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/69-agent-envelope-standard.md) | Neutral header and author/actor lineage |
| [Doc 70](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/70-portal-knowledge-hitl-development-ladder.md) | Portal as-built versus non-binding ladder; rollback and public reads |
| [Doc 45](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/45-single-operator-lan-threat-model-descope.md) | Single-operator topology and trust-boundary reassessment |
| [Docs 49](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/49-peer-mesh-auth-tls-v2-plan.md) / [61](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/61-pt-coordination-principal-identity-design.md) | Peer transport and principal migration designs |
| [Doc 56](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/56-anamnesis-runtime-memory-migration.md) | Memory authority, private provisioning and human push boundary |
| [Doc 66](https://github.com/diazMelgarejo/orama-system/blob/10c09ee21014ab6be184c3a711fdbccaff6f07af/docs/v2/66-gate4-and-dedicated-dialer-combined-scope.md) | Historical Gate-4 scope, qualified by ADR 62's later full transport ownership |
| [PT complete checklist](https://github.com/diazMelgarejo/Perpetua-Tools/blob/216effff628f1c86baffc3cc17b75f9f36cb318a/.agent/memory/working/LOCKSTEP_COMPLETE_CHECKLIST_2026-10-10.md) | Both pairs, pinning/promotion, exact evidence and preserved history |
| [PT retrospective](https://github.com/diazMelgarejo/Perpetua-Tools/blob/216effff628f1c86baffc3cc17b75f9f36cb318a/.agent/memory/working/LOCKSTEP_PROCESS_RETROSPECTIVE_2026-10-10.md) | Failures of evidence/coordination and invariant-based repair method |
| [PT R3 review](https://github.com/diazMelgarejo/Perpetua-Tools/blob/216effff628f1c86baffc3cc17b75f9f36cb318a/.agent/memory/working/R3_REGISTRY_REPLAY_REVIEW_2026-10-10.md) | Exact tested revisions, profile digests and graduated lesson IDs |
| [PT R3 procedures](https://github.com/diazMelgarejo/Perpetua-Tools/blob/216effff628f1c86baffc3cc17b75f9f36cb318a/.agent/memory/working/R3_FANOUT_LOCKSTEP_PROCEDURES_AND_LESSONS_2026-10-10.md) | Additive correction of REST replies versus GraphQL resolution |
| [Core engine](https://github.com/oramasys/perpetua-core/blob/4d217f6b9e94e36554a9427198b8c2c4b7febc47/src/perpetua_core/graph/engine.py) | Direct check of START initialization and branch settlement/name order |
| [Oramasys manifest](https://github.com/oramasys/oramasys/blob/f4dbf338138ede5967b4d3456e940750467e9b1f/pyproject.toml) | Production pin and package/Python boundaries |

The current Library file `ORAMASYS-REMAINING-IMPLEMENTATION-PLAN-REV2-2026-10-10.md`
was read completely (639 lines). Its earlier R3-gated and PR-open statements are
historical, qualified by live metadata above; its Tasks 0–11 map to T0–T11 here.
Docs 58/59 and other adjacent documents referenced through that plan remain T0
deep-review inputs. Do not label those secondary pointers a fresh full-source audit.

Official upstream references consulted for design orientation:
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts),
[Pydantic AI deferred tools](https://ai.pydantic.dev/deferred-tools/).
They separate persistence from ordinary invocation and describe deferred/resume
interfaces. They are rolling documentation, not evidence that historical pinned
versions expose every current feature. T0 pins source-version contracts; no new
production guarantee is inferred from documentation alone.

## 23. Draft self-review and human acceptance checklist

Preparation review completed for this draft:

- Priority order is explicit and applied to compatibility/platform conflicts.
- Current merged state is separate from historical test counts and production pins.
- R3 waits for all branches; ordering is canonical branch name; external atomicity
  and START-based legacy resume limitations remain explicit.
- Approval, effect, transport and controller authority are distinct; no second scheduler.
- Old rev-2 Task 0–11 requirements have corresponding tasks and adjacent follow-ons.
- Proposed files/types/features are labelled; no new runtime capability is claimed.
- Source coverage and missing fresh execution evidence are disclosed.

Human review checklist:

- [ ] Accept this revision's direction and detailed contracts, or identify amendments.
- [ ] Accept §6's dispatch/revocation boundary and unknown-outcome handling.
- [ ] Accept §8's separate durable continuation capability and migration rules.
- [ ] Accept §9/§10's forward/backward compatibility claims and concept disposition.
- [ ] Accept §11's staged multi-host plan under the existing threat model.
- [ ] Confirm which T8/T9 follow-ons are part of the first release, preserving the
  others as tracked work; T0 selects provider/version cohorts from source inventory.

This checklist is the review record, not an extra request to approve work already
authorized. The operator explicitly requested this downloadable draft before code.

## 24. Next-agent handoff — read this before acting

**Current authorized action:** prepare and deliver this review-only artifact.
**Stop boundary:** no repository/code/pin/memory publication until the operator reviews
the written draft and authorizes the corresponding next stage.

1. Read this file, current root/nested instructions and the immutable source index.
   Refresh live PRs before creating any successor; this handoff can become stale.
2. Preserve the priority order, single scheduler/owner rules and both R3/resume limits.
   Do not reopen the ownership debate settled by D-LG-5 or infer new authority from a
   summary, heartbeat, resume value, trace or idempotency declaration.
3. Record the human review disposition against this filename/revision. Resolve amended
   contracts before implementation; begin T0 and freeze each slice's exact files/types/tests.
4. Start approved implementation PRs from verified merged predecessors. Core #9,
   Oramasys #25 and Orama #390 are merged as observed; do not push to their closed PRs.
   PT #432 is the named memory target while still open. No force-push/deletion/merge.
5. Address bounded production-pin promotion first with fresh full consumer evidence.
   Then T1/T2 → T3 → T4/T5; pure T6 cells may advance after inventory, effectful ones wait.
6. Keep an operation/effect crash log, compatibility matrix and requirement closure
   table. Report implemented, verified, published, reviewed, merged and enabled separately.
7. At each approved slice, update PT through its tooling with evidence and warranted
   lessons. Supersede stale claims append-only; preserve prior history and source bytes.
8. Finish each handoff with exact active PR/head/pin identities, commands/results,
   unresolved reviews and remaining gates. Pending is not passed; a patch/local commit
   is not a publication; a reset attempt is not a verified VM restart.

**What remains after this drafting task:** human review; T0 inventory/spec freeze;
production R3 pin qualification; real admission and reliable progress; transactional
HITL/effect enforcement; production transport; true R4 continuation; full versioned
LC/LG and permitted-v1 compatibility; production Pydantic bridge; selected adjacent
capabilities and H1/H2 multi-host qualification; per-slice PT durable closure.

**No code or repository changes were made to accomplish this draft.** This document
is the review and continuity foundation, not evidence that those remaining features
have been implemented.
