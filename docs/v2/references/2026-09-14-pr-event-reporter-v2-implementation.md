# PR event reporter v2 — implementation and acceptance plan

> Execute with the executing-plans workflow, one verified task at a time.
> User-approved scope here is the design package; no runtime is shipped by this PR.

**Goal:** Move routine reporting off shared PR-body replacement while retaining
durable evidence, replay identity and accountable recovery.

**Architecture:** One durable Orama broker owns a SQLite outbox; a protected
Git branch stores immutable events; GitHub issue comments carry verified pointers.
Use the [specification](2026-09-14-pr-event-reporter-v2-production-plan.md) and
[contracts](2026-09-14-pr-event-reporter-v2-contracts.md) together. They supersede
the original outline's unresolved choices and exactly-one-comment wording.

**Technology:** Python 3.11+, stdlib sqlite3/hashlib/json, the successor's pinned
HTTP client, existing Telos and Phylax ports. New Redis, replicated SQLite and
autonomous PR-body fallback are outside this design.

## Scope and dependency order

All `src/orama/reporting/` and reporter `tests/` paths below are PLANNED paths
in `oramasys/oramasys`, not claims that those modules exist in legacy Orama.
Resolve/import pinned policy ports at Gate 0; never implement parallel policy
engines here. Record their versions and behavior-vector results in the receipt.

`Gate 0 → T1 → T2 → T3 → T4 → T5 → T6 → T7`. Each task adds failing behavioral
tests first, implements the smallest complete contract, runs that task's tests
and relevant prior tests, then records evidence in its review comment.
Tests use fake GitHub transports and real temporary SQLite/Git stores; production
claims additionally require the controlled GitHub sandbox proof in T7.

## Gate 0 — deployment capability proof (repository operator + policy owners)

- Provision a test repository and protected `report-evidence-v1` branch.
- Establish a separate trusted verifier allowed to inspect and certify proposed
  commits before publication. A publisher cannot set its own required success.
- Configure required preservation checks bound to that verifier app, no
  publisher bypass, no force/delete, restricted writes and private visibility.
  Require direct checked ref advancement; a required-PR-only rule is incompatible
  with this protocol unless the implementation is explicitly redesigned.
- Prove valid insertion succeeds; rewrite, removal, mode change, forged check,
  unavailable verifier and wrong actor fail. Verify the target GitHub plan/rules
  actually support this configuration. Failure blocks rollout; no silent fallback.
- Pin Telos/Phylax ports, authorize the exact host/endpoints and test rejection
  vectors. Resolve broker host, off-host backup operator and restore credentials.
- Receipt fields: repository numeric ID, branch, rule/check/app IDs, policy
  versions, test commit IDs/results, observer identity and observation time.

## T1 — contracts and stable preparation (reporting maintainer)

Create `src/orama/reporting/contracts.py` and `tests/test_reporting_contracts.py`.
Define typed frozen `ReportRequest`/`ReportEvent`/`EvidenceReceipt`/`PointerReceipt`
and explicit outcomes `Conflict`, `Blocked` and `Uncertain`.
Implement strict schema, canonical UTF-8 encoding, hash verification and limits.

Acceptance: R3/R4/R5/R7. Cases C01–C06: newline/Unicode byte preservation;
duplicate-key/NaN/type/version rejection; oversize rejection before dispatch;
forged Summary/marker rejection; changed content under one operation key conflicts;
redaction occurs before freezing, policy changes never alter a frozen record.

## T2 — transactional ledger and crash recovery (reporting maintainer)

Create `src/orama/reporting/ledger.py` and `tests/test_reporting_ledger.py`.
Implement preparation uniqueness, immutable BLOB storage, revision claims, leases,
attempt/observation transactions and schema migrations. Entry points:

```python
def prepare(request: ReportRequest) -> ReportEvent: ...
def claim(event_id: str, worker_id: str) -> Claim | None: ...
def begin_attempt(claim: Claim, phase: Phase) -> Attempt: ...
def observe(attempt: Attempt, result: Observation) -> Transition: ...
```

These are interfaces, not executable test evidence. `Claim` carries event ID,
worker identity, revision and lease expiry; every mutation rechecks ownership.
Use the state table in the contracts, including cancellation tombstones.

Acceptance: R2/R5/R8. Cases L01–L08: concurrent identical prepare returns one
event; conflicting prepare fails; crash before/after each commit/send boundary;
stale worker update rejected; lease expiry retains uncertainty; disk full
prevents I/O; migration/restore preserves frozen bytes; lost client resumes the
same operation key. A negative read after timeout never releases a legacy grant.

## T3 — evidence store and preservation verifier (reporting + repository operators)

Create `src/orama/reporting/evidence_store.py`, separately deploy the trusted
verifier, and create `tests/test_reporting_evidence_store.py`.
Implement proposed-parent validation, non-force advancement, exact readback,
existing-record adoption and concurrent-head rebuilding. Receipt contains
observed head/commit/tree/blob and record digest; never accept API acknowledgement
as the receipt. The verifier runs from a separately protected artifact/version,
not executable code in a submitted report branch.

Acceptance: R4/R6/R7. Cases E01–E09: sibling writers both survive; ordinary
fast-forward rewrite rejected; mode/delete/rename rejected; candidate without
check blocked; acknowledged but wrong blob rejected; timeout-after-success
adopted; late earlier write and retry converge; branch movement reverified;
public/private mismatch or unknown protection health prevents writes.

