# E1 C2 (part 2): dispatch-permit wire fields and role reconciliation

Status: PROPOSED specification for independent review. Not ratified, no code, no wire change, not
authorization for T3. It fixes the wire choices that E1 section 13.4.1 leaves open and reconciles
the role and revocation text across sections 2, 11, 13.2, 13.4, 13.7 and 13.8. Part 1 is the
[purpose, version and refusal contract](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md).

## 1. Permit objects (proposed)

Encoding follows the recovery-grant rules: canonical JSON, ASCII keys, strings and safe integers
only, no nulls, six-digit UTC timestamps, unpadded base64url signature, at most 65,536 bytes.

**Permit request** (consumer to issuer, authenticated channel): `grant_id`, `grant_payload_digest`,
`operation_id`, `request_digest`, `artifact_digest`, `reservation_id`, `ledger_store_id`,
`configuration_policy_epoch`, `authority_epoch`, `requested_at`.

**Permit** (issuer-signed, preimage domain `phylax-dispatch-permit-v1\x00`, `schema_version` 1,
exact field set): every request field above, plus `permit_id`, `revocation_version` (the
issuer's gapless revocation counter at the decision, written `R_p`), `issuer_authority_version`,
`issued_at`, `expires_at`, `issuer_key_id`, `payload_digest`, `issuer_signature`.

**Lifetime.** `expires_at` is at most the grant's `expires_at` and at most `issued_at` plus a
permit lifetime fixed by the signed policy, never by the request. The value is an operator
decision; a short bound of the order of the 60-second clock allowance already decided is
recommended. A permit that is expired at step 3 is refused and counts as used (section 3).

**Issuer storage (proposed).** One table `dispatch_permits` with `permit_id` primary key,
`grant_id` **unique**, `reservation_id`, `request_digest`, `r_p`, `issued_at`, `expires_at` and a
state. The unique `grant_id` is what makes "no permit exists other than an identical retry" a
database fact, and an identical retry (same grant, reservation and request digest) returns the
stored permit unchanged.

**Consumer record at step 3 (proposed).** In the same transaction that records the intent and the
outbox item: `permit_id`, permit digest, `r_p`, the effective `authority_pair`, and
`cascade_acked_through`.

**Cascade acknowledgement.** The issuer emits revocation and cascade events with a gapless
increasing `version`. The consumer keeps `issuer_cascade_ack(issuer_id, version, event_digest,
applied_at)` and the contiguous high-water mark `acked_through`. Step 3 requires
`acked_through >= r_p`; a gap or a lag refuses dispatch and retries later. Nothing is inferred from
silence.

## 2. Ordering by owner (resolves the two cascade directions)

| Direction | Originates at | Ordered by | Consumer effect |
| --- | --- | --- | --- |
| Approver or role revoked at the consumer (13.8) | Consumer, `authority_epoch` advances | The consumer transaction that commits the epoch and the durable cascade request | Step 3 sees the new epoch and the pending request and refuses; the issuer may still sign a permit in the gap, which is safe because step 3 is consumer-owned |
| Grant, approval or issuer revoked at the issuer (13.4) | Issuer, `revocation_version` advances | The issuer transaction; a permit records `r_p` | Revocations at or below `r_p` must be acknowledged before step 3; later ones are post-authorization (in-flight rule) |
| Issuer rolled back from an older snapshot | Operations | The recovery witness (section 8.2) | Consumer holds the highest `r_p` it ever stored; an issuer store whose version is lower stays quarantined |

## 3. Replay and crash cases (proposed tests; no executable claim)

| Case | Required outcome |
| --- | --- |
| Issuer crashes before the permit transaction commits | No permit exists; an identical retry decides again |
| Permit committed, response lost | An identical retry returns the same permit; no second permit |
| Consumer crashes after receiving the permit, before step 3 commits | On restart the consumer knows from its own store that step 3 did not commit; an unexpired permit may be used once; an expired one is used up and the grant is not re-permitted |
| Step 3 committed, crash before the outbox send | The outbox protocol of section 4 governs; the attempt is `unknown` if a send may have started |
| Permit presented for another reservation, request digest or `authority_pair` | Refused; no state change |
| Permit replayed after step 3 recorded it | Refused as already recorded |
| Revocation committed at the issuer after `r_p` | Post-authorization: in-flight rule, nothing claimed undone |
| Issuer unreachable, permit forged, unbound or expired | Dispatch refused; reported unavailable, never valid |
| Issuer store restored to an older state | Quarantine until reconciled against the consumer's stored `r_p` |

## 4. Reconciliation of sections 2, 11, 13.2, 13.4, 13.7 and 13.8

| # | Statement | Where | Finding | Proposed resolution |
| --- | --- | --- | --- | --- |
| 1 | Operator principal "May execute: No" | 2 | Resolved by 2.1 (capability versus role) | No change; keep the table-driven test |
| 2 | A bootstrap reconciler "can never by itself" release a hold | 2 (rule 4), 2.1, 11, 13.1 | Reads as absolute, while 13.2 and 13.7 permit one bounded release | Use one phrase everywhere: "cannot release a hold except under the one bounded exception of 13.2, which needs the mechanically verified `NOT_ACCEPTED` assertion and the ledger fence" |
| 3 | Optional second-approver field frozen now; M2 every class requires 1; 2-of-2 later; second principal not enrolled | 11, 13.4, 13.8 | Consistent only if stated once | State: the field is in the wire now; at M2 no class may require 2; with no enrolled second principal a non-empty `second_approval_ref` cannot verify and is refused; the first 2-of-2 policy needs the enrollment decision (deferred) |
| 4 | Older verifier refuses with `grant.schema_unsupported` | 13.4 | Wrong for the pinned parser (field set first) | Correct as in part 1, section 6 |
| 5 | Consumer-originated and issuer-originated cascades | 13.4, 13.4.1, 13.8 | Two directions described in separate places | Adopt the ordering table in section 2 above |
| 6 | "Oramasys carries no cryptography" versus the consumer verifying a permit | 2 (rule 2), 13.4.1 | Apparent conflict | Verification goes through the injected verifier port that Phylax supplies; Oramasys code still contains no signature primitive |
| 7 | "Serving is verifier-only and never opens the issuer" versus asking the issuer for a permit at dispatch | 2 (rule 1), 13.4.1 | **Real tension** | Rule 1 must say that the serving process never loads signing material and never opens the authority store, but may call the issuer's narrow permit operation over an authenticated channel; issuer availability becomes a dispatch dependency that fails closed |
| 8 | Independent release needs a distinct principal and credential | 2, 13.1, 13.2, 13.8 | Consistent; enrollment deferred | No change; until a second principal is enrolled, no reconciler is `independent` |

## 5. Erratum text for the durable-effects contract (not applied here)

Step 4 currently reads as the linearization point for revocation. Proposed wording at ratification:
"The dispatch-authorization transaction orders the consumer-owned facts (role revision,
`authority_epoch`, worker ownership, fencing epoch). Issuer-owned facts (grant, approval and issuer
revocation, grant use) are ordered at the issuer by the dispatch permit and are acknowledged here
through `acked_through >= r_p`." This pull request does not edit that contract.

## 6. Decisions left to the operator

1. Permit lifetime value and whether it may differ per effect class.
2. Resolution 7: issuer availability as a dispatch dependency, or a different mechanism.
3. Which Phylax release carries the version-first parser order, and the `effect_class` registry.
4. Ratification of the integrated contract, by exact commit, after independent review.
