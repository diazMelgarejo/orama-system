# Queue Fencing and Recovery — Consolidated v1/v2 Execution Plan

> **Status note added 2026-11-12 (additive; the plan text below records its
> pre-ratification state):** the [D-0 decision record](decision-record.md)
> records operator acceptance of Q-D23, Q-TOPO, Q-D1, Q-D2, Q-68, Q-SQLITE,
> Q-AGE, Q-RET and Q-LAYOUT. Q-68b uses the two-stage retry rule (attempt 1
> original; attempt 2, the first verified retry, may return the token; attempt
> 3 and later are token-free). These
> decisions do not authorize merges, pushes, activation, C3d-base or the other
> owner-held gates.

Status: proposal for manual review. Nothing here is ratified, implemented, published or activated.
Only the two read-only audits (V1-1, V2-1) and the documentation work package (D-0) are ready to
start. On acceptance this plan replaces, as recommendations only, the 2026-11-10 authenticated
queue plan, the review of that plan, and the 2026-11-11 reconciled draft. All three stay
preserved as historical inputs.

## 1. Scope, method and what this consolidates

AFRP: Type C | Expert | Mode 2. Method: `oramasys-method` (context immersion, smallest coherent
design, remove unsupported mechanisms, failing-first slices, evidence and limits) with the
contract-migration method (`oramasys-method/references/contract-migration.md`) as the structure of
section 6. The code-graph and semantic-search tools are not available in the planning container;
targeted reads of the cited files were used. No test, host command or runtime change was run.

Proposed home, only after authorized publication: `orama-system/docs/v2/` as a subordinate work
package of the master closure register, with short pointers (not copies) in
`Perpetua-Tools/docs/next/` and in oramasys docs. This is not a competing register: every task
below maps to an existing master row.

| Input | Kept | Changed or dropped here |
| --- | --- | --- |
| Authenticated-queue plan (11-10) | Generation fencing, versioned atomic recovery, closed recovery dispositions, held uncertain effects, separate v1/v2, non-deployable intermediate commits | Per-worker sessions, signed holder proofs and encrypted proof delivery move to an optional slice A. The stray "local guidance" header paragraph is removed |
| Review of that plan (my 11-10 review) | C1–C3 and I1–I9 as gates, S2–S9 | C3 severity corrected (section 2.3). S1 (HMAC proof derivation) withdrawn: no audited facility exists to reuse |
| Reconciled plan (11-11) | F/A split, Q-decision gates, authority topology, separate private ledger, L-1 as its own task, evidence discipline, finding map | The default replay rule is reclassified from fix to optional hardening (section 2.3). L-1 gets an earlier interim step, L-1a (section 4.3) |
| Release 0–2 plan (10-25) | Default-deny capability bits, final-boundary re-verification, adversarial test list, real process death for crash qualification, one draft per repo | Used as invariants (section 8). Its D0–D4 drafts are a different stream and are neither reopened nor closed here |
| Operator qualification and baseline notes | Python 3.13.18 / SQLite 3.53.1 as the development baseline; WAL-reset fix verified first; 60 ms ruling; exact-SHA C3d acceptance | Applied as a runtime gate for the new ledgers (Q-SQLITE) and as renewed C3d scope. The memory-crystallization step is queued, not performed (task K-Q) |

## 2. Ground truth and the three design ideas

### 2.1 Verified at the time of writing

| Repository | Main | Open PRs |
| --- | --- | --- |
| Perpetua-Tools | `1020b58` | none |
| oramasys | `f33d809` | none |
| orama-system | `23059e8f` | none |
| Phylax | `2c11d15` | not checked |

The closure PRs #95, #481 and #477 are merged. The master register is at orama main `23059e8f`.

Facts checked in source this session:

- PT queue ownership is the `task_claims` table (`task_id`, `agent_id`, `claimed_at`) created in
  the same SQLite file as the gossip log through `bus.connect()`. Task state is a fold of
  replicated heartbeat events. `release_claim_with_event` conditions its DELETE on `agent_id`
  only, so a same-name restart that reclaims is indistinguishable from the original claimant.
- `cleanup_stale_queue_claims` reads the dead-agent set and the claim rows before the release
  transaction, then releases by agent name. It is called from `heartbeat_monitor.py`. PR 493
  records continuing quiescence as the interim mitigation.
