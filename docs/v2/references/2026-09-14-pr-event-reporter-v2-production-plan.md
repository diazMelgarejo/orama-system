# PR event reporter v2 — production specification

Status: approved design, implementation pending. This document and its
[contracts](2026-09-14-pr-event-reporter-v2-contracts.md) and
[implementation plan](2026-09-14-pr-event-reporter-v2-implementation.md) complete
the [original decision](2026-09-13-pr-reporting-rearchitecture.md).
Only documentation is delivered in legacy Orama by this change.

## Requirements and feasibility

| ID | Requirement | Mechanism and limit |
| --- | --- | --- |
| R1 | Preserve human PR prose | Reporters never PATCH the PR body. Local locks cannot eliminate external lost updates. |
| R2 | Retain uncertain writes | Durable intent precedes network I/O; uncertainty never releases the operation identity. |
| R3 | Reject fabricated recovery | Verify the full persisted event, remote provenance and pointer identity. No Summary heuristic. |
| R4 | Preserve bytes | Strict UTF-8, exact payload and record hashes, no newline/Unicode normalization. |
| R5 | Preserve retries | One event per durable operation key; conflicting content fails closed. |
| R6 | Preserve concurrent history | Non-force Git ref advancement plus validation that every old record is unchanged. |
| R7 | Preserve authority | Authorized publisher, Telos network policy, Phylax admission/redaction, private visibility. |
| R8 | Survive host loss | Durable broker ledger and reachable Git history; disposable clients retain no sole copy. |
| R9 | Preserve delivery truth | At-least-once pointer attempts; consumers deduplicate; no exactly-once comment promise. |
| R10 | Migrate without loss | Inventory, reader-first rollout, retained evidence, no fallback to autonomous body edits. |

R1 avoids the contested update rather than emulating unavailable body CAS.
R2 is feasible with a durable outbox and recovery worker. R3 prevents fabricated
success; lost historical prose is recoverable only from a verified complete
snapshot. Digests cannot reconstruct missing content.

## Ownership and placement

| Owner | V2 responsibility | Boundary |
| --- | --- | --- |
| `oramasys/oramasys` | `src/orama/reporting/` service, ledger, adapters, CLI and reader | Owns lifecycle and composition, not policy engines. |
| `oramasys/telos` | Authorize GitHub API endpoints and redirects using its pinned public contract | Reporter never reimplements endpoint checks. |
| `oramasys/phylax` | Admit actor/artifact, sanitize before hashing, classify evidence and audit failures | A verified stored report is still a claim, not proof all assertions inside are true. |
| Target repository | Protected `report-evidence-v1` branch and access boundary | No report of private material to a public repository. |
| PT `.agent` | V1 canonical development memory and additive lesson capture | Reporter events do not replace semantic memory or graduate themselves. |
| Future Anamnesis | Optional downstream memory ingestion under [D26](../56-anamnesis-runtime-memory-migration.md) | Not a prerequisite or a second reporter ledger. |

Runtime implementation belongs in the successor repository, not legacy
`diazMelgarejo/orama-system`. Use Python 3.11+, stdlib SQLite/JSON/hashing, the
successor's pinned HTTP stack and Telos/Phylax public adapters; no Redis or new
distributed database for the single-broker initial release.

## Storage choice and enforcement

Use one evidence branch per target repository; configuration binds numeric
repository ID, GitHub host and branch. Paths use stable IDs to survive renames:

`reports/v1/<repository_id>/pr-<number>/<event_id>.json`

An event file is a regular UTF-8 JSON blob with mode `100644`. No symlinks,
submodules, LFS pointers, deletes, renames or replacements are valid events.
The branch starts from an operator-approved bootstrap tree and retains history.

Disallow force pushes and branch deletion; restrict the publisher identity and
require `report-evidence-preservation` from a separately trusted verifier.
No publisher bypass is allowed. The verifier checks the proposed parent/head
tree pair: every old path/mode/blob survives, and additions contain only valid
new event files bound to the authenticated request's actor and admitted bytes.
Its signed receipt binds candidate commit, repository, actor, policy versions
and outcome; retain receipts in a separately administered off-host audit archive
for the event lifetime. Git commit author text alone is not provenance.
Schema, verifier and protection changes take the separate
human-reviewed configuration path. Ordinary fast-forward commits can rewrite
files, so force-push protection alone is explicitly insufficient.

Before rollout, prove those restrictions using sacrificial fixtures and store
a signed/provenance-verified configuration receipt. Provisioning and periodic
health checks require an operator connection with permission to inspect rules;
an app unable to inspect them cannot declare protection verified. Revalidate
on configuration change and at least every 15 minutes; stale/unknown protection
health pauses writes. The server-required check remains the enforcement layer.

This is application-enforced immutability within the configured trust boundary,
not WORM storage against repository administrators. Never change an old report
to correct it: append a correction with `corrects_event_id` and retain both.
No event-retention deletion or automatic cleanup is enabled by default.

## Remote commit protocol

1. Admit and sanitize the payload, then bind its frozen bytes and stable
   operation key in one ledger transaction before network I/O.
