# Release 0 to 2 contract freeze (2026-10-26)

Status: **DRAFT freeze for implementation, not ratified.** Ratification is the operator's. A draft
pull request, green CI or this file is not an activation, enablement or ratification record.
`ORAMA_GRANT_SERVING` stays unset everywhere. No implementation may set it, read a date to enable
anything, or default any capability bit to allow. Missing or invalid input means deny.

This note is the normative draft for the capability record, the startup refusal matrix, the
public error vocabulary, the terminal taxonomy mapping and the Release 2 frozen items. It is
the contract that the Phylax, Oramasys and Telos drafts are built against. The baseline facts
(heads, pins, digests, E1 heads) are in the
[activation-readiness baseline receipt](activation-readiness-baseline-2026-10-26.md). The
machine-readable form of Section 1 is
[capability-record.schema.json](../../schemas/capability-record.schema.json).

## 1. Capability record

Owner: this repository defines the schema; Phylax, Oramasys and Telos enforce it.

```json
{
  "schema": "orama-capability-record/v1",
  "record_id": "<opaque>",
  "issued_at": "<RFC3339 UTC>",
  "issuer": "<control-plane id>",
  "capabilities": {
    "serving": false,
    "effects": false,
    "transport": false,
    "continuation": false,
    "autonomous_settlement": false
  },
  "binds": {"binary_digest": "sha256:<hex>", "config_digest": "sha256:<hex>"},
  "signature": null
}
```

`signature` is `null` or a non-blank string (an operator signature envelope in text form; its
verification is not in the schema). An object, an empty string or a whitespace-only string is
invalid.

Rules:

- Each bit is independent; none is inferred from another. `serving=true` never implies
  `effects`.
- A missing record, unreadable record, unknown `schema`, missing bit, non-boolean bit, or digest
  mismatch makes every bit effectively `false` (deny), and readiness reports the reason.
- The reason set is closed and shared by the consumer and Phylax: `record_missing`,
  `record_unreadable`, `schema_unsupported`, `record_invalid`, `bit_invalid`, `digest_mismatch`,
  `digest_unverified` (a bit is true and no expected digest is available to compare) and
  `unsigned_enablement`. A missing or non-boolean bit is `bit_invalid`; any other malformed
  record is `record_invalid`. The `startup.*` codes in Section 2 are consumer-only.
  `capability.ok` is Phylax-internal and is never a public or startup code.
- The consumer parser rejects a record that has a duplicate key at any level and a record larger
  than 8 KiB (8192 bytes), both as `record_invalid`.
- `signature: null` is allowed only while every bit is false. The schema enforces this shape: any
  `true` bit requires `signature` to be a string. Any `true` bit also needs a verified
  operator signature. In Releases 0 to 2 no signing path exists, so any `true` bit is refused at
  startup with `capability.unsigned_enablement`.
- Readiness prints each bit's effective value and the reason when it differs from the record.
- The schema checks shape only. The consumer must parse `issued_at` as an RFC 3339 UTC
  timestamp; a parse failure makes the record invalid and denies every capability. Digest
  comparison and signature verification are also runtime checks in the consumer and are not
  expressed in the schema.

## 2. Startup refusal matrix

Refuse at startup, before any dispatch.

| Code | Condition |
| --- | --- |
| `startup.serving_without_verifier` | `serving` true and no verify-only authority available |
| `startup.effects_without_permit_verifier` | `effects` true and no valid permit verifier |
| `startup.transport_without_policy` | `transport` true and no Telos policy loaded |
| `startup.autonomy_without_activation` | `autonomous_settlement` or `continuation` true without a C4 activation record |
| `startup.monitoring_as_permission` | any configuration where a monitoring, health or export failure would allow an action |
| `startup.serving_implies_effects` | any code path or configuration treating `serving` as `effects` |
| `capability.unsigned_enablement` | any bit true without a verified operator signature |

## 3. Public error vocabulary

Codes are stable. Nothing in a response may carry a grant id, a key, a path or a policy
internal. Body shape:

```json
{"error": {"code": "<code>", "correlation_id": "<uuid>"}}
```

Where a durable record exists the `error` object also carries `"receipt_ref": "<opaque>"`, so the
body is `{"error": {"code", "correlation_id", "receipt_ref"}}`. There is exactly one placement:
`receipt_ref` is never a sibling of `error`. Nothing else.

Verifier denial codes (mapped from the Phylax internal reasons). The consumer-side codes that
Phylax does not produce are in the second table below.