- The CLI opens SQLite directly. There is no PT queue endpoint, so v1 has no process boundary.
- `/gossip/emit` accepts any `event_type` and payload under mesh authentication, and the fold
  trusts task-kind events. Replicas fold in arrival order.
- v2 `ControllerStore` serializes the claim receipt, including the raw `lease_token`, into the
  idempotency row and rebuilds it on replay. Replay still passes the transport and capability
  ports first (claim contract, idempotency section). `release` always returns the task to
  `pending`, schema version 1 has no recipient field, and `reconcile` is terminal.
- PT already has the pattern this plan should reuse: `orchestrator/dispatch_guard.py` keeps a
  private SQLite ledger under `PT_STATE_DIR`, validates ownership, permissions and symlinks,
  has no expiry, automatic release or maintenance daemon, and forbids deleting the ledger to
  retry (`docs/coordination/runtime-dispatch-guard.md`).
- `scripts/c6_runtime.py` in oramasys already refuses SQLite older than 3.51.3 and the C6 runbook
  names Python 3.13.18 / SQLite 3.53.1 as the baseline. PT has no equivalent gate.

### 2.2 The three ideas

1. **Acquisition continuity.** Every acquisition has a persistent, never-reset generation (v1) or
   the existing lease fence (v2). Every release, completion, renewal and recovery re-reads canonical
   state inside the write transaction and compares the whole acquisition and the versions, not
   the agent name. This one mechanism fixes the same-name restart, the stale worker, the cleanup
   race and recovery-versus-completion races, with no new credentials.
2. **Reuse, do not invent.** The v1 ledger follows the existing `dispatch_guard` private-state
   pattern. v2 extends the existing Controller. There is no new cryptography, no new daemon and
   no second authority.
3. **Smallest independent fix first.** The cleanup race has a narrow interim repair (L-1a) that
   needs no migration, so it lands before the ledger and is later subsumed by the authority
   boundary.

### 2.3 Two corrections made while consolidating

- **C3 in my earlier review was overstated for the current Controller.** An authorized replay
  must pass the Telos transport attestation and the Phylax capability check before the store
  returns the stored receipt. A captured request alone does not carry a channel attestation. The
  Critical rating applies to the proposed holder-proof design (an identical nonce accepted twice).
  For the current Controller it is Important defense in depth.
- **Token-free replay fails D23's own test.** D23 asks whether a mechanism's value needs an
  adversary. Removing the raw token from replay mainly protects against a stolen database or a
  hostile channel, and it makes the canonical honest failure (a lost response) cost a full lease
  TTL. So the F slice keeps authorized replay as today, and token-free delivery becomes decision
  Q-68b with the cost stated. The cross-channel replay regression test applies to both options.

## 3. Decisions required

None of these is ratified. Each names who accepts it and what it blocks. Existing rules stay
binding: D1 (PT manual; automatic release only in the v2 Controller, opt-in, fenced), D2 (retain
shims), D3 (POSIX and native Windows before promotion), D23 (see slices), IC-1–IC-29, and the
separate R6/R7/R8 and C3d gates. Network authentication, TLS and v2 Telos/Phylax admission are
not waived by D23.

**Slices.** F is honest-but-flaky correctness: fencing, versions, recovery, idempotency, private
canonical state, one writer. A is additional worker identity and hostile-worker assurance:
per-worker credentials, signed holder proofs, token-free delivery, isolation spike. F never
claims protection from a hostile same-user process. A needs its own premise record.

