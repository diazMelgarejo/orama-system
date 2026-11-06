# Master closure, implementation and handoff plan

Status: scope decisions D1–D3 ratified by the user on 2026-11-06 UTC.
Local preparation and commits are authorized. Publication
is held until the user confirms the existing PRs have merged.
**2026-11-06 update:** the user confirmed the merges and released the push
hold for one PR per affected repository; see the
[C0 record](closure/c0-merge-reconciliation-2026-11-06.md).

## Outcome and source authority

One closure register replaces competing active checklists for this work. Earlier
plans remain evidence; their historical text is preserved. This register routes
to their contracts rather than copying implementations or inventing approval.

Canonical home: `orama-system/docs/v2/MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md`.
PT and Oramasys keep short handoff pointers with repository-specific entrypoints.
They must not maintain independent copies of this register.

Read together:

- [Current architecture reconciliation](architecture-status-2026-11-06.md).
- [Controller design](68-orchestrator-controller-satellite.md) and
  [agent envelopes](69-agent-envelope-standard.md).
- [Operator provisioning ADR](71-operator-provisioning-and-autonomous-tier-adr.md),
  [implementation plan](72-task6-operator-provisioning-and-autonomous-tier-plan.md),
  and [lost-run design](74-lost-run-takeover-entrypoint-design.md).
- PT's `docs/next/2026-08-23-coordination-consolidation-part3-plan.md`,
  July consolidation plans, phase-0 master plan and November 2–5 weekly receipt.
- Oramasys's `docs/release12-postmerge-qualification-2026-11-04.md`,
  `docs/revocation-capacity-handoff-2026-11-03.md`,
  `docs/serving-activation-runbook.md` and loaded-deployment-identity ADR.
- Original architecture review dated November 6: findings are claims to verify
  against current sources; its own coverage limits remain applicable.

Ownership: Core structures; Oramasys composes; Telos owns endpoint authority;
Phylax owns principal/capability authority; Agate owns hardware placement.
PT remains the v1 runtime owner. Orama holds design records and the ownership
registry; the capability schema lives in `docs/schemas`.

## Resume baseline and publication barrier

Prepared on existing PR tips: Orama #475 `6f5112b9`, Oramasys #93 `b952dc69`,
PT #480 `256f97bc`. Full identities are recorded by the local Git parents.
These are candidate tips, not assumptions about the eventual merge SHAs.

- [x] User confirms which PRs merged. User confirmed 2026-11-06: Orama #475,
  Oramasys #93 and #94, PT #480.