| Public code | Internal reason(s) |
| --- | --- |
| `deny.revocation_stale` | `revocation.stale`; raised when the observation is older than 60 seconds, more than 5 seconds in the future, or has no timezone (ADR 71 REVOCATION_MAX_AGE_SECONDS); an observation exactly 60 seconds old is fresh |
| `deny.unknown_key` | `grant.key_unknown` |
| `deny.malformed_grant` | `grant.malformed`, `grant.schema_unsupported`, `grant.signature_invalid`, `grant.expired`, `grant.future_dated` |
| `deny.revoked_grant` | `grant.revoked` |
| `deny.missing_capability_record` | capability record absent or invalid (new) |
| `deny.verifier_unavailable` | `verifier.unavailable` |

Consumer-side codes (raised by the consumer itself, with no Phylax internal reason):

| Public code | Condition |
| --- | --- |
| `deny.unauthorized_caller` | caller not authenticated, not the principal bound to the attempt, or the `attempt_id` is unknown (new) |
| `deny.grant_conflict` | the consumption ledger refuses a definitive, non-retryable conflict on `/adjustments` (hold not eligible, units exceed remaining, digest conflict, epoch fenced, basis or store mismatch and similar); the internal reason is never exposed (new) |

Serving codes: `serving.not_ready` (HTTP 503, stable) and `serving.route_not_exposed`
(HTTP 404). There is no separate disabled-serving code: `serving.route_not_exposed` covers a disabled
surface without revealing whether the route exists.

HTTP status of each `deny.*` code, one table for every surface:

| Public code | HTTP |
| --- | --- |
| `deny.malformed_grant` | 400 |
| `deny.unauthorized_caller` | 401 |
| `deny.unknown_key`, `deny.revoked_grant`, `deny.missing_capability_record` | 403 |
| `deny.grant_conflict` | 409 |
| `deny.revocation_stale`, `deny.verifier_unavailable` | 503 |

Two rules are fixed here, in the body of the contract, and apply to every route:

- **Unauthenticated caller.** A caller that is not authenticated, or is not the principal bound to
  the attempt, on a route that is exposed gets HTTP 401 with `deny.unauthorized_caller` in the
  Section 3 body. On the effect route an `attempt_id` that does not exist gets the identical
  answer (same status, same body shape, no `receipt_ref`), so a caller cannot learn whether an
  attempt exists. A bare framework body such as `{"detail": ...}` is not a conforming answer on an
  exposed route. A route that is not exposed answers `serving.route_not_exposed` (404) instead.
- **In-doubt dispatch.** When the send marker is set (Section 4) and the outcome is not proven, or a
  verifier, clock or outcome cannot be vouched for, the answer is HTTP 503 with
  `deny.verifier_unavailable` and the opaque `receipt_ref` of the durable attempt record. It is a
  deny, never an allow, and never a refusal record: the attempt stays `unknown` (blocking) until
  an authenticated operator reconciliation settles it.

One closed error envelope covers every response of the application, installed once at application
level. No response carries a `detail` key. The framework and transport failures map as follows:

| Failure | HTTP | Code |
| --- | --- | --- |
| authentication middleware rejects the caller | 401 | `deny.unauthorized_caller` |
| the authentication token is not configured | 503 | `serving.not_ready` |
| unknown route or method (404, 405) | 404 | `serving.route_not_exposed` |
| request validation failure | 400 | `deny.malformed_grant` |
| any other unhandled failure | 503 | `deny.verifier_unavailable` |

Route-level mappings. `/run`: a missing authenticated context is 401
`deny.unauthorized_caller`; every other admission refusal is 503 `deny.verifier_unavailable`.
`/adjustments`: verifier failures use the Section 3 verifier codes; a ledger consumption refusal
is 409 `deny.grant_conflict` (a definitive ledger answer, do not retry, with the reason hidden); a
principal mismatch is 401 `deny.unauthorized_caller`; a clock regression is 503
`deny.verifier_unavailable`. Per-route handlers remain only to attach the audit `receipt_ref`.

## 4. Terminal taxonomy mapping

E1 Parts 1 and 2 are ratified (see Section 5 of the baseline receipt for the exact head). The
stored names stay as they are. The plan names and the R4 contract names are **aliases only**; no
ratified name is renamed.

| Plan state | Stored (E1 / Oramasys) | R4 contract name |
| --- | --- | --- |
| `prepared` | attempt `created` | none |
| `authorized` | `authorized` | none |
| `dispatched` | outbox `send_started = 1` | none |
| `acknowledged` | outcome `confirmed` | `confirmed_applied` |
| `refused` (pre-dispatch) | `AuthorizationRefused`, a terminal disposition record | none |
| `refused` (target refuses after dispatch) | stored `failed` | `confirmed_not_applied` |
| `unknown` | outcome `unknown` (blocking; never auto-rolled back) | `unknown` |