| Gate | Proposal | Accepted by | Blocks |
| --- | --- | --- | --- |
| Q-D23 | Ratify F's reduced guarantee and record Q1–Q3 evidence and reassessment triggers. A needs a separate premise decision | Operator | Every implementation task |
| Q-TOPO | One authority on the approved primary POSIX role, separately for v1 and v2. The other host is a client, never a replicated writer. Bindings stay in a protected local record. Outage means refusal, no fallback writer, no shared-filesystem SQLite | Operator | V1-2, V2-2 |
| Q-D1 | An explicitly started, request-serving PT queue authority is allowed. It may answer requests and drain committed outbox rows. It may not sweep, schedule, auto-transfer or auto-start | Operator | V1-2 |
| Q-D2 | Retain shim names. Approve the changed availability and handle requirements for mutations. Observe callers first, then enforce. No fallback writer after cutover | Operator | V1-4 |
| Q-68 | Amend doc 68, the claim contract, envelope and migration rules together: reserved handoff, versioned recipient fields, old-client refusal. Correct the stale "no runtime implementation" banner additively | Orama design owner and operator | V2-3, reserved recovery |
| Q-68b | Replay delivery: A keeps authorized replay returning the token (default, F). B returns the receipt without the token and holds a lost-response lease for conservative recovery (hardening, A) | Operator | V2-2 replay change |
| Q-AGE | Any maximum admission age is configurable, rationale-backed and tested under lock contention. No invented default. Without one, do not claim immediate revocation | Owner and operator | V2-2 admission profile |
| Q-RET | No automatic purge in this slice. Retain receipts, tombstones, generations and audit. Operator accepts capacity and backup policy before activation | Operator | Activation |
| Q-LAYOUT | Extend existing PT and Controller owners. New executable artifacts follow doc 46 under `src`. Any narrow exception for the legacy PT tree is explicit and approved | Operator | V1-2 packaging |
| Q-SQLITE | Both new ledgers refuse to open on SQLite below the existing `c6_runtime` gate and record the library version and source id. Python 3.13.18 / SQLite 3.53.1 is the development baseline. The fix check is run, not assumed | Operator | V1-2, V2-2 |

## 4. Design

### 4.1 v1 (Perpetua-Tools owns; Orama adapts)

- **Ledger.** A separate private database file in a protected directory, using the existing
  private-state helpers, with its own WAL/SHM handling and backups. Records: tasks with a
  persistent last generation and versions; acquisitions (claim id, generation, opaque
  incarnation reference); reservations; public receipts; private audit; transactional outbox.
  Index by task and state. Never fold the whole gossip log per operation.
- **Authority.** One service on the primary role (Q-TOPO). Gossip carries redacted post-commit
  projections only, marked non-authoritative with freshness metadata. A gossip ACK is not claim
  acceptance. A peer refreshes canonical state before mutating.
- **Claim handle.** `ClaimHandle(task_id, claim_id, generation)`. A handle proves acquisition
  continuity, not who the worker is. Renew, fail, complete and release compare the full current
  acquisition and expected versions inside `BEGIN IMMEDIATE`.
- **Recovery.** Manual and operator initiated. Closed dispositions: `hold`,
  `requeue_same_reservation`, `transfer_reservation`, `abandon`. One transaction validates
  permission, fresh clock, versions, retry and uncertainty policy, then invalidates the old
  acquisition, bumps versions and writes state, receipt, audit and outbox together. Unknown
  effects and legacy-unverified claims are held. Retry counters are preserved and no pulse is
  fabricated. A reservation is not a claim.
- **Errors.** 400 invalid, 401 missing or invalid authentication, 403 insufficient scope, 404
  authorized unknown task, 409 stale or conflicting, 503 unavailable or busy. No generic success
  on uncertainty.
- **Clock.** Sample aware time under the write lock, persist a high-water mark, and refuse
  time-sensitive authorization on backward movement until documented operator reconciliation.

### 4.2 v2 (Oramasys owns)

- Extend the existing Controller and its Telos and Phylax ports. No replacement controller.
- Reserved handoff stays release followed by a separately admitted claim. The release atomically
  establishes a versioned reservation so an unrelated principal cannot take the gap. This needs
  the Q-68 amendment. Forced takeover stays controller-only expiry and recovery.
- Replay follows Q-68b with attempt 1 original, attempt 2 first retry and attempt 3+
  token-free. Consume the token-bearing retry allowance atomically with store-side verification
  and persist it before returning the token. Concurrent retries and restart cannot reset it.
  External verifiers stay outside the write lock. Every channel still requires full admission.
  Prove the transition using concurrent retries and real process death before and after commit.
  Schema-2 cutover remains blocked on the replay-identity gate in amendment-drafts section 2.7.
- `verified_at` and any maximum age enter only through Q-AGE, checked inside the write
  transaction before idempotency or task lookup. No network verifier runs under the SQLite lock.
- `reconcile` resolution tooling is out of this slice. No operator bypass returns a `reconcile`
  task to `pending`.
- Phylax owns any holder or session verification and Telos any generic verified-channel support.
  If slice A is chosen, that is its own producer task and PR (P-H1).

