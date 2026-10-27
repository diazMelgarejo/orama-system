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

Rules:

- Each bit is independent; none is inferred from another. `serving=true` never implies
  `effects`.
- A missing record, unreadable record, unknown `schema`, missing bit, non-boolean bit, or digest
  mismatch makes every bit effectively `false` (deny), and readiness reports the reason.
- `signature: null` is allowed only while every bit is false. Any `true` bit needs a verified
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

Verifier denial codes (mapped from the Phylax internal reasons):

| Public code | Internal reason(s) |
| --- | --- |
| `deny.revocation_stale` | `revocation.stale`; must actually be raised when the observation is older than 60 seconds (ADR 71 REVOCATION_MAX_AGE_SECONDS) |
| `deny.unknown_key` | `grant.key_unknown` |
| `deny.malformed_grant` | `grant.malformed`, `grant.schema_unsupported`, `grant.signature_invalid`, `grant.expired`, `grant.future_dated` |
| `deny.revoked_grant` | `grant.revoked` |
| `deny.missing_capability_record` | capability record absent or invalid (new) |
| `deny.unauthorized_caller` | caller not authenticated or authorized for the surface (new) |
| `deny.attempt_binding_conflict` | `attempt.binding_conflict` (same `attempt_id`, different bound identity) |
| `deny.verifier_unavailable` | `verifier.unavailable` |

Serving codes: `serving.not_ready` (HTTP 503, stable), `serving.disabled` (HTTP 503) and
`serving.route_not_exposed` (HTTP 404).

HTTP status of each `deny.*` code, one table for every surface:

| Public code | HTTP |
| --- | --- |
| `deny.malformed_grant` | 400 |
| `deny.unauthorized_caller` | 401 |
| `deny.unknown_key`, `deny.revoked_grant`, `deny.missing_capability_record` | 403 |
| `deny.attempt_binding_conflict` | 409 |
| `deny.revocation_stale`, `deny.verifier_unavailable` | 503 |

Two rules are fixed here, in the body of the contract, and apply to every route:

- **Unauthenticated caller.** A caller that is not authenticated, or is not the principal bound to
  the attempt, on a route that is exposed gets HTTP 401 with `deny.unauthorized_caller` in the
  Section 3 body. A bare framework body such as `{"detail": ...}` is not a conforming answer on an
  exposed route. A route that is not exposed answers `serving.route_not_exposed` (404) instead.
- **In-doubt dispatch.** When the send marker is set (Section 4) and the outcome is not proven, or a
  verifier, clock or outcome cannot be vouched for, the answer is HTTP 503 with
  `deny.verifier_unavailable` and the opaque `receipt_ref` of the durable attempt record. It is a
  deny, never an allow, and never a refusal record: the attempt stays `unknown` (blocking) until
  an authenticated operator reconciliation settles it.
- **Attempt binding conflict.** A request that reuses an `attempt_id` with a different bound
  identity (Section 4 replay check) gets HTTP 409 with `deny.attempt_binding_conflict` in the
  Section 3 body. The body carries only `code` and `correlation_id` — no `receipt_ref` and no
  stored refusal fields — so the response does not expose whether a prior refusal exists.

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
2. **Record shape.** The existing attempt store holds one refusal record per `attempt_id` with the
   discriminator `disposition: "authorization_refused"` and contract fields: `attempt_id`,
   verifiable `binding_digest` (bound identity tuple hash for replay verification), `disposition`,
   `refusal_code` (one Section 3 `deny.*` code), opaque `receipt_ref`, and `recorded_at`. It stores
   no grant id, key id, target or payload. One rule covers internal detail: an attempt refusal record
   may store the internal kind, rule or reason for audit only, and never exposes it. The public
   fields are exactly `disposition`, `refusal_code`, `receipt_ref` and `recorded_at`; internal
   reasons otherwise appear only in logs, never in a response.
3. **Written in the authorization transaction.** Within the existing `BEGIN IMMEDIATE`
   authorization transaction, the consumer looks up the attempt by `attempt_id`.
   - *No prior row:* If no row exists and final authorization refuses the attempt, that same
     transaction writes the refusal record with its `binding_digest` and commits before returning.
   - *Existing unsent attempt blocked by revocation or a cascade:* If an attempt row already
     exists before dispatch (`send_started = 0`) and revocation or a cascade blocks authorization
     before `send_started`, that same transaction atomically transitions the existing attempt to
     `disposition: "authorization_refused"`, releases any held reservation, clears pending outbox
     intent, updates the refusal metadata (`refusal_code`, opaque `receipt_ref`, `recorded_at`),
     and commits without setting `send_started`.
   It does not consume a use, write an intent or outbox item, or set `send_started` in either
   case. The unique `attempt_id` makes concurrent refusals converge on the committed record, and the
   first record wins.
4. **Replay returns the same refusal.** An exact replay first looks up `attempt_id`; when it finds
   `authorization_refused`, it compares the incoming request's bound identity against the stored
   `binding_digest`. If the bound identity matches, it performs no new authorization or dispatch and
   returns the stored refusal with the HTTP status of the stored `refusal_code` (Section 3). Its
   public body is exactly:

   ```json
   {"error":{"code":"<stored refusal_code>","correlation_id":"<new uuid>","receipt_ref":"<stored opaque receipt_ref>"}}
   ```

   The fresh correlation id is request tracing only; the stored code and receipt reference
   identify the same terminal refusal on every replay. A request with the same `attempt_id` but a
   different bound identity fails the binding digest check, is rejected as HTTP 409
   `deny.attempt_binding_conflict` (Section 3) without exposing the stored refusal, and must not
   replace the committed record.
5. **No terminal refusal after the send marker.** Once the outbox send marker (`send_started = 1`)
   is set, no refusal record may be written for that attempt, and an existing refusal is never
   rewritten into a send. From that point the only stored outcomes are `confirmed`, `failed`
   (target refused after dispatch) and `unknown`.
6. **In-doubt dispatch.** After the send marker, an unproven outcome is `unknown` and is answered
   as HTTP 503 `deny.verifier_unavailable` with its `receipt_ref` (Section 3). It is never
   converted into a refusal record and never auto-rolled back.

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
