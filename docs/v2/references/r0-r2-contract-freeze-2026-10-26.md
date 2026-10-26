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

Where a durable record exists the body also carries `"receipt_ref": "<opaque>"`. Nothing else.

Verifier denial codes (mapped from the Phylax internal reasons):

| Public code | Internal reason(s) |
| --- | --- |
| `deny.revocation_stale` | `revocation.stale`; must actually be raised when the observation is older than 60 seconds (ADR 71 REVOCATION_MAX_AGE_SECONDS) |
| `deny.unknown_key` | `grant.key_unknown` |
| `deny.malformed_grant` | `grant.malformed`, `grant.schema_unsupported`, `grant.signature_invalid`, `grant.expired`, `grant.future_dated` |
| `deny.revoked_grant` | `grant.revoked` |
| `deny.missing_capability_record` | capability record absent or invalid (new) |
| `deny.unauthorized_caller` | caller not authenticated or authorized for the surface (new) |
| `deny.verifier_unavailable` | `verifier.unavailable` |

Serving codes: `serving.not_ready` (HTTP 503, stable), `serving.disabled` (HTTP 503) and
`serving.route_not_exposed` (HTTP 404).

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

`AuthorizationRefused` is the `authorization_refused` **disposition**, not an outcome value. The
ratified E1 outcome vocabulary remains `confirmed`, `failed`, and `unknown`; a refusal is recorded
only before an outbox send starts, so it has no outcome and cannot be represented as `failed`.

The existing attempt store holds one refusal record per `attempt_id` with the discriminator
`disposition: "authorization_refused"` and exactly these contract fields: `attempt_id`,
`disposition`, `refusal_code` (one Section 3 `deny.*` code), opaque `receipt_ref`, and
`recorded_at`. It stores no grant id, key id, target, payload, or internal verifier reason.

Within the existing `BEGIN IMMEDIATE` authorization transaction, the consumer first looks up the
bound attempt identity. If no row exists and final authorization refuses the attempt, that same
transaction writes the refusal record and commits before returning. It does not consume a use,
write an intent or outbox item, or set `send_started`. The unique `attempt_id` makes concurrent
refusals converge on the committed record.

An exact replay first looks up `attempt_id`; when it finds `authorization_refused`, it performs no
new authorization or dispatch and returns the stored refusal. Its public body is exactly:

```json
{"error":{"code":"<stored refusal_code>","correlation_id":"<new uuid>"},"receipt_ref":"<stored opaque receipt_ref>"}
```

The fresh correlation id is request tracing only; the stored code and receipt reference identify
the same terminal refusal on every replay. A request with the same `attempt_id` but different
bound identity is a conflict and must not replace the committed record.

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
- **Outbox item and dispatch receipt.** The existing outbox, plus a redacted receipt record
  `{attempt_ref, outcome, receipt_digest, recorded_at}` carrying no payload, no grant id and no
  key id.
- **Replay.** An exact replay returns the stored receipt. A second dispatch for the same
  identity is refused.
- **Sealed command envelope (inert driver input).** Canonical JSON
  `{"v":1,"attempt_id":..., "operation_digest":"sha256:..", "target":"inert://simulation",
  "epoch":<int>, "expires_at":..}` plus its sha256. The driver rejects anything else and never
  executes text.
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