### 4.3 The cleanup race: L-1 in two steps

L-1 stays a separate task with its own review.

- **L-1a (interim, PT, no migration).** The claim table and the gossip log are the same SQLite
  file today. Inside the existing `BEGIN IMMEDIATE` release, also compare the claim row's
  `claimed_at` captured by cleanup, and recheck liveness from the heartbeat events on the same
  connection. A restarted worker that reclaimed (new `claimed_at`), or that pulsed without
  reclaiming, is no longer released. Implemented as optional arguments so existing callers keep
  their signature. To be confirmed by the V1-1 audit before work starts. `claimed_at` is a
  wall-clock float, so this is a practical fence and not a generation.
- **L-1b (at protected cutover).** Once the ledger leaves the gossip file the same-file atomicity
  is gone. Protected queues then refuse legacy cleanup writes and route manual recovery through
  the authority with expected generation and versions. If liveness exists only elsewhere, refuse
  or require continuing quiescence. No false cross-database atomicity.
- Continuing quiescence from Perpetua-Tools PR 493 covers affected workers, automatic
  restarts and queue mutations throughout each operator-authorized cleanup. It stays in
  force until L-1 lands, is tested, is deployed to every relevant caller and its boundary
  is proven. This documentation authorizes no live cleanup. Do not run cleanup during audits.
  No periodic PT cleanup is introduced (D1).

## 5. Work packages (map to the master register)

Local task labels, not new register rows. The integrator appends accepted rows and keeps
proposed, implemented, tested, reviewed, qualified and activated separate.

| Task | Owner and parent row | Deliverable and acceptance | Needs |
| --- | --- | --- | --- |
| V1-1 | PT and integrator, C2/C4/C5 | Read-only audit: refresh SHAs, callers, claim writers, folds, ingress, cleanup, schema and package layout, PT docs cross-references. Old/new ledger (section 6). Known external installations listed with operator input, unknown ones marked. No schema, code, credential or claim change | none |
| V2-1 | Oramasys and integrator, C2/C3a–C3d | Read-only audit: IC-by-IC evidence map, replay and migration behavior, Telos and Phylax interfaces, Q-68 and Q-68b amendment text, C3d packet outline | none |
| D-0 | Orama design owner and operator, C1/C2 | Register rows, decision record for the section 3 gates, doc 68, claim contract and doc 61 amendments, additive banner correction, PT and oramasys pointers. One documentation PR | V1-1, V2-1 |
| L-1a | PT, C2/C5 | Interim cleanup repair (section 4.3) with the failing-first schedule below | V1-1, Q-D23, authorization to run tests |
| V1-2 | PT, C2/C4/C5 | Separate private ledger, indexed state, generations, authority boundary, canonical folds, migration and import. Forged-gossip regression first. Nondeployable | D-0 accepted gates, Q-SQLITE |
| V1-3 | PT, C2/C5 | Manual recovery, holds, reservations, all-mutation idempotency with immutable public receipts. Nondeployable until V1-4 | V1-2 |
| L-1b | PT, C2/C5 | Protected-queue cleanup refusal and routing (section 4.3) | V1-2 |
| V1-4 | PT and verified Orama callers, C2/C4/C5/C8 | Migrate every inventoried caller, shim and importer. Observe-first ledger complete. Rehearse service-down refusal, protected storage, backup, restore, rollback on both hosts | V1-3, L-1b, Q-D2 |
| C3d-base | Operator, C3d | Source-backed review of the existing Controller, legacy disposition, runbook and rollback, or a staged C3d with a base checkpoint | none |
| V2-2 | Oramasys, C2a/C3a/C3c | Missing real admission composition outside `src/orama`, replay rule per Q-68b, `verified_at` per Q-AGE, existing-store migration and old-client refusal | V2-1, Q-68, C3d-base, Q-SQLITE |
| V2-3 | Oramasys, C3/C3b/C3c | Versioned reserved release and claim, reservation expiry and refusal policy, proven expiry and outbox gaps | V2-2, Q-68 |
| V2-4 | Oramasys and operator, C3d/C7–C11 | Consumer composition, host evidence, migration and rollback, runbook, renewed exact-head C3d, then separate R4/R5, R6, R7, R8 | V2-2, V2-3 |
| V1-0 | PT and host owners, C4/C8 | Slice A only: isolation spike on POSIX and native Windows with separate identities, real denied reads and writes. Never infer hostile-worker security from same-user file modes | A premise decision |
| A-V1 | PT, new C2 child | Slice A only: scoped worker sessions and revocation, after V1-0 passes | V1-0 |
| P-H1 | Phylax and Telos, C3a child | Slice A only: holder and session proof with fresh per-transmission nonce, durable consumption, channel binding. Own design, PR, review and pin | A premise decision |
| K-Q | PT memory writers | After verification: crystallize lessons and domain-knowledge entries into the existing PT memory, reusing the existing PR and canonical writers. Read the local Gossip board first | verification |