2. Read evidence ref H and inspect the deterministic event path. An existing
   matching record is reused; a different record is an integrity conflict.
3. Create blob, tree and child commit C with H as its sole parent. Validate
   local and fetched blob bytes, schema and all old path identities.
4. Obtain the trusted preservation check on C. Request ref advancement to C
   with `force=false`. A sibling concurrent commit makes this non-fast-forward;
   re-read the ref and rebuild the tree on its new head, preserving all records.
5. After any reply or timeout, fetch the ref and event at a pinned commit.
   Accept C or a verified descendant that retains the identical event blob;
   head movement is never silently ignored. Recheck the new head before reporting.
6. Persist the actual commit/tree/blob receipt. Only then publish a pointer.

A 409 is not automatically a safe failed write; reconcile it. A 422 is classified
from its response and current ref, not retried blindly. Retry budget and uncertain
states are defined in the contracts. Staging objects alone are not publication.

The [Git reference API][git-refs] supports non-force advancement. This gives the
chosen append protocol server-enforced ancestry checking; it does not turn the
unconditional [PR-body API][pulls] into a compare-and-swap operation.

## Durable host and failure model

The broker runs on a durable host. Work/sandbox clients submit requests to it
with the same operation key on retry. SQLite WAL with `synchronous=FULL` stores
frozen payload/record bytes, state, observations and attempts on local durable
disk. Network-mounted SQLite and multiple independent writers with private
ledgers are unsupported. Use one logical broker per repository scope.

A transaction claims work using a monotonically increasing revision and a
60-second renewable lease; no transaction holds a lock during network I/O.
Every write attempt is persisted before sending. On crash or lease expiry,
reconcile first. A stale worker cannot commit ledger transitions; duplicate
external comments remain possible and are handled by R9.

Disk-full, unavailable ledger, missing identity or failed admission blocks new
network writes. A migrated broker must fence the old publisher before resuming.
Back up SQLite using its consistent backup API every hour and before upgrades;
retain off-host backups for 30 days. Events remain reachable on the protected
branch, with a daily separately administered repository backup.

Broker loss loses no verified events while GitHub and the receipt archive survive;
broker-backup RPO is up to one hour. GitHub-history loss can lose up to 24 hours
against the daily backup. Target broker-only recovery within four hours, proved
by restore drill; external-provider outage duration is not guaranteed.
Loss of both ledger and Git history is disaster recovery, not transparent resume.
Freeze dispatch, restore ledger, enumerate remote
records by operation key, reconcile intents and comments, then resume. Missing
prepared payloads require operator re-submission under the original key.

## Migration and operator gates

| Phase | Entry/exit evidence |
| --- | --- |
| P0: capability proof | Verify branch restrictions, trusted check, permissions and restore drill; defaults remain off. |
| P1: readers and ledger | Inventory every producer/consumer; reader displays verified evidence separately from legacy narrative. |
| P2: shadow | Record test-cohort events; no pointer comments. Reconcile failures and test consumer reads. |
| P3: canary | Enable pointers for one approved private repository for seven days and at least 100 events. |
| P4: expand | Zero overwritten records/body writes; all R1–R10 cases pass; no unresolved integrity incidents or uncertainty older than 24 hours. |
| P5: retire legacy automation | All inventoried consumers support events; body mutation remains limited to explicit human edits. |

Legacy body-write restrictions already apply during shadow/canary. Plain additive
comments remain an allowed manual fallback with explicit unverified status; they
are never presented as completed durable events. New flags default to false:
`report_events_enabled` and `report_event_pointers_enabled`. Body-write authority
cannot be enabled by either flag.

Rollback pauses claims and pointer attempts, retains records/ledger and reader
access, and reconciles all in-flight attempts. Do not restore a stale database
over live operation or re-enable autonomous PR-body replacement.

Measure pending/uncertain counts and age, verify failures, conflicts, pointer
duplicates, unauthorized attempts, and oldest work age. Warn at 15 minutes;
escalate at 24 hours without expiring evidence or unblocking replay.

## Supervised legacy recovery

Before any exceptional body edit, keep complete original and merged snapshots
and their byte hashes. Mark possible remote dispatch durably before sending;
a failure after dispatch retains uncertainty until fresh readback. An accepted
HTTP response alone cannot prove original-body preservation.

Match exact merged bytes to confirm application. A match to base bytes is only
a current observation, not proof that an earlier request cannot still complete.
Never automatically release/retry an uncertain legacy replacement. Mismatch,
missing snapshots and old unbound reservations require human inspection.

Restoration requires current human authority and a verified original snapshot.
It is another unconditional edit with the same external race. Prefer manual
curation or adding a recovery comment; never invent a missing Summary.

## References

[git-refs]: https://docs.github.com/en/rest/git/refs#update-a-reference
[pulls]: https://docs.github.com/en/rest/pulls/pulls#update-a-pull-request

- [GitHub protection capabilities][protection]
- [Telos/Phylax authority](../62-telos-phylax-authority-gate0-adr.md)
- [Observed versus derived evidence](../60-phylax-monitorability-design-spec.md)

[protection]: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