### Pre-dispatch refusal record and replay

One rule set; the activation plan restates it and must not differ.

1. **Terminal refusal record before dispatch.** `AuthorizationRefused` is the
   `authorization_refused` **disposition**, not an outcome value. The ratified E1 outcome
   vocabulary remains `confirmed`, `failed`, and `unknown`; a refusal is recorded only before an
   outbox send starts, so it has no outcome and cannot be represented as `failed`.
2. **Record shape.** The existing attempt store holds one append-only refusal row per
   `attempt_id`. The stored fields are `attempt_id`, `disposition` (always
   `"authorization_refused"`), `kind`, `rule`, `reason`, `refusal_code` (one Section 3 `deny.*`
   code), the opaque `receipt_ref` and `recorded_at`. It stores no grant id, key id, target,
   payload or binding digest. The public fields are exactly `disposition`, `refusal_code`,
   `receipt_ref` and `recorded_at`. The `kind`, `rule` and `reason` fields are internal: they may
   be stored for audit only, and never appear in a response or outside logs.
3. **Overlay, not rewrite.** The refusal row is an overlay that fences the attempt. Refusing never
   releases the reservation, deletes the outbox row or rewrites the attempt. A database trigger
   aborts any update of `send_started` on an outbox row whose attempt has a refusal row, so a
   refused attempt can never start a send. The refusal row is written in the existing
   `BEGIN IMMEDIATE` authorization transaction, which re-checks `send_started = 0` before it
   inserts. When a verifier or other I/O has to run before the refusal is known, the row is
   recorded afterwards in its own transaction: no write lock is held across I/O, and the trigger
   plus the re-check close the gap.
   - *No prior row:* if final authorization refuses an attempt that has no row, the refusal row is
     committed before returning.
   - *Revocation or a cascade found at the send boundary:* the send-time recheck writes the
     terminal refusal in the same begin-send transaction (kind `final_boundary`, reason the fact:
     `grant_revoked`, `issuer_revoked` or `cascade_listed`, code `deny.revoked_grant`),
     commits, and then raises the refusal with its `receipt_ref`. The inert path never runs.
   The refusal does not consume a use, write an intent or an outbox item, or set `send_started`.
   The unique `attempt_id` makes concurrent refusals converge on the committed row, and the first
   row wins.
4. **Replay returns the same refusal.** The bound tuple is immutable. The `effect_grant_bindings`
   table accepts no UPDATE and no DELETE (append-only triggers), and
   `reservations.consumed_attempt_id` cannot change once it is set; the same triggers are applied
   when an existing database is migrated. The request body carries only `attempt_id`, and the
   grant, scope, target and epoch come from that stored binding. So the replay check is the
   authenticated principal equal to the bound principal, made before the refusal lookup; there is
   no binding digest. An exact replay first looks up `attempt_id`; when it finds
   `authorization_refused`, it performs no new authorization or dispatch and returns the stored
   refusal with the HTTP status of the stored `refusal_code` (Section 3). Its public body is
   exactly:

   ```json
   {"error":{"code":"<stored refusal_code>","correlation_id":"<new uuid>","receipt_ref":"<stored opaque receipt_ref>"}}
   ```

   The fresh correlation id is request tracing only; the stored code and receipt reference
   identify the same terminal refusal on every replay. A caller that is not the bound principal,
   and an unknown `attempt_id`, both get the identical 401 `deny.unauthorized_caller` of Section 3
   and never see the stored refusal.
5. **No terminal refusal after the send marker.** Once the outbox send marker (`send_started = 1`)
   is set, no refusal record may be written for that attempt, and an existing refusal is never
   rewritten into a send. From that point the only stored outcomes are `confirmed`, `failed`
   (target refused after dispatch) and `unknown`.
6. **In-doubt dispatch.** After the send marker, an unproven outcome is `unknown` and is answered
   as HTTP 503 `deny.verifier_unavailable` with its `receipt_ref` (Section 3). It is never
   converted into a refusal record and never auto-rolled back.

### Synthesis decisions

Recorded 2026-10-27 when the documented contract and the code were reconciled, keeping the
stronger guarantee of each side. Nothing here enables serving or effects.

- **F1.** No binding-conflict code or 409; wrong principal and unknown `attempt_id` both get
  the same 401, which removes an existence oracle.