Order: V1-1 and V2-1 in parallel, then D-0, then L-1a, then V1-2 → V1-3 → L-1b → V1-4 on the
v1 side and C3d-base → V2-2 → V2-3 → V2-4 on the v2 side. v1 and v2 share no runtime imports,
state or pins. Slice A items wait for their own premise decision.

## 6. Contract-migration ledger (persistence, contract, callers, transport, lifecycle, operations)

Required before any edit, as `contract-migration.md` prescribes. V1-1 and V2-1 complete and
verify these rows. A leaf-only patch is an incomplete migration.

### 6.1 v1: Perpetua-Tools queue

| Layer | Old contract | New contract | Owner | Proving test |
| --- | --- | --- | --- | --- |
| Persistence | `task_claims` row in the gossip database; task state folded from replicated events | Private ledger file with generations, versions, receipts, audit and outbox. One-time import with source digests; legacy claims `legacy_unverified` | PT | Fresh and existing-store migration; partial-migration crash; forged gossip emit and importer change nothing |
| Contract | `queue_*` return `bool or None` and print; identity is an agent name; release conditions on name | `ClaimHandle` plus expected versions; closed `RecoveryRequest`; error map in 4.1. Shim names and exit behavior kept until Q-D2 | PT | Per-operation contract assertions; existing manual-cleanup characterization tests keep passing |
| Callers | CLI queue commands, heartbeat cleanup call, legacy `agent_claim` cleanup, four script shims, one known Orama PowerShell caller, importers and snapshot folders | Every writer routed through the authority. Unknown external callers listed as unknown | PT and Orama | Exhaustive search ledger; one test per caller; no old binary can mutate protected state |
| Transport | Cross-host by gossip replication (`/gossip/emit`, `/gossip/tail`, LAN bridge) | Peers call the authority over the audited PT control-plane route. Gossip carries redacted projections | PT | Partition: claim refuses with 503, no second claim. Duplicate and reordered projections cannot mutate state |
| Lifecycle | Cleanup deletes by name outside the transaction; no restart fence | Generation bumps each acquisition; L-1a then L-1b; service started explicitly, no sweeps; ledger open refuses unsupported SQLite | PT | L-1 failing-first schedule; crash at every commit boundary with real process death; duplicate authority refusal |
| Operations | Quiescence rule from PR 493; no runbook for an authority | Runbook, protected backup, observe-first telemetry, tested rollback, retention debt recorded | PT and operator | Rollback rehearsal on both platforms; older binary refuses the new schema |

### 6.2 v2: Oramasys Controller

| Layer | Old contract | New contract | Owner | Proving test |
| --- | --- | --- | --- | --- |
| Persistence | Schema 1; idempotency row stores the full receipt including the raw lease token; `release` returns to `pending`; `reconcile` terminal | Versioned reservation fields (Q-68). Token handling per Q-68b. No change to lease-token digest storage in `leases` | Oramasys | Fresh and existing-store migration; old receipts handled per the chosen option |
| Contract | Six operations; envelope schema 1 with no recipient; handoff is release then claim | Reservation on release; schema version bump with old-client refusal; admission result may carry `verified_at` (Q-AGE) | Oramasys with Orama doc 68 | Envelope tests for new and old versions; old client denied; IC-1–IC-29 mapping table still complete |
| Callers | No application composition yet; `submit` has tests only | Real adapters outside `src/orama`; no other state writer | Oramasys | Caller search; existing single-writer scans stay green |
| Transport | Telos transport port and Phylax capability port, deny-all defaults | Real adapters; replay re-passes both; no holder proof unless slice A | Oramasys, Telos, Phylax | Deny paths; byte-identical captured request from another channel yields no token without full admission |
| Lifecycle | Opt-in fenced expiry worker; `max(clock, high-water)` rule | Reservation expiry and refusal policy; forced takeover controller-only | Oramasys | Reservation expiry; partition and renew race; restart; unknown effect stays `reconcile` |
| Operations | C3d open; partial implementation not composed | Renewed exact-head C3d on the final head; runbook and rollback; reconcile tooling out | Operator | Rollback rehearsal; C3d acceptance bound to exact SHAs |