- [x] Verify actual merged mains and compare the changed paths against candidate
  trees; account explicitly for squash merges, concurrent edits and omitted content.
  All were merge commits whose trees equal their PR heads; see the
  [C0 record](closure/c0-merge-reconciliation-2026-11-06.md#branch-base-reverification).
  No fetch is claimed: read-only GitHub main identities matched available local
  objects. Reverification confirms the exact recorded merges in the isolated
  lane baselines, including Orama `006c226702b8c6bb265718fe5e0196db2d6e06fe`.
  Before clearing any later closure branch, verify its actual base against the
  recorded merge and current remote main, using tree/content reconciliation at
  known rewrite boundaries. A checked comparison is not clearance for a stale
  local `main` ref or a different branch base.
- [x] Reapply only a verified missing delta from these local plan commits onto
  isolated branches based on merged main; preserve old local tips. No missing
  delta was found, so nothing was reapplied.
- [ ] Recheck open PR inventory: reuse one appropriate PR or open at most one
  per affected repository. Refresh descriptions for the final scope.
  Inventory rechecked 2026-11-06 (C0 record); opening the PR and refreshing its
  description remain with the integrator.
- [x] Publish only after the user releases the current push hold. Push hold
  released by the user 2026-11-06 for one PR per repository.

Do not judge rewritten legacy branches from ahead/behind counts. Use the
repository's content/tree comparison protocol. Do not amend or force-push the
existing signed/session commits to alter verification badges.

## Ratified scope decisions

| ID | Decision | Ratified resolution | Current state |
| --- | --- | --- | --- |
| D1 | Part 3 automation authority | Automatic stale-claim release belongs to the v2 Controller only, under explicit expiry and fencing rules. PT remains manual. | Ratified 2026-11-06 |
| D2 | Legacy caller compatibility | Retain compatibility shims; decide removal separately after caller migration. | Ratified 2026-11-06 |
| D3 | Deployment evidence target | Require both POSIX and native Windows qualification before any promotion. Work can run in parallel; neither substitutes for the other. | Ratified 2026-11-06 |

Decision provenance: the user selected automatic release with expiry/fencing
for v2 only and PT manual, retained shims, and both platforms before promotion.
This ratifies implementation scope. Actual release qualification, generation
approval and activation retain their separately evidenced gates. The push hold
and merge barrier remain in effect.

## Part 3 review and revised scope

### Additional closure decisions confirmed on 2026-11-06

The operator directly confirmed the six J1 recommendations after the
GossipBus announcement in rows 6308 and 6309, topic
`OPERATOR_RATIFICATION_ALL_SIX_DECISIONS_AND_CLOSURE_APPROVAL_20261106`.
This direct confirmation, not the agent announcement alone, is the authority
for the following scope. D1-D3 above retain their original meanings.

| J1 ID | Ratified scope | Evidence still required |
| --- | --- | --- |
| CL-1 | Fresh capability-time check after verification and deadline enforcement under the SQLite write lock | Preserve expiry/refusal regressions; approval is not deployment evidence |
| CL-2 | Detected absent or changing signing-key trust refuses the current operation, including prewarm, warm lookup and refresh | No retry into allow in the same operation; preserve real-signature regressions |
| CL-3 | C6 expected workload: up to 256 events, separate refresh every 15 seconds, eight senders at five sends/second; send p95 at most 50 ms; zero fail-open | Physical target-filesystem and dual-host qualification remain open; the full owner specification retains its additional metrics |
| CL-4 | Export sanitized derived views only; raw coordination history remains node-local | Source-database protection, topology scans and item-level delivery evidence |
| CL-5 | macOS primary POSIX host and Windows 11 secondary peer; serving remains off, grant-serving flag unset and library default `governed=False` | Actual host/runtime receipts and separate activation gates |
| CL-6 | Paired doc 30/PT pointers; no Doc 69 retrofit of legacy Core modules; strict D1 separation | Canonical generation and downstream parity checks; PT remains manual |

Implemented integration heads accepted by the operator: Orama `9ecdf955`,
PT `ec88e63c`, and Oramasys `c2f4a14`. A subsequent operator instruction permits
K1-K3 remediation, local rehearsal and one final push per affected repository.
No agent may infer merge, deployment, serving activation or completed host
qualification from ratification. C3d uses operator-only human review under the
[exact-head procedure](closure/c3d-operator-review-procedure-2026-11-06.md);
a second human is not required. Fresh interactive GitHub authentication is
performed by the operator, not an agent, and does not by itself prove review.
All K1-K3 fixes precede final CI and exact-head acceptance; C6 runs last.

Cross-repository CI pairs differently named review branches through
`config/docs-pointer-peers.json`: PR number to immutable PT commit. An explicit
partner checkout must fail closed, never fall back to main on failure. Other
PRs retain the existing same-branch/main lookup, and main always checks PT main.
After PT lands, rerun the main parity gate; a paired-PR pass does not establish
that the downstream main already contains the pointer updates. Preserve the
ratified review/landing order Orama #477, PT #481, then Oramasys #95, with no
deployment between the paired documentation merges.

The August draft is superseded in the following implementation details:

1. `orchestrator/coordination/heartbeat.py` does not exist in the inspected PT
   tree. `_heartbeat_cleanup` is in `liveness.py`; it delegates to
   `cleanup_stale_claims` and releases claims. Inspect that owner's atomic checks
   and failure behavior when characterizing compatibility. PT remains manual;
   do not schedule this cleanup or implement the draft's
   `heartbeat_cleanup(bus, stale_threshold_sec=...)` call as an assumed API.
2. Staleness alone is insufficient evidence that work can safely be reassigned.
   Test late heartbeats, partitioned workers, owner changes and uncertain effects.
   D1 requires v2 expiry and fencing checks in the authoritative claim transaction.
3. The v2 maintenance worker must be opt-in, have one owner per intended database scope, bounded
   work per sweep, explicit start/status/stop behavior, graceful cancellation and
   no import-time or install-time autostart. Its state comes from the Controller;
   a PT database resolver is not the v2 authority.
4. Replace the proposed path/name/hash identifier with a random opaque identifier
   and a protected local mapping if one is needed. Neither branch/worktree names
   nor a public bare hash of a predictable path provides the intended privacy.
5. A ten-worker race can include contention, retries and eventual losers. Assert
   exactly one committed claim; validate the documented outcome vocabulary rather
   than requiring a fixed distribution of nine outcomes across timing schedules.
6. A mock replication bridge proves bounded simulation behavior. Label live LAN,
   crash and multi-host evidence separately. Test duplicate/reordered events and
   the reorder buffer's real capacity/refusal contract before inventing N=1000.
7. A repository search inventories known callers, not every external installation.
   Characterize CLI compatibility before delegation and retain shims per D2.

The v2 job-claim Controller remains a separate protocol and implementation. Existing
execution run leases do not establish job-claim-controller completion.

## Deduplicated execution register

Each row is one deliverable with one owner and one closure decision. Mark an item
implemented, verified, reviewed, qualified and activated separately where applicable.

| ID | Deliverable and owner | Depends on | Acceptance evidence |
| --- | --- | --- | --- |
| C0 | Merge-content and source reconciliation — integrator | User merge notice | Exact main revisions, path comparisons, PR inventory, no unexplained omission |
| C1 | Complete remaining documentation findings — Orama/PT/Oramasys owners | C0 | Every review finding has a code/source-backed fixed, superseded, historical, rejected or blocked disposition |
| C2 | Manual v1 compatibility characterization and v2 claim contract — PT/Oramasys | D1, D2, C0 | Existing PT cleanup and callers documented; v2 expiry, fencing, refusal and recovery rules specified against doc 68 |
| C2a | Controller SQLite state and claim/idempotency implementation — Oramasys | C2 protocol freeze and Telos/Phylax contract review | Reviewed migrations; atomic claim, completion/release/failure transitions; same-key replay and changed-key rejection; persisted version/authority checks |
| C3 | Automatic expiry/release worker — Oramasys v2 Controller | C2a | Atomic expiry/claim-version checks; fencing rejects old workers; bounded sweep; late renewal/partition safety; clean restart; uncertain effects retained; controller closure also requires C3a–C3d |
| C3a | Controller Telos/Phylax adapters — Oramasys | C3 | Unauthorized, expired and revoked callers refuse; no gossip or topology authorization; deny-path integration tests |
| C3b | Transactional controller outbox — Oramasys | C3a | State/outbox atomicity; restart durability; duplicate/reordered delivery cannot mutate claim authority |
| C3c | Controller invariant and isolated-worker conformance — Oramasys | C3b | Doc 68 sections 10/10.1 covered, including IC-1–IC-29; source mismatch, completion, timeout, retry, revocation, restart and redaction evidence |
| C3d | Controller delivery closure — maintainer/reviewer | C3c | Accepted security review, legacy-job disposition, rollback and operational runbook under doc 68 section 9 |
| C4 | Portable identity and topology hygiene — PT | C2 | Random IDs and protected mapping; disposition of historical gossip/private-path records; sanitized episodic/portable projections; restart, collision and export scans |
| C5 | Concurrency and replication coverage — PT | C2 | One committed race winner; bounded lock handling; duplicate/reordered events; no dropped or falsely acknowledged events |
| C6 | Revocation availability — Oramasys | C0 | Trust-and-byte-aware snapshot validation; retirement/tamper/restart regressions; complete-send plus refresh benchmark on target filesystem |
| C7 | Loaded configuration binding — Oramasys | D3, C0 | Actual loader and consumed policy/artifact/process binding; secret exclusion; replacement/reload/refusal tests; reviewed collection contract |
| C8 | Deployment R4/R5 evidence on POSIX and native Windows — operator with tooling owner | C7, D3 | Both platform receipts: real service identity denials, installed-set and configuration evidence outside checkout, actual filesystem/platform limits |
| C9 | Independent R6 — independent reviewer | C8 | Review binds exact producer, consumer and configuration revisions and host evidence |
| C10 | R7 generation/pin decision — approved operator | C9, C8 on both platforms | New immutable generation with paired reviewed pins and recorded approval; no promotion with one platform unqualified |
| C11 | Separate R8 activation — operator | C10 | Scope, expiry, canary, monitoring, rollback and applicable activation approval record |
| C12 | Product parity and broader constellation roadmap — application/kernel owners | C0 | Capability inventory first; offline artifact/verifier parity; separately reviewed retrieval/provider, continuation and distributed-runtime increments |

C1 includes the unfinished individual reconciliation of docs 67 and 70–72,
older PT coordination plans, preserved September migration inputs and their errata,
the R1–R8 status chain, and stale ownership/pin claims. Use narrow status notes
or a current errata route for preserved historical sources. Existing formatting
debt remains explicit; do not silently exempt new content or call it verified.
Orama-scope C1 dispositions are in the
[C1 ledger](closure/c1-orama-dispositions-2026-11-06.md), which also records
where the C2 artifacts live. PR publication and implementation evidence do not
by themselves close review, host qualification or activation.

C4 covers stored data as well as new events. Inventory existing gossip records
and derived episodic views without printing private paths. Restrict or quarantine
raw legacy stores under the approved local retention/access policy; sanitize
derived portable/export views before release. Preserve tracked append-only source
bytes and use additive corrections; any sensitive-history removal requires a
separately approved incident procedure. Test synthetic legacy worktree labels
through gossip-to-memory derivation and export, ensuring names and private paths
are absent from portable views. Block export of unclassified legacy rows rather
than assuming a new producer identifier repairs historical data.

For C6, use the ratified CL-3 workload and the full owner specification; the
operator selected the Mac APFS data volume, with Windows qualification separate.
Obtain target-filesystem measurements after final CI and operator C3d acceptance
before claiming availability. For C7/C8, require
actual deployment inputs rather than guessing a
host, service manager or configuration loader. C12 is a program of bounded
follow-on slices; it is not authorization for an unreviewable kernel rewrite.

## Immediate next implementation slice after the merge barrier

1. Close C0 and produce the source/disposition ledger for C1. Do not reopen
   already merged fixes merely because a historical checkbox is empty.
2. Apply ratified D1–D3. Characterize PT's manual callers and cleanup using
   current `liveness.py`, `claims.py`, `task_queue.py`, `paths.py` and `cli.py`;
   specify the separate v2 claim contract under doc 68 before implementing C3.
3. Implement C3 in Oramasys. A release must atomically verify lease expiry and
   current claim identity/version; fence the previous worker before reassignment.
   Test renewal racing expiry, stale workers, partitions, duplicate sweeps and
   restart. Unknown external effects remain held for reconciliation. PT C4/C5
   cover privacy and tests of manual behavior without adding a maintenance daemon.
   Implement C2a before expiry work, then adapters (C3a), transactional outbox
   (C3b), isolated-worker/invariant conformance (C3c), and reviewed delivery
   closure (C3d), following doc 68 section 9. The controller cannot be declared
   complete from expiry-worker tests alone.
4. C6 can proceed independently after its contract/workload is established.
   C7–C11 proceed in dependency order with actual host evidence and owner decisions.

## Implementation and handoff contract

Each batch names exact repository/base/head SHAs, source contracts, owned paths,
observable gap, before/after behavior, relevant tests and output, known baseline
failures, unresolved decisions and rollback. Record author, actor and bounded
review separately. Test results never become operator approval.

Verification includes the existing graph-map checker and real candidate maps,
the compatibility/pin tests for workflow edits, native PT memory prefix and
rendering checks for memory edits, changed-document lint and source links.
Do not reuse a full-suite result if the tracked tree changed afterwards.

Commit batches: (1) canonical master register, (2) owner-repository routing and
draft-plan disposition. Later implementation batches follow C2/C3/C4/C5 rather
than combining daemon authority, caller removal and privacy migration in one patch.

Closure requires evidence or an explicit owner-held block for every register row.
Retain unknown effects, unsupported platforms and missing approvals as such.
No fixed calendar deadline substitutes for a missing prerequisite.