- **F2.** No binding digest; the replay check is principal equality, and the bound tuple is
  immutable in storage through append-only triggers.
- **F3.** The refusal row is an append-only overlay, fenced by a trigger on `send_started`; the
  reservation and outbox row are kept.
- **F4.** Revocation found at the send boundary writes its refusal in the begin-send transaction,
  so replay returns the same `receipt_ref`.
- **F5.** One closed error envelope at application level; no `detail` key; new public code
  `deny.grant_conflict` (409) keeps the ledger answer definitive while hiding internal reasons.
- **F6.** Stored and public refusal fields are listed explicitly; `kind`, `rule` and `reason`
  stay internal.
- **F7.** The 401 and 409 codes sit in a consumer-side table, so "Two rules" is accurate.
- **F8.** One freshness rule everywhere: stale if older than 60 s, more than 5 s in the future or
  naive; exactly 60 s is fresh.
- **F9.** Schema `signature` is a non-blank string or null, and a true bit requires a string.
- **F10.** One closed capability reason set shared by both sides; `startup.*` is consumer-only.
- **F11.** The disabled-serving code is removed; `serving.route_not_exposed` covers it.

## 5. Release 2 frozen items

Frozen here, before any Release 2 implementation commit. Oramasys implements them on its
existing attempt store; no second ledger is created.

- **Effect-attempt identity.** The existing `attempt_id` (primary key), bound to principal,
  graph id, policy hash, operation (payload) digest, artifact identity, destination (target),
  authority epoch and expiry.
- **Approval binding.** Single use, bound to exactly that tuple. Any change yields a different
  attempt and is refused.
- **Reservation and fencing epoch.** Committed in the same `BEGIN IMMEDIATE` transaction as the
  ledger transition (the existing `_authorize_in_transaction`). An explicit integer fencing
  epoch column is added if absent.
- **Fencing epoch (defined).** A positive integer owned by the attempt store: one monotonic
  current mark per store, stamped once on an attempt at authorization. Authorizing below the
  current mark is refused as stale, a later send is refused when the mark has moved past the
  attempt's stamp, and the mark is raised only by an authenticated operator action that is
  logged append-only. It fences stale writers and stale attempts.
- **Lease epoch (defined, distinct).** A positive integer naming the generation of the consumer's
  lease, carried as a verified fact of the signed grant (`consumer_lease_epoch`) and checked
  again at send time. It proves that the consumer holding the grant is the current lease holder.
  It is never compared with, substituted for, derived from or stored in the fencing epoch field,
  and neither epoch implies the other: a send needs both to hold.
- **One send path.** The final-boundary send path of the attempt store is the only way an effect
  is sent. The send-time checks (expiry, revocation, divergence and quarantine state, clock and
  anchor checks, consumer lease validation) live in one shared helper that every send entry point
  calls. A composer verifies the signed grant and binds it into that path; no second path sends
  around effects gating, single-use approval consumption, fencing or those rechecks.
- **Outbox item and dispatch receipt.** The existing outbox, plus a redacted receipt record
  `{attempt_ref, outcome, receipt_digest, recorded_at}` carrying no payload, no grant id and no
  key id.
- **Replay.** An exact replay returns the stored receipt. A second dispatch for the same
  identity is refused. Replay of a settled successful send returns the stored receipt before any
  re-authorization. The consumer lease check runs in the shared send-time helper inside the send
  transaction and fails closed when no lease view is available.
- **Sealed command envelope (inert driver input).** Canonical JSON
  `{"v":1,"attempt_id":..., "operation_digest":"sha256:..", "target":"inert://simulation",
  "epoch":<int>, "expires_at":..}` plus its sha256. The `epoch` field is the fencing epoch
  (distinct from the consumer lease epoch, which is never carried in the envelope). The driver
  rejects anything else and never executes text.
- **Redaction envelope.** Public surfaces carry only the Section 3 body shape and the receipt
  record above.

Owner map: Core owns neutral scheduler mechanics and lifecycle seams only; Phylax owns
approval and grant verification, revocation, evidence integrity and the monitoring contract;
Oramasys owns the attempt ledger, durable reservation, idempotency, fencing and composition;
Telos owns endpoint and egress policy and health constraints; Agate is not in this wave.

## 6. Out of scope

Release 3 to 5, provider calls, live effects, operator enablement records, merging, setting
`ORAMA_GRANT_SERVING`, editing the open candidate pull requests directly, Agate changes and Core
changes. The four live-T3 gates (trusted effect-grant composition, final-boundary
authorization, isolation evidence, subprocess crash qualification) stay explicit draft gates.