## 7. Verification and evidence discipline

- Failing-first. Every defect test must fail for its intended guard (remove or mutate the guard
  where practical), then pass after the repair. Record the interpreter, SQLite version and source
  id, base, head and tested tree, command, exact summary line, skips, warnings and baseline
  failures. A test result is never operator approval. Do not reuse a full-suite result after the
  tracked tree changes. This plan contains no pre-filled test counts.
- Known baseline commands to revalidate before use: the PT coordination and queue suites named in
  the reconciled draft, and the oramasys `src/tests/orchestrator_controller` suite. Historical
  counts (57, 3,390, 3,738) are retained only with their original revisions.
- L-1 schedule, with deterministic barriers and no sleeps: cleanup captures claim A for a dead
  agent; pause; the worker restarts under the same name and takes claim B; resume cleanup. Assert
  B's row, counters and events are unchanged and cleanup reports a refused outcome. Add pulse-only,
  different-owner, contention and uncertain-effect cases.
- Gates carried from the reconciled draft, unchanged: canonical ingress and storage, fencing and
  recovery (a ten-worker race with exactly one committed winner and the documented outcome
  vocabulary, not a fixed distribution), atomicity and durability (no cross-database atomic
  commit claim), replay and secrecy, clock and admission, reservation and effects,
  compatibility and process, migration and rollback.
- Crash qualification uses real process death at each durable boundary followed by restart and
  reconciliation to the durable record, as in the Release 0–2 plan. Mocked crashes are
  development tests only.
- 100% docstring coverage on every changed Python module, class, function, method and test, with
  an enumerated numerator, denominator and tool scope.
- Markdown follows PT's lint (100-column wrap outside tables and code, no workstation paths, no
  "coordinator" as a synonym for orchestrator in public names or headings). Historical files that
  already fail lint get dated notes routed through a ledger, as in the November 6 closure.

## 8. Carried invariants from the Release 0–2 plan and the C6 qualification

- `ORAMA_GRANT_SERVING` stays unset and the `effects` capability stays deny. Queue work touches
  neither. Heartbeat and liveness are evidence, never authorization. A monitoring failure is
  never a permission.
- Where a queue transition authorizes anything effectful, the final boundary re-verifies bound
  identity, payload digest, epoch and expiry. A changed field is a different attempt. Revocation
  turns in-doubt work into `unknown`, never a silent rollback and retry.
- C6 stays on its ratified amended acceptance: scheduled p95 and successful-call p95 at or under
  60 ms, scheduled p99 at or under 250 ms, three consecutive qualifying trials preserved
  individually. This plan adds no benchmark threshold. Operator qualification means the operator
  runs or supervises the benchmark on the actual hosts and accepts the exact tested revision.
  C3d acceptance is bound to exact SHAs, so any v2 change here requires renewed acceptance on the
  final head. Login establishes account control, not independent review. R6 remains separate.
- Native Windows and POSIX qualification are both required before promotion, and neither
  substitutes for the other (D3).

## 9. Compliance matrix

Each row is a governing document and how this plan stays consistent with it. Rows citing orama
docs 47, 61, 69 and the C3d procedure rely on the reconciled draft's summaries. V1-1 and V2-1
re-verify them against the files and stop on any conflict.

