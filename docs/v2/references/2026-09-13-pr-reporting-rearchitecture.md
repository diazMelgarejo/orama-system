# PR reporting rearchitecture: append evidence, do not replace shared prose

## Decision

Routine agent reporting MUST move off PR-body replacement. The PR body is
human-owned narrative state, not an agent transport. Automated reporting uses
append-only evidence records and a new PR comment that points to the record.
An explicitly authorized, supervised body edit remains a narrow legacy escape
hatch; it is not a mechanism from which strong concurrency or recovery
guarantees can be derived.

This is a production redesign decision, not a claim that another reread or
another test can make GitHub's unconditional PR-body update atomic.

## Why the existing helper has a hard limit

GitHub's PR-body update is full replacement and exposes no compare-and-swap
precondition for the body revision. The helper can read, back up, merge,
re-read, write, and verify. Those steps detect many stale writes, but an
external edit can still land after the last re-read and before the write. A
local lock can serialize cooperating local processes; it cannot lock a GitHub
PR against a human, another client, or another runner.

Therefore:

| Problem | Legacy body helper | New reporting path |
| --- | --- | --- |
| Shared-body lost update | Cannot be closed client-side | Avoided: automation does not write the shared body |
| Grant release with remote state unknown | Requires a durable pending/uncertain state | Reporter event is immutable before its pointer is emitted |
| Recovery after a destroyed Summary | A summary-presence heuristic is insufficient | Recovery verifies the event record and pointer, never reconstructs approval from body prose |
| Meaningful trailing bytes | Must preserve bytes in the exceptional helper | Payload is stored and hashed as an immutable UTF-8 artifact |

The append-pr-body helper guards remain worth keeping for the exceptional
human-authorized path. They are best-effort detection, not exclusivity or an
atomic precondition.

## V1 legacy-helper integrity binding

Until automated body mutation is retired, each authorized append records both
the exact base-body digest and exact merged-body digest in its durable nonce
reservation before the GitHub write. Crash reconciliation requires an existing
reservation bound to the grant's append-payload digest and requires the
freshly fetched remote body to equal the persisted merged-body digest exactly.
That comparison and the ``remote_applied`` transition occur in one
nonce-ledger transaction, and CLI reconciliation hashes the fetched body as
raw bytes so CRLF and other meaningful newline bytes are not normalized away.

It does not use a Summary heading, a follow-up substring, or any other prose
shape as evidence. A body with a forged Summary and copied follow-up is a
mismatch incident: it must neither consume the grant nor create a new
reservation. Older reservations without the two body digests cannot be
reconciled automatically and require an explicit fresh authorization.

This gives v1 safe detection and preserves a byte-exact recovery target. It
does not make a later automatic restoration safe: restoring a PR body is
another unconditional full-body replacement and retains the external race.

## Target protocol

1. Build a UTF-8 report payload and validate it locally.
2. Write one immutable evidence record before publishing any pointer. The
   record contains a schema version, repository, PR number, source head SHA,
   actor, timestamp, payload bytes/digest, and a unique event ID.
3. Verify the stored record by fetching it from its exact remote ref and
   comparing its digest. If the write acknowledgement cannot be independently
   verified, leave the event pending; do not release or reuse its idempotency
   key.
4. Create a new PR comment containing the event ID, digest, and a stable
   link. It is an additive operation and cannot replace the PR's Summary.
5. Fetch the comment and verify its ID and event/digest pointer. A failed
   verification leaves an observable pending event for reconciliation.
6. A human may curate the PR body from verified evidence, with explicit
   authorization. That curation is a separate action and never a prerequisite
   for reporting.

The implementation may use a versioned, append-only repository record or an
external immutable store. It must not use the PR body as the event log. A
comment is the notification/pointer, not the sole source of truth.

V2 promotes the v1 base/merged digest pair into the immutable event record,
alongside the record's remote identity and the pointer-comment identity.

## Required durable state machine

Prepared -> Evidence verified -> Pointer published -> Complete

At any transport ambiguity, transition to Uncertain. Uncertain retains the
event identity and may reach Complete only after exact event and pointer
reconciliation.

Uncertain is durable and non-replayable. It records enough identity to
reconcile: event ID, payload digest, expected remote record identity, expected
comment marker, and attempt metadata. It is never converted to safe to release
merely because a client did not receive a success response.

## Idempotency and reconciliation

Use repository, PR number, event ID, and payload digest as the idempotency
identity. Reconciliation must require exact equality of the event payload
digest and remote record identity. It MUST NOT infer success from a Summary
heading, a substring, or any prose that could have been replaced.

If a pointer comment exists but its record is absent or mismatched, preserve
the incident and require operator action. If the record exists but no pointer
comment does, create exactly one pointer bearing that event ID. Neither case
licenses mutation of the PR body.

## Migration plan

1. Add a report-pr-event command that writes and verifies an immutable
   evidence record, then posts a pointer comment.
2. Make autonomous and background agents use that command exclusively.
3. Change dashboards and summaries to read verified event records; do not
   parse the PR body as state.
4. Retain append-pr-body.sh only behind existing explicit human authority,
   label it best-effort, and log each use.
5. After adoption, deprecate automated body mutation. A future removal requires
   evidence that all required consumers read the event stream.

## Acceptance criteria

- A concurrent external PR-body edit cannot erase an automated report because
  the reporter does not modify the body.
- Every reported event is independently fetchable and digest-verifiable from
  its exact remote identity.
- Every ambiguous transport result remains durable and non-replayable until
  reconciliation establishes the exact event/pointer relation.
- Recovery rejects a replacement body regardless of whether it contains a
  Summary heading or a copied follow-up.
- Tests exercise the state transitions and exact remote identities, rather
  than scanning source text for error-code strings.

## 2026-09-14 production-contract completion

The outline above is retained as decision history. The
[production specification](2026-09-14-pr-event-reporter-v2-production-plan.md),
[contracts](2026-09-14-pr-event-reporter-v2-contracts.md) and
[implementation plan](2026-09-14-pr-event-reporter-v2-implementation.md) now govern
implementation and explicitly refine these earlier statements:

- Storage is a protected per-repository evidence branch with a separately trusted
  preservation verifier. Non-force advancement alone cannot prevent record edits.
- The stable caller operation key binds one frozen event in a durable broker
  ledger. A fresh event UUID or a changed digest is not a retry identity.
- “Create exactly one pointer” is replaced by at-least-once pointer attempts and
  consumer deduplication. GitHub comment creation has no event-idempotency key.
- Routine events do not depend on body snapshots. The original/merged digest
  pair and complete snapshots apply specifically to supervised legacy recovery.
- Uncertain forbids identity release and blind replay. Reconciliation may retry
  the same immutable event through the preservation protocol; legacy body
  replacement has no equivalent safe automatic retry.
- A base-equal read does not prove an earlier request cannot still complete.
  Missing snapshots require operator action, never a fabricated Summary.

This completes the v2 design, not its runtime delivery. The v1 byte claim also
requires an exact transport boundary: raw-file hashing alone does not distinguish
an API helper's presentation LF from an original trailing LF. Implementations
must remove only a documented transport byte and retain original LF/CRLF bytes;
the new event path avoids this body-transport dependency entirely.