## T4 — additive pointer transport (reporting maintainer)

Create `src/orama/reporting/github_pointer.py` and
`tests/test_reporting_pointer.py`. Use typed API responses and the exact marker
contract. List every page, fetch candidates, validate actor/provenance and
persist comment IDs. Only create new comments; no PATCH or DELETE operations.

Acceptance: R1/R3/R9. Cases P01–P07: human body edit remains byte-identical
through reporting; crash after comment creation converges; duplicate comments
render one logical event; forged marker cannot complete intent; incomplete
pagination cannot assert absence; stale/edited/deleted pointer reconciles without
rewriting evidence; permissions/rate limits preserve pending state.

## T5 — service, reader and caller integration (Orama + consumer maintainers)

Create `src/orama/reporting/service.py`, `reader.py`, `cli.py` and thin
`scripts/report-pr-event.py`; test in `tests/test_reporting_service.py`.
Compose ports and recovery scheduler. CLI accepts persisted operation key,
destination and UTF-8 payload file; machine output includes event ID, state and
verified receipts. Nonzero/Uncertain is never formatted as successful publication.
Reader distinguishes verified storage from semantic claims and legacy prose.

Create a checked migration manifest at `docs/reporting/consumer-inventory.json`.
Each row records producer/consumer path, owner, source revision, replacement,
compatibility fixture and rollout status. No unmapped active caller may pass P4.

| Existing surface (legacy paths) | Required disposition / owner |
| --- | --- |
| `scripts/cursor/append-pr-body.sh`, `pr-body-grant-lib.py`, grant helper | Supervised legacy only; Cursor integration owner. |
| `scripts/cursor/hooks/before-shell-pr-body-guard.sh`, `pr-body-guard-core.py`, submit reminder | Preserve body guard; teach reporting command; Cursor integration owner. |
| `.cursor/rules/append-only-pr-body.mdc`, `pr-body-comment-only.mdc`, `common-git-workflow.mdc` | Point autonomous reporting at events; skills/rules owner. |
| `bin/orama-system/skills/cursor-pr-body/` and git reference cards | Update canonical source then prescribed sync; skills owner. |
| `.github/workflows/pr-body-guard.yml` and `scripts/git/verify-pr-body-not-clobbered.sh` | Retain human-metadata protection; CI owner. |
| PT mirrors and `orchestrator/contracts.py` task/result consumers | Separate PT change after reader readiness; PT owner. |
| Dashboards, summaries, external workers found by discovery | Register owner and compatibility test before enabling that caller. |

Run `rg -n 'append-pr-body|gh pr edit|report-pr-event|follow.up|pr.*body'` across
both repositories and deployed caller configuration. Classify hits as active,
test, authority, mirror or historical; record exclusions with reasons.
This table seeds discovery, not an assertion that external clients were audited.

Acceptance: R1/R3/R7/R9/R10. Cases S01–S05: end-to-end event receipt; unchanged
body under parallel external edit; no network on admission failure; duplicate/
foreign pointers render safely; each inventoried consumer passes compatibility.

## T6 — operations and legacy recovery (on-call + reporting maintainer)

Create `docs/reporting/runbook.md` and `tests/test_reporting_recovery.py`.
Specify backup/restore, lease fencing, rate limits, alert routing, redacted
diagnostics, configuration refresh and operator transitions from NeedsOperator.
Implement flag shutdown that stops claims but retains in-flight reconciliation.
Test SQLite backup with active transactions and an interrupted schema upgrade.

Acceptance: R2/R3/R8/R10. Cases O01–O07: sandbox disappears; broker disk lost
and backup restored; stale publisher fenced; uncertain event older than 24 hours
retained; changed/missing original Summary snapshot refuses legacy recovery;
base-equal read does not prove no in-flight write; flag rollback never invokes
body replacement. Store recovery transcripts without payloads or credentials.

## T7 — production acceptance (operator, reviewer and consumer owners)

Run the focused suites from T1–T6, then the full successor suite. Repeat the
Gate 0 enforcement proof on the target configuration, not just a mock server.
Run two independent workers with injected timeout/crash at every dispatch edge.
Load baseline: 1,000 16-KiB events, ten concurrent requests, one repository.
Record p50/p95 completion time, storage growth, lock contention and API throttling;
ratify capacity before broader rollout, without weakening preservation gates.

Exercise P0–P5, seven-day/100-event canary, backup restore and rollback.
The acceptance artifact maps R1–R10 to the case IDs above, actual test command,
source SHA, outcome and reviewer. “Test added”, “API returned SHA” and a
successful reread before write are not independent remote-integrity evidence.

## Residual limits and completion definition

No atomic body CAS, exactly-once comment API, administrator-proof WORM or
reconstruction of lost original prose is promised. Those are limits, not gaps
to paper over with extra retries. The protocol removes routine body writes,
makes uncertainty durable and binds recovery to verifiable evidence.

This design package is complete when links, ownership, contracts, failure
transitions and requirement mappings agree. Production completion is a separate
reviewed delivery requiring T1–T7 evidence. Until then, maintain supervised v1
guards and additive manual reporting; do not advertise an unbuilt event service.