| Document | Obligation | How the plan complies |
| --- | --- | --- |
| PT `CLAUDE.md` section 0 | PT is runtime and state authority for the job queue. Orama is stateless and imports from PT, never the reverse. `orchestrator` terminology | v1 authority stays in PT; Orama callers adapt. No Orama state, no reverse import |
| `docs/coordination/runtime-dispatch-guard.md` | Private state directory, no expiry, automatic release or maintenance daemon, never delete a ledger to retry | The v1 ledger reuses the pattern. Q-D1 allows a request-serving service only |
| `docs/next/2026-07-19-heartbeat-daemon-design.md` | A heartbeat daemon is design only. Problem 1 is fixed | No PT daemon or sweep. Cleanup stays operator invoked |
| `docs/coordination/manual-cleanup-characterization-2026-11-06.md` | Pins current manual behavior and shims | Characterization tests keep passing until Q-D2 changes a pinned behavior explicitly |
| `docs/coordination/portable-producer-identity-2026-11-06.md` | Opaque producer ids; no names or paths in events | Projections and receipts carry opaque ids only |
| `docs/coordination/concurrency-replication-coverage-2026-11-06.md` | No invented capacity; replicas depend on arrival order | The authoritative ledger removes arrival-order dependence; reorder-buffer contract is not changed |
| `docs/next/LOCKSTEP-REVIEW-CLOSURE-2026-11-08.md` | Private durable claim; PT owns authority, Orama adapts; repair a shared vertical contract as a pair | Section 6 is that vertical contract. Caller and authority changes land as a sequenced pair |
| `docs/next/MASTER-CLOSURE-HANDOFF-2026-11-06.md` and the master register | One register; D1–D3; C3d and R6 distinct | Subordinate work package; no new register |
| Orama D23 (doc 45) | Gate adversary-dependent mechanisms on three questions | F/A split; Q-68b and slice A gated |
| Orama doc 46 | Executable artifacts under `src` | Q-LAYOUT extends existing owners and records any exception |
| Orama docs 47, 61, 68, 69 | Local-topology invariant; principal identity; Controller; envelopes | Q-68 amends 68 and the contract together; 61 amendment for D2; no topology in artifacts |
| `contract-migration.md` | Ledger across six layers before editing; fresh and existing-store tests; caller search; rollback decision | Section 6 and section 7 |

## 10. Rollout and rollback

Per version: freeze the accepted contract and caller ledger → stop writers and workers under
continuing quiescence → protected SQLite-safe backup with manifest → choose one canonical legacy
history by operator reconciliation, never "latest peer wins" → import once with source digests and
unverified dispositions → validate invariants → select the protected authority atomically →
exclude old direct writers → start only the accepted service → synthetic canary → both-host
qualification → separate review, promotion and activation. No live migration is authorized here.

Rollback: stop new requests and workers; retain uncertain effects; drain or preserve the outbox;
protect backups; choose forward repair or an accepted compatible restore. Never revive old
tokens, generations, leases or revoked authority from an old snapshot. Older code that cannot
honor the schema must refuse. Never delete active or `reconcile` data to make rollback pass.

Publication: reuse suitable branches and PRs after rechecking inventory. Small sequential logical
PRs, at most one active appropriate PR per affected repository. Do not combine fencing, optional
identity, caller retirement and privacy migration in one patch. Preserve signed and session
commits. Reply to each inline thread with the real fixing SHA.

## 11. Not verified and owner-held

- No code, test, host command or deployed process was run or observed here.
- The L-1a feasibility (same-file atomicity and an in-transaction liveness read) was read from
  source, not executed. V1-1 confirms it.
- Orama docs 47, 61, 69 and the C3d procedure were not re-read for this plan. The Phylax open-PR
  inventory was not checked. Core, Telos and Agate were not audited for this plan.
- The local Gossip board could not be read from the planning environment. K-Q must read it first.
- Owner-held: every section 3 decision, C3d acceptance, both-platform host evidence, R6, R7 and R8.
  Windows behavior is unexercised.

## 12. Next actions

1. PT owner runs V1-1 and the oramasys owner runs V2-1, as separate read-only audits, and both
   complete the section 6 ledger rows.
2. Integrator records the outputs and the section 3 proposals in D-0. The operator accepts or
   rejects Q-D23, Q-TOPO, Q-D1, Q-D2, Q-68, Q-68b, Q-SQLITE and the scoped Q-AGE, Q-RET and
   Q-LAYOUT items.
3. After the gates clear, a fresh implementer and task reviewer per bounded task, one active
   implementer per repository, a whole-branch review at the end, and source-backed findings. Same-
   session review is labeled as such.
4. Release owner assembles the tests, migrations, rollback and POSIX and native Windows receipts;
   the operator completes exact-head C3d and the distinct R6/R7/R8 gates. Missing evidence stays
   blocked, not checked.
