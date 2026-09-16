# PR event reporter v2 — contracts and recovery

Status: design contract, not shipped runtime. Subordinate to the
[production specification](2026-09-14-pr-event-reporter-v2-production-plan.md);
Task/test mapping lives in the
[implementation plan](2026-09-14-pr-event-reporter-v2-implementation.md).

## Preparation and identity

The caller supplies a stable `operation_key`, derived from its persisted job ID,
report kind and report sequence. It is 1–200 printable ASCII characters, with
no secrets. A retry MUST reuse it. Generate a UUIDv4 `event_id` exactly once,
inside the first successful preparation transaction. A new UUID per attempt
is not idempotency. Missing caller identity after a crash requires recovery
of the original job/key, not guessing a new key.

Unique ledger key: `(github_host, repository_id, pr_number, operation_key)`.
The payload digest is deliberately NOT part of this uniqueness constraint:
a retry with changed content or source SHA is a conflict, not another event.
Concurrent prepare calls return the same frozen record or fail on conflict.
Timestamp and event ID are reused from that record, never regenerated.

Admission authenticates the submitting principal and destination. The configured
publisher is verified against GitHub's authenticated identity. Telos authorizes
each endpoint/redirect; Phylax applies admission/redaction before bytes freeze.
Replays never re-sanitize frozen bytes. A changed policy that rejects them blocks
publication and requires a new explicitly corrected operation.

