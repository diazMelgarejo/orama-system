# Master closure, implementation and handoff plan

Status: consolidated execution proposal, 2026-11-06 UTC. Decisions D1–D3 await
the user's answers. Local preparation and commits are authorized. Publication
is held until the user confirms the existing PRs have merged.

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

- [ ] User confirms which PRs merged.
- [ ] Fetch actual merged mains and compare the changed paths against candidate
  trees; account explicitly for squash merges, concurrent edits and omitted content.
- [ ] Reapply only a verified missing delta from these local plan commits onto
  isolated branches based on merged main; preserve old local tips.
- [ ] Recheck open PR inventory: reuse one appropriate PR or open at most one
  per affected repository. Refresh descriptions for the final scope.
- [ ] Publish only after the user releases the current push hold.

Do not judge rewritten legacy branches from ahead/behind counts. Use the
repository's content/tree comparison protocol. Do not amend or force-push the
existing signed/session commits to alter verification badges.

## Decisions requiring user ratification

| ID | Decision | Recommended resolution | Current state |
| --- | --- | --- | --- |
| D1 | Part 3 daemon authority | PT v1 maintenance initially observes and reports; release only through reviewed existing owner semantics. Ambiguous claims remain held. | Pending user answer |
| D2 | Legacy caller compatibility | Retain forwarding shims until known callers migrate; removal requires its own later decision. | Pending user answer |
| D3 | Deployment evidence target | Linux/POSIX first, with native Windows qualification separately tracked. | Pending user answer |

These recommendations are proposals. Passing time, a local commit, or an empty
PR queue does not ratify them. The choice is recorded here before dependent
implementation begins; independent audit and consolidation can proceed.

## Part 3 review and revised scope

The August draft is superseded in the following implementation details:

1. `orchestrator/coordination/heartbeat.py` does not exist in the inspected PT
   tree. `_heartbeat_cleanup` is in `liveness.py`; it delegates to
   `cleanup_stale_claims` and releases claims. Inspect that owner's atomic checks
   and failure behavior before scheduling it. Do not implement the draft's
   `heartbeat_cleanup(bus, stale_threshold_sec=...)` call as an assumed API.
2. Staleness alone is insufficient evidence that work can safely be reassigned.
   Test late heartbeats, partitioned workers, owner changes and uncertain effects.
   The selected D1 policy must state which condition permits a release.
3. The daemon must be opt-in, have one owner per intended database scope, bounded
   work per sweep, explicit start/status/stop behavior, graceful cancellation and
   no import-time or install-time autostart. Use the existing canonical DB resolver.
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
| C2 | Part 3 contract and CLI characterization — PT | D1, D2, C0 | Existing cleanup and caller behavior documented; race, refusal and compatibility tests fail before any repair |
| C3 | Opt-in v1 maintenance daemon — PT | C2 | Bounded sweep; single ownership; late heartbeat and claim-change safety; clean stop/restart; no uncertain-effect replay |
| C4 | Portable identity and topology hygiene — PT | C2 | Random IDs; protected mapping; no names/paths in outbound events; restart and collision tests |
| C5 | Concurrency and replication coverage — PT | C2 | One committed race winner; bounded lock handling; duplicate/reordered events; no dropped or falsely acknowledged events |
| C6 | Revocation availability — Oramasys | C0 | Trust-and-byte-aware snapshot validation; retirement/tamper/restart regressions; complete-send plus refresh benchmark on target filesystem |
| C7 | Loaded configuration binding — Oramasys | D3, C0 | Actual loader and consumed policy/artifact/process binding; secret exclusion; replacement/reload/refusal tests; reviewed collection contract |
| C8 | Deployment R4/R5 evidence — operator with tooling owner | C7 | Real service identity denials; installed-set and configuration evidence outside checkout; actual filesystem/platform limits |
| C9 | Independent R6 — independent reviewer | C8 | Review binds exact producer, consumer and configuration revisions and host evidence |
| C10 | R7 generation/pin decision — approved operator | C9 | New immutable generation with paired reviewed pins and recorded approval |
| C11 | Separate R8 activation — operator | C10 | Scope, expiry, canary, monitoring, rollback and applicable activation approval record |
| C12 | Product parity and broader constellation roadmap — application/kernel owners | C0 | Capability inventory first; offline artifact/verifier parity; separately reviewed retrieval/provider, continuation and distributed-runtime increments |

C1 includes the unfinished individual reconciliation of docs 67 and 70–72,
older PT coordination plans, preserved September migration inputs and their errata,
the R1–R8 status chain, and stale ownership/pin claims. Use narrow status notes
or a current errata route for preserved historical sources. Existing formatting
debt remains explicit; do not silently exempt new content or call it verified.

For C6, choose an expected workload and latency/error budget before claiming
availability. For C7/C8, require actual deployment inputs rather than guessing a
host, service manager or configuration loader. C12 is a program of bounded
follow-on slices; it is not authorization for an unreviewable kernel rewrite.

## Immediate next implementation slice after the merge barrier

1. Close C0 and produce the source/disposition ledger for C1. Do not reopen
   already merged fixes merely because a historical checkbox is empty.
2. Record D1–D3 answers. Complete C2's caller and cleanup characterization using
   current `liveness.py`, `claims.py`, `task_queue.py`, `paths.py` and `cli.py`.
3. Implement C3–C5 in small reviewable PT batches after the policy is ratified.
   Tests must distinguish stale observation from actual release authority and
   exercise the real owner transaction rather than a mock that always succeeds.
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
