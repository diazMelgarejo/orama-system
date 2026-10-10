# P0 through T2 implementation plan - revision 3

> For agentic workers: use `superpowers:executing-plans` task by task. No delegation,
> publication or merge is implied by this document. Review the contract refinements
> below before implementing T1/T2.

**Status:** operator-directed planning synthesis; implementation qualification and human merge gates remain separate.
**Date:** 2026-10-10 UTC. AFRP: Type C | Level Practitioner | Mode 2.
**Goal:** finish P0 safely, then implement enforceable admission, bounded observation
delivery, cancellation and restart-safe accounting without a second scheduler.
**Architecture:** qualify immutable producer/consumer pairs before consumer activation.
One neutral Core dispatch gate composes Oramasys admission, run control, delivery health
and atomic accounting. Core supplies mechanics; Oramasys owns policy and accounting. Durable
accounting records consumption, not graph position or permission to resume.
**Tech stack:** Python 3.11/3.12, pytest, asyncio, schema-versioned JSON, SQLite.
**Specs:** [parent](PLAN-R4-EXECUTION.md), [admission](CONTRACT-ARTIFACT-ADMISSION.md),
[continuation](CONTRACT-DURABLE-CONTINUATION.md), [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
**Supersedes:** the execution instructions in
[revision 2](P0-THROUGH-T2-EXECUTION-PLAN-REV2-2026-10-10.md), the
[first P0-T2 plan](P0-THROUGH-T2-EXECUTION-PLAN-2026-10-10.md) and the release order in
[the first P0 plan](PLAN-P0-CORE-PIN-PROMOTION.md). Those files remain historical inputs.

## 1. Review disposition and corrected assumptions

The supplied architectural review was read in full. Its substantive gaps are adopted;
its severity labels and example code are not treated as verified implementation facts.

| Finding | Disposition | Execution correction |
| --- | --- | --- |
| Qualify only after Orama merges | Accept sequencing risk | Qualify both PR heads before either promotion; immutable SHA and digest receipts |
| Failed promotion irreversibly corrupts main | Reject permanence claim | Existing parent permits reviewed forward/revert commits; retain the last qualified pair |
| Move or fast-forward a signed candidate tag | Reject | Never move a tag; use full candidate and merge SHAs; requalify changed content |
| `pip check` is insufficient | Accept | Add non-editable install, symbol/construction smoke and PEP 610 source verification |
| Import `oramasys`, assert Core `__commit__` | Correct example | Distribution is `oramasys`, module is `orama`; inspected Core exports no `__commit__` |
| Durable budgets conflict with no continuation | Clarify distinct capabilities | Recommend durable accounting only, consistent with parent T2; cursor recovery stays T5 |
| START replay necessarily double-charges | Correct | Actual repeated work must be charged; never reuse a crashed run to replay START automatically |
| PT ledger implies a shared v1/v2 authority | Reject runtime coupling | Reuse verified design lessons, not imports, database, keyspace or a v1 service dependency |
| Callable reference text proves code safety | Accept enforcement gap | Resolve only trusted pre-bound code registry entries; never load artifact-supplied modules |
| Lease triggers lack execution boundaries | Accept | Guard actual node/reducer execution and pre-commit boundaries; test parallel branches |
| Missing admission service prevents all tests | Accept fixture need, reject inevitability | Inject deterministic test-only providers; production missing authority still refuses |
| Slow observer can stall execution | Accept risk, reject guaranteed deadlock | Existing ordered observer awaits listeners; bounded critical acknowledgement and isolated telemetry |
| Cancellation can undo arbitrary effects | Reject | Cooperative bounded cancellation; preserve uncertain attempts; T3/T4 effect recovery remains gated |
| Matrix needs a source of truth | Accept | One six-cell manifest; exact expected-cell set, explicit not-applicable cases |

Additional verified P0 defect: the retained pre-R3 registry digest is currently
`ab0bcf96099e2bf81ce62138032456d87d0bbf966cf2a2c7bccbab8ea96a6417`, but the original
Orama baseline at `bccc1528260e86a854c946d61a3f273aa52b742d` is
`c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f`.
Equivalent JSON is not byte-preservation. Restore the original blob bytes in both
repositories; do not reserialize the archive or erase the earlier commit.

### Revision-3 verification and disposition

The preceding defect is preserved as the REV2 finding. It has since been repaired
on the existing draft branches. The uploaded [REV3 synthesis](P0-THROUGH-T2-REV3-SYNTHESIS-INPUT.md),
preserved unchanged with SHA-256 `f950d6cf81bf3010b755f3590d0a7b4414979bbde6f4760e826a71a65b97ae4c`,
is an additional review input; this plan corrects its stale main-only claims with staged
evidence. The user's instruction authorizes this documentation synthesis and publication;
the attachment itself does not authorize runtime promotion or a merge.

| Freshly read location (2026-10-10 UTC) | SHA | Meaning |
| --- | --- | --- |
| Orama main / merged #393 | `f5a9e005fb7a980f00ef9d9ff6081b79d86b2fb3` | Canonical R3 registry already promoted; archived pre-R3 bytes need forward repair |
| Orama open draft #394, before this revision | `d711ce6425f332c24ea04ba34da9dbdefa0768b1` | Archive restored; repair continues on this branch |
| Oramasys main | `f4dbf338138ede5967b4d3456e940750467e9b1f` | Old consumer pair; main-to-main drift is real |
| Oramasys open draft #26 | `566409be45257561ba0fdbc76f94a718af7aaa5c` | Production pin and byte-identical fixtures already staged |
| Core main | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Current P0 target; unified gate is not implemented by this planning change |

| Uploaded suggestion | Disposition and security refinement |
| --- | --- |
| Reconcile drift before qualification | Adopt; record separate main/staged receipts, preserve promoted canonical bytes, restore only the corrupted archive unless evidence warrants a separately reviewed rollback |
| P0 not started because consumer main is old | Correct; #26 already stages the changes, while qualification is still incomplete |
| One gate and one durable writer | Adopt a neutral seam; Oramasys remains the policy owner, with atomic hold reservation and commit fencing |
| Lease max-steps becomes a ledger hold | Adopt one accounting source with run/lease scopes; retain Core's independent structural graph bound |
| Trusted callable registry and hermetic fakes | Adopt; reject artifact imports, production fake selection and unauthenticated authority |
| Shielded timeout and forced cancellation | Adopt bounded waiting only; track tasks, fence late results, and require isolation for enforceable termination |
| WAL/FULL, append-only reconciliation | Adopt with single-writer fencing, restrictive database/WAL/SHM permissions and typed idempotent adjustments |

**Registry decision:** retain the intended R3 canonical SHA-256
`fbde64f2c3b2bec62f703137f5fddb480d502440b9e1b229c15292816b52f7e2`.
Restore the pre-R3 archive SHA-256 `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f`.
Do not replace the promoted canonical file with the old schema-1 baseline merely to
make old consumer main appear matched. Staged policy-r3 and core-r3 digests are
`4972754f7ceb0ad3e908f6583533fec3c59a807732ac86c3ee967df33e29e36f` and
`e270493a7c924871e50fcf384c792a6922a375976127e26214f69b7c89ba9437`.
All four staged Orama/Oramasys file pairs match byte-for-byte. Historical source
versions remain preserved in git; metadata corrections are not original historical bytes.

## 2. Global constraints and review focus

- One Core scheduler: `CompiledGraph._run()`. No traversal in adapters or observers.
- Orama owns registry bytes; Oramasys owns byte-identical fixtures and runtime composition.
- Phylax, Agate and Telos retain their actual authority; absent authority never defaults allow.
- v1 PT and Orama stay independent of v2; v2 runtime does not import PT accounting.
- Core production target: `4d217f6b9e94e36554a9427198b8c2c4b7febc47`.
- No force push, tag movement, branch deletion, historical-memory rewrite or agent merge.
- No T3 effect grants, T4 provider transport, T5 continuation, remote workers or exactly-once claim.
- Preserve R3 settle-all joins, branch-name fold order and atomic local region merges.

Five failure classes must have proving tests: source/fixture drift (P0), expired or
revoked admission in fan-out (T1), non-cooperative sinks (T2-A), crash between hold and
settlement (T2-B), and cancellation racing with local commit (T2-B).

## 3. P0 - two-phase qualification, then promotion

### P0.0 Reconcile drift and preserve the last qualified pair

- [ ] Re-read all three main heads and both repair heads before each qualification.
  Record a drift receipt binding full SHAs, file blob IDs, SHA-256 digests and status.
- [ ] Compare main-to-main separately from staged-to-staged parity. A staged match
  does not certify main, and main drift does not undo already-staged implementation.
- [ ] Continue forward archive repair on #394 and consumer promotion on #26; no
  replacement PR, force update, branch deletion or canonical schema downgrade.
- [ ] Find the last pair with actual qualification receipts. If none proves safe,
  report qualification unknown and refuse new runtime activation; do not invent a
  "last qualified" claim from old pins or matching trees alone.

### P0.1 Repair and freeze the candidate

**Files:** Orama `docs/v2/references/loop-graph-compatibility-2026-10-09/ownership-registry*.json`;
Oramasys `src/tests/fixtures/graph-ownership-registry*.json`,
`src/tests/test_ownership_registry.py`, `requirements/compatibility-manifest.json` (new).
**Interface:** manifest version 1 contains exactly six cells: three profiles times
Python 3.11 and 3.12. Each cell names Core SHA, registry filename/digest, required tests
and explicit not-applicable capabilities. A separate evidence receipt binds manifest
digest, tested producer/consumer SHAs, lock digest, interpreter and actual cell outcomes.
Do not put a file's containing commit SHA inside that same file.

- [ ] Add failing byte-preservation assertion against the original blob digest above.
- [ ] Restore original pre-R3 bytes in both repos, retain all earlier commits, rerun parity.
- [ ] Add manifest tests rejecting missing/duplicate cells, wrong pins, wrong profile,
  mismatched canonical bytes, unknown selector and missing required checkout in CI.
- [ ] Generate or validate the workflow matrix from this manifest; avoid a second pin table.
- [ ] Preserve the original historical profiles in their original git revisions; metadata
  corrections are separately attributed, never represented as unchanged original blobs.
- [ ] Commit on existing open #394/#26 branches; inspect full blobs, batch logical
  commits locally and publish once per changed branch after all validation.

| Profile | Core SHA | Meaning |
| --- | --- | --- |
| production | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Promoted baseline, never candidate auto-selection |
| policy-r3 | `04759a50c748444ff97136ea95c1e1289eac3a1a` | Historical schema-1 qualification |
| core-r3 | `34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68` | Historical schema-2 candidate qualification |

### P0.2 Clean installations and real qualification

**Files:** Oramasys `pyproject.toml`, both existing CI workflows,
`scripts/verify_production_install.py` (new), `src/tests/test_production_install.py` (new),
`src/tests/test_perpetua_graph_spec.py`, existing offline oracle suites.
**Interface:** `verify_production_install(expected_core_sha: str) -> None` rejects
editable Core, missing/mismatched PEP 610 `direct_url.json` VCS identity, wrong symbols,
and inability to construct/execute a minimal graph. It supplements `pip check`.

- [ ] Write failing verifier tests: correct package metadata but absent runtime symbols;
  wrong source commit; editable Core; working-directory source shadowing installed wheel.
- [ ] Build/install the Oramasys wheel non-editably from the committed production manifest
  into a new environment with no Core overlay and `--no-cache-dir`; run from outside
  the checkout. Import `orama`, `perpetua_core`, `GraphSpec`, `ReducerSpec`, `JoinSpec`;
  construct and invoke a minimal graph. Record resolved module paths and Core VCS identity.
- [ ] Run `python -m pip check`, native tests with the existing coverage gate, authority
  scan, compile smoke, and a packaged-resource smoke. Verify offline oracles separately
  in the pinned oracle environment; an overlay never substitutes for installation proof.
- [ ] Run all six exact-head cells; reject missing required tests and unexpected skips.
  Schema-1 lacks R3 deliberately: record those named tests as not applicable, not passes.
- [ ] Run canonical-checkout parity in every cell. Record results rather than infer them
  from one interpreter or a previously mutated virtual environment.

### P0.3 Acyclic release protocol and rollback

The existing Orama #394 head is the immutable repair candidate; no extra release
branch, moving tag or staged-main schema is needed. #393 already changed producer
main. Qualify the forward archive repair and consumer together before merging #394;
consumer activation stays blocked until the final merged pair has fresh receipts.

| State | Required evidence | Allowed next action |
| --- | --- | --- |
| STAGED | Candidate Orama SHA/digests + consumer PR SHA/manifest | Run full paired qualification; do not claim active production |
| QUALIFIED | Six-cell receipts + wheel smoke + resolved reviews | Operator may merge canonical Orama PR |
| CANONICAL | Actual Orama merge SHA; relevant blobs/digests unchanged | Update consumer pin to merge SHA and rerun affected/full required CI |
| ACTIVATED | Operator-merged consumer SHA + green post-merge verification | Publish dated Orama closure, then PT append-only memory |
| SUPERSEDED | Failure/change receipt, previous qualified pair | Forward correction or reviewed revert; repeat qualification |

- [ ] Open/update the consumer PR before the canonical merge, using the exact candidate
  SHA in CI. Reuse open Orama #394 and Oramasys #26; #393 is historical and merged.
- [ ] Record exact tested SHAs and relevant registry digests; branch names are not evidence.
- [ ] Operator merges only after both heads qualify. If merge changes registry bytes,
  consumers or locks, invalidate the receipt and requalify; tree identity alone is not
  a substitute for environment evidence.
- [ ] Refresh consumer workflow pin to the actual canonical merge SHA, review and rerun CI;
  operator then merges consumer. Cross-repo commits are not an atomic transaction.
- [ ] During the merge interval, consumer main remains pinned to the old qualified pair;
  never discover a new baseline from Orama main dynamically.
- [ ] On pre-merge failure, keep old main active. On post-canonical consumer failure,
  stop activation and forward-fix or revert the canonical promotion by a reviewed commit.
  On post-consumer failure, restore the prior qualified consumer pair by reviewed commit.
  Preserve candidate profiles and all failure receipts in either case.
- [ ] Publish Orama evidence before PT memory, through native memory tooling. Preserve T0.
  PR-body remediation is comment-only without the repository's operator-grant procedure.

**P0 exit:** matched canonical revision, production fixture/digest and committed Core pin;
all required fresh-install and six-cell evidence at exact heads; reviewed/merged/active
statuses separately reported. Local test totals from the earlier session are supporting
evidence only, not proof that these remaining gates passed.

## 4. T1 - executable identity and admission lifecycle

**Files proposed:** Oramasys `src/orama/graph/admission.py`,
`src/orama/graph/execution_guard.py`, `src/tests/test_artifact_admission.py`,
`src/tests/test_execution_guard.py`, and `src/tests/fixtures/admission/`.
Existing equivalents must be reused if the T0 seam inventory finds them.

**Interfaces proposed for freeze:**

- `CallableRef`: opaque validated registry key, not a Python import expression.
  Trusted application construction binds it to a callable and reviewed artifact digest;
  freeze that mapping for the invocation. Unknown/changed bindings refuse. A finite enum
  is optional for a fixed built-in set, not a universal limit on custom nodes/reducers.
- `AdmissionDecision`: discriminated allow/refuse/pending, decision ID, binding digest,
  owner/evidence references, issued/expiry UTC, max authorized steps and authority epoch.
- `admit_artifact(binding, context) -> AdmissionDecision`: actual owner adapters.
- `ExecutionGuard.before_dispatch(...) -> DispatchDecision` and
  `before_commit(...) -> CommitDecision` from REV2 are consolidated into
  `DispatchGate.before_dispatch(...) -> GateDecision` and
  `before_commit(...) -> GateDecision`. Core owns the neutral protocol; Oramasys
  supplies its implementation. This is not an edge selector or second scheduler.

### Unified gate contract (T1 foundation; T2 inputs extend it)

- Fixed order: authority/lease, stop state, delivery health, then budget. Results are
  `allow`, `refuse(reason)`, or `stop`; terminal outcomes remain Oramasys-owned:
  completed, interrupted, cancelled, refused, budget, unknown. Reason codes retain
  cause detail; a refusal never disguises unknown in-flight effects as safe.
- `before_dispatch` atomically reserves a unique attempt hold and marks dispatch
  eligibility under the current run/lease epoch. No separate lease step counter.
  The ledger enforces the stricter run and lease bounds without duplicate charging;
  Core's existing graph `max_steps` remains a structural safety limit.
- Fan-out reserves each attempted branch against shared scoped limits; reducers
  also receive attempt identities. Define charge units and rollback of unstarted
  reservations before freezing the contract. No unaccounted parallel dispatch.
- `before_commit` validates current authority, stop, delivery and the existing hold
  without reserving again. Validate and publish a local delta within one serialized
  commit boundary; no intervening await. A stale epoch or token cannot commit.
  Persist uncertainty when a crash occurs between local commit and settlement.
- Authenticate owner decisions and define epoch freshness/expiry and clock policies;
  SQLite cannot make remote revocation atomic. State that observation window explicitly.
- T1 needs step accounting and a single-writer/fencing foundation before it can claim
  atomic lease bounds. T2-B extends that store to time/cost/attempt accounting;
  do not defer the foundation while claiming a working unified gate.
- A dedicated Core review covers nodes, routers/custom joins where executable,
  reducers, each fan-out branch and pre-commit. Preserve settle-all semantics and
  one scheduler. Qualify the new immutable Core revision before Oramasys adopts it.

- [ ] Freeze canonical encodings, clock/expiry policy, provider interfaces and the neutral
  Core guard seam at T0. Missing Phylax/Agate capabilities require an owner contract first.
- [ ] Write tests for `os:system`, dotted lookup, aliases and unknown keys: reject without
  importing or executing them. Static AST checks cover artifact resolvers, not every
  legitimate import or `getattr` in the application. This is not a sandbox for trusted code.
- [ ] Use contract acceptance tests for changed code, stale policy, non-Observed evidence,
  missing hardware/principal and unavailable enforcement services.
- [ ] Test expiry/revocation between admission and node dispatch, before reducer execution,
  before commit, and concurrently across fan-out branches. Reserve step allowances
  atomically; use injected UTC/monotonic clocks so expiry tests do not sleep.
- [ ] Guard actual execution boundaries in the one scheduler through a reviewed neutral
  protocol. If today's seam cannot guard every branch, amend Core before claiming T1.
  Lease revocation stops future work/commit; it cannot undo a completed external effect.
- [ ] Inject deterministic `FakeAdmissionProvider` fixtures explicitly in tests. Production
  never auto-selects a fake on network/service failure; disconnected production refuses.
- [ ] Keep fake providers in test-only packages excluded from the wheel. Production
  startup validates provider identity; lint/package tests reject fake imports/selection.
  Monkeypatch artifact-resolution `importlib.import_module` to fail and prove artifact
  strings never reach dynamic imports; do not forbid legitimate trusted bootstrap imports.
- [ ] Implement minimal records/adapters/guards; run focused failures-to-green, native,
  fan-out and resolver-mutation tests; review the vertical slice before commit/publication.

**T1 exit:** actual authenticated owner decisions and bound code identity; every execution
boundary enforces expiry/current authority without copied policy or traversal authority.

## 5. T2-A - bounded neutral observation delivery

**Files:** Core `src/perpetua_core/graph/plugins/observer.py`,
`src/perpetua_core/graph/engine.py` only for a reviewed neutral seam;
`src/tests/graph/test_observer_delivery.py` (proposed). Oramasys terminal interpretation
stays outside Core. The existing observer calls listeners sequentially and awaits them.

**Proposed defaults for contract review:** telemetry queue capacity 1024 per sink plus
8 MiB total detached queued-payload bound; critical acknowledgement deadline 500 ms;
shutdown grace 1000 ms. These are configurable application-delivery limits, not safety
evidence or guaranteed suitability for every deployment. Reject zero/unbounded values.

- [ ] Define ordered event identities `(run_id, sequence)`, detached payloads, delivery
  outcomes and dropped-count/gap ranges. Ordering is per sink; no global atomic ack claim.
- [ ] Non-critical sinks consume isolated bounded FIFO queues; enqueue is non-blocking.
  On overflow drop newest telemetry, increment externally readable counters, record gaps.
  Counters do not depend on the failing sink. Redact projections and bound payload sizes.
- [ ] Critical sinks acknowledge explicit persistence boundaries, not every streamed token.
  Never drop critical records. Deadline expiry, queue exhaustion or failed acknowledgement
  raises neutral `CriticalDeliveryFailed`; do not advance to the next dispatch. Oramasys
  maps it to terminal `unknown` plus a delivery-uncertain reason, not a new Core policy enum.
- [ ] Write tests for slow telemetry not delaying nodes, mutation isolation, ordered sinks,
  critical timeout before next dispatch, oversized payloads, queue overflow, duplicate
  subscription, and disconnect/cleanup. Include cancellation-suppressing async sinks.
- [ ] Async callbacks must not perform blocking I/O on the scheduler loop. Reject unsupported
  blocking sinks; use an isolated adapter for them. Cancelling a thread/coroutine does not
  prove it stopped: retain tracked tasks, open a bounded circuit and forbid late authority.
  Do not use `wait_for` as a hard-deadline claim for a cancellation-suppressing callback.
- [ ] For async critical delivery, retain task references and use `asyncio.wait` with
  a bounded timeout. Shield ownership where needed; timeout ends waiting, not work.
  Revoke task/run fencing authority on abandonment and refuse its late acknowledgement.
  Test pending task bounds, shutdown, and cancellation suppression. Blocking callbacks
  require process isolation or a declared supported adapter; threads cannot be killed safely.
- [ ] Preserve R3 settle-all semantics and one drain; no observer schedules nodes. Closing
  a paused iterator prevents later dispatch but is not an in-flight effect rollback.
- [ ] Run Core observation/graph/region suites and paired Oramasys failure mapping tests.
  Critical delivery is a bounded execution precondition, not unconditional non-blocking.

**T2-A exit:** bounded memory and failure latency under the declared cooperative/isolated
sink contract; telemetry gaps visible; critical loss stops further dispatch without hangs.

## 6. T2-B - single-writer accounting and cooperative stop

**Recommended scope:** durable accounting, distinct from T5 durable continuation. This
preserves the parent requirement that restart does not reset consumption. An in-memory-only
alternative would need an explicit parent requirement amendment; it is not silently adopted.

**Files proposed:** Oramasys `src/orama/graph/budget_ledger.py`,
`src/orama/graph/run_control.py`, `src/tests/test_budget_ledger.py`,
`src/tests/test_run_control.py`, `src/tests/test_budget_crash_recovery.py`.
**Interfaces for freeze:** `reserve_attempt(run_id, attempt_id, limits) -> BudgetHold`,
`mark_started(hold_id) -> DispatchMarker`, `settle_attempt(hold_id, receipt) -> Settlement`,
`recover_accounting(run_id) -> RecoveryDecision`, `request_stop(run_id) -> StopReceipt`.

- [ ] One H0 SQLite accounting writer, unique run/attempt keys, integer units, immutable
  events and transactional projections. Store attempts/holds/settlements, not cursor,
  frontier, checkpoint state or permission to replay. Schema migrations run twice safely.
- [ ] Use WAL with `synchronous=FULL`, validated local filesystem support, a private
  directory (0700) and database/WAL/SHM permissions (0600). Serialize writes and
  fence stale writers after restart; a SQLite write lock alone does not establish
  single-writer ownership. Append events; projections may update transactionally.
- [ ] Freeze separate step, elapsed-time, cost and effect-attempt units. Persist absolute
  expiry and elapsed charges; use monotonic clocks within a process and the approved UTC
  regression policy after restart. Test clock rollback, expiry, missing usage and invalid
  negative receipts. Effect-attempt accounting supplies no effect authorization.
- [ ] Write subprocess crash tests before reserve, after hold, after start marker, after
  outcome and before settlement. A hold without a start marker may be released only
  after the single writer proves no dispatch can race that release;
  marker without reliable receipt stays unknown and consumes the conservative hold.
  Observations do not create charges; authoritative pre-dispatch/settlement calls do.
- [ ] Nested calls share the parent accounting context. Real retry execution consumes
  fresh allowances; duplicated settlement for the same attempt is idempotent. Concurrent
  holds cannot overdraw. Restart recovers accounting and refuses replay of unfinished runs.
- [ ] A fresh START traversal requires explicit new-run admission and limits; it is not
  continuation or a reset of the old run. No automatic retry-after-crash. T3/T4 must later
  bind real effects/usage receipts before production provider-cost enforcement is claimed.
- [ ] Set stop-requested before future dispatch; signal cooperative cancellation to active
  nodes. Proposed grace is 1000 ms, then cancel/abort through supported capabilities.
  Track remaining tasks, bound abandonment and block additional work when circuit opens.
- [ ] Persist stop state before signalling; after the 1000 ms grace, use supported
  cancel/abort capabilities only. No Python coroutine/thread hard-stop claim. Isolated
  process termination may prove local termination but cannot roll back remote effects.
  Open the circuit and increment the fence epoch before discarding late results.
- [ ] Reconcile unknown holds only through an authenticated operator adjustment event:
  unique adjustment ID, hold ID, expected epoch, evidence, reason and integer settlement
  or release units. Reject duplicate/conflicting/oversized adjustments. Release only
  after proving dispatch/late commits cannot race it; uncertain effects require explicit
  evidence and disposition. Preserve the original unknown event and account for prior
  adjustments transactionally; never edit/delete ledger history or silently replenish budgets.
- [ ] Test before-dispatch, partial-stream, between-result-and-commit, nested/fan-out and
  uncooperative cancellation races. Cleanup in `finally`; local staged deltas may be
  discarded, but charges/markers and possible external effects are never erased.
- [ ] Accounting outage refuses new dispatch. Deadline/critical-delivery failure requests
  stop and records `unknown` if unfinished work cannot be proven terminated. A cancel
  request is not a confirmed cancelled outcome or rollback proof.
- [ ] Run focused tests, real subprocess recovery, production-profile compatibility and
  combined immutable-head Core/Oramasys qualification; publish canonical evidence first.

**T2 exit:** admission/stop/budget holds fence the next actual dispatch; terminal evidence
distinguishes completed, interrupted, cancelled, refused, budget and unknown. Restart-safe
charges are proven independently of graph resume. No provider exactly-once claim.

## 7. Immediate sequence and release runbook

1. Freeze this revision's unified gate, accounting units, fencing and delivery contracts.
2. Capture P0.0 drift evidence; complete the P0 manifest/install verification.
3. Publish paired P0 PRs for qualification before canonical promotion; reuse open branches.
4. Complete P0.3, then finish the scoped T0 contract freeze before T1/T2 code.
5. Implement the Core gate and T1 step-ledger foundation together; then T2-A delivery
   and T2-B accounting/stop extensions in dependency order with named
   failing tests, green regressions, one logical commit per task, and human merge gates.

| Failure | State and operator action |
| --- | --- |
| Any required P0 cell fails | Candidate unqualified; retain last active pair; fix then rerun |
| Registry bytes change after qualification | Receipt invalid; pin new immutable SHA and requalify |
| Admission expires or owner service disappears | Refuse next dispatch/commit; stop in-flight work within its contract |
| Telemetry overflows | Visible drop/gap counters; critical records never use drop policy |
| Critical sink hangs | Bounded failure, stop dispatch, retain uncertainty; no infinite retry |
| Accounting store unavailable/corrupt | Refuse work; preserve store and receipts; validated restore/reconciliation |
| Crash or cancellation leaves started attempt | Unknown consumption, no blind replay, preserve hold/marker |
| Unknown hold needs disposition | Authenticated append-only adjustment, fenced against late dispatch/commit |

## 8. Assumptions, review gates and lessons

- These defaults (1024 events, 8 MiB total queued payload, 500 ms acknowledgement,
  1000 ms grace) are starting configuration, not proven universal safety bounds.
  Count the aggregate payload across sinks; bound individual and in-flight payloads too.
- The ledger is an Oramasys local authority for accounting, not a second policy service
  or a Core scheduler. Admission still derives from authenticated Phylax/Agate decisions.
- Operator direction approves this synthesis and publication. Freeze revised executable
  contracts and review Core's seam before T1/T2 implementation; qualification receipts
  and human merges remain required. No PT runtime coupling, T3/T4/T5 expansion or replay.
- Preserve prior plans and the earlier handoff with dated supersession links. Lesson:
  compare main and staged states explicitly, preserve source bytes independently of
  semantic corrections, and distinguish bounded waiting from proven termination.
- Crystallization evidence is this disposition plus validated complete files. PT memory
  graduation follows canonical qualification evidence through native append-only tooling.

M1 requires merged and qualified P0/T1/T2, not merely this document. T3 effects, T4
transport and T5 cursor continuation remain disabled. This revision changes plans only;
it does not certify local commits as published, reviewed, merged or enabled.