## Event schema version 1

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`; reject unsupported versions and unknown fields. |
| `event_id`, `operation_key` | Canonical UUIDv4 and stable caller key above. |
| `github_host` | Approved configured host; no user-controlled alternate endpoint. |
| `repository_id`, `pr_number` | Positive integers; booleans are invalid integers. |
| `repository_name` | Resolved owner/name snapshot; identity remains the numeric ID. |
| `source_head_sha` | Full 40-character lowercase GitHub commit SHA, verified in target PR history. |
| `actor_id` | Nonempty namespaced authenticated-principal string, at most 200 characters; not an environment-variable identity claim. |
| `publisher_id` | Positive integer GitHub actor ID from the authenticated API identity; booleans are invalid. |
| `created_at` | UTC RFC3339 timestamp with `Z`, allocated at preparation. |
| `kind` | `report` or `legacy_recovery`. |
| `payload`, `payload_sha256` | Exact admitted text and SHA-256 of its UTF-8 bytes. |
| `corrects_event_id` | Optional earlier UUID in the same repository/PR; both records remain readable. |
| `legacy_snapshot` | Required for `legacy_recovery`, forbidden for `report`; contract below. |

Text is strict UTF-8 without BOM or unpaired surrogates. Preserve embedded LF,
CRLF, lone CR, trailing LFs and Unicode code points without normalization.
Payload limit: 128 KiB after UTF-8 encoding. Serialized event limit: 1 MiB,
including optional recovery snapshots. Oversize requests fail before intent or
network writes; they require separately authorized artifact handling.

Serialize with Python `json.dumps(sort_keys=True, ensure_ascii=False,
separators=(",", ":"), allow_nan=False)`, UTF-8 encoding and one record-terminating
LF. Parsing rejects duplicate keys, non-finite values and wrong field types.
Readers require canonical re-encoding to equal the stored record bytes.
Record SHA-256 is external to the record; self-referential hashes are forbidden.
Git blob identity and record SHA-256 are both verified on independent readback.
Correction targets must already be verified in the same PR; self-reference and
cycles are invalid. A record's declared actor is checked against the authenticated
request and retained verifier receipt, never accepted merely because it parses.

Routine reports do not read, hash, or depend on the PR body.
`legacy_snapshot` contains `original_body`, `original_sha256`, `merged_body`,
`merged_sha256` and the authorized grant identifier. These are complete admitted
snapshots with exact byte hashes, not Summary fragments. Never include grant
secrets. If policy prohibits retaining the original privately, automatic legacy
recovery is unavailable. Do not redact it and claim the digest proves equality.
Keep rejected sensitive content out of public events and operational logs.

## Ledger schema and transactions

| Table | Required data/invariant |
| --- | --- |
| `intents` | Unique operation key; frozen record BLOB, both digests, state/phase, source SHA, revision, lease owner/expiry. |
| `attempts` | Event ID, monotonic attempt number, phase, request digest, local request ID, dispatch-intent time, reply classification. |
| `observations` | Append-only received response/readback time, observed ref/commit/tree/blob/comment IDs and verification result. |
| `schema_migrations` | Version/checksum and applied time; migrations preserve frozen bytes and identities. |

Preparation, attempt intent, result observation and each state change are atomic
SQLite transactions. State writes use `WHERE revision = expected_revision`;
zero updated rows means lost ownership, not permission to continue.
Lease renewal uses the same revision check. No network call runs in a transaction.
Persist the dispatch-intent row BEFORE sending; a crash between intent and send
is conservatively uncertain. Do not manufacture a safe negative observation.

| Current state | Evidence required | Next state/action |
| --- | --- | --- |
| Prepared | Frozen record and successful admission committed | EvidencePending; persist dispatch intent. |
| EvidencePending | Reachable protected-ref record, exact bytes/schema/provenance verified | EvidenceVerified; persist receipt. |
| EvidenceVerified | Pointer intent committed | PointerPending; dispatch additive comment. |
| PointerPending | Full event and authorized pointer re-fetched and matched | Complete; persist both receipts. |
| Either pending state | Timeout, crash, unknown response, interrupted verification | Uncertain, retaining the uncertain phase and all identities. |
| Uncertain | Matching evidence/pointer verified | Resume the corresponding verified state or Complete. |
| Uncertain | Conclusive conflict or exhausted operational recovery budget | NeedsOperator; retain frozen intent and observations. |
| NeedsOperator | Audited authorized repair/reconciliation decision | Resume reconciliation under the same identity, or remain blocked. |
| Complete | Later pointer deletion/record integrity alert | Record incident; re-verify; repair pointer additively or block on record conflict. |

No TTL, process exit, negative lookup, lease expiry or `gh` failure releases an
identity. Cancellation before any dispatch intent may stop work, but retains an
identity tombstone. Cancellation after possible dispatch requires reconciliation.
A different payload is a new deliberate operation with an explicit correction
relationship, never an implicit overwrite or recycling of a failed key.

## Reconciliation and retry policy

Evidence retries are safe only through the deterministic event path and
non-force/preservation protocol. List/fetch under the configured repository ID,
pin the observed ref and compare full record bytes and protected provenance.
If already present, adopt the receipt; if conflicting, stop. If absent, retain
the old attempt and retry the SAME record against the latest ref. A late earlier
request can only publish that same event or lose the ancestry race.

Pointer retries are at-least-once. List all issue-comment pages (100 per page),
search exact event markers, then fetch candidate comments individually.
An error, permission failure or incomplete pagination is not confirmed absence.
Even complete absence cannot exclude an in-flight create; duplicates are an
accepted outcome, deduplicated by event identity by every consumer.

Retry transient network/5xx/ref conflicts at 1, 2, 4, 8 and 16 seconds with
bounded jitter (±10%); at most five dispatches per worker claim.
Honor `Retry-After` and GitHub rate-limit reset when later than that schedule.
Authentication/permission rejection blocks pending reauthorization; schema,
identity or digest conflict immediately needs operator inspection.
After a claim budget, retain Uncertain and schedule recovery, starting at one
minute and capped at 30 minutes. Warn at 15 minutes and require operator ownership
at 24 hours. Neither deadline discards the record or licenses a new identity.

## Pointer contract and consumer behavior

A pointer contains a human-readable summary and exactly one versioned marker:

```text
<!-- orama-report-event:v1 {"event_id":"<uuid>","repository_id":1,"pr_number":1,"record_sha256":"<sha256>","commit_sha":"<sha>","blob_sha":"<sha>"} -->
```

The actual values must pass their schema. Include an HTTPS link pinned to the
verified commit and event path, never a mutable branch URL. No secret material
belongs in marker or comment. GitHub assigns the comment ID; persist that ID
and the repository/PR binding after readback.

Consumers verify marker schema, authorized comment author, target repository/PR,
full record bytes/digests, protected-branch membership and the event identity.
The source SHA names historical evidence; a later PR commit does not rewrite it.
Verify historical publisher identity against retained authorization/protection
receipts; revoked-current credentials must not erase previously verified history.
A valid event proves what was stored, not the truth of every statement in it.

Forged/foreign/malformed markers are untrusted inputs: ignore for completion,
audit safely and continue legitimate reconciliation. A conflict attached to an
authorized identity is an integrity incident. Copied follow-up prose, a Summary
heading, a URL alone, or another user's marker cannot consume an operation.

Deduplicate logical events by the stable repository/PR/event identity; retain all
matching comment IDs for diagnostics. Never delete comments to approximate
exactly-once delivery. If a verified pointer is deleted, the event stays durable;
post an additive replacement only after re-verification and admission.
A removed/rewritten evidence record halts reporting and triggers restore/incident
review; never silently redirect a pointer to a different record.

## Contract authority

GitHub's [create-comment API][comments]
creates comments but documents no event-idempotency precondition. These contracts
therefore promise one immutable logical event and potentially multiple pointers.
Legacy body edits retain their unclosable external race and cannot reuse the safe
event retry policy. See the production specification's supervised recovery rules.

[comments]: https://docs.github.com/en/rest/issues/comments#create-an-issue-comment
