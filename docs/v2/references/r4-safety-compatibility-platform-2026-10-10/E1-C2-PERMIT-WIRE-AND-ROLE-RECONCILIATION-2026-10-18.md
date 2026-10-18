# E1 C2 (part 2): dispatch-permit wire fields and role reconciliation

Status: PROPOSED specification for independent review. Not ratified, no code, no wire change, not
authorization for T3. It fixes the wire choices that E1 section 13.4.1 leaves open and reconciles
the role and revocation text across sections 2, 11, 13.2, 13.4, 13.7 and 13.8. Part 1 is the
[purpose, version and refusal contract](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md).

**Naming.** The durable-effects contract numbers its steps 1 to 6; its step 3 is the atomic
reservation and its step 4 is dispatch authorization. Section 13.4.1 splits step 4 into a permit
request, a permit decision and the consumer transaction. This record calls those **4.1, 4.2 and
4.3**. "Step 4.3" is the consumer dispatch-authorization transaction.

## 1. Permit objects (proposed)

Encoding follows the recovery-grant rules: canonical JSON, ASCII keys, strings and safe integers
only, no nulls, six-digit UTC timestamps, unpadded base64url signature, at most 65,536 bytes.

**Permit request (4.1, consumer to issuer, authenticated channel; exactly 11 fields):** `grant_id`,
`grant_payload_digest`, `operation_id`, `request_digest`, `artifact_digest`, `reservation_id`,
`ledger_store_id`, `configuration_policy_epoch`, `authority_epoch`, `consumer_acked_through` (the
consumer's contiguous acknowledged issuer version when it asked) and `requested_at`.
`artifact_digest` is **consumer-asserted**: the grant carries none, so the issuer cannot verify it.
It is signed as a binding the issuer saw, and the consumer re-verifies it at step 4.3.

**Permit (4.2, issuer-signed; exactly 20 fields):** `schema_version` (the integer 1), every request
field above, `permit_id`, `revocation_version` (the issuer's gapless revocation counter at the
decision, written `R_p`), `issuer_authority_version`, `issued_at`, `expires_at`, `issuer_key_id`,
`payload_digest` and `issuer_signature`. Preimage domain `phylax-dispatch-permit-v1\x00`.

**Issuer decision (4.2).** In one issuer transaction: refuse if the grant, its approval chain or the
issuer is revoked or a cascade for them is pending; refuse if `R_p` (the issuer's own counter)
would be **below `consumer_acked_through`**, because an issuer that is behind a version the
consumer already acknowledged has been rolled back and must stay quarantined; otherwise record the
permit at `R_p` and return it.

**Step 4.3 (consumer transaction) requires all of:**

1. The permit is authentic, bound to this reservation, request digest, `artifact_digest` and
   `authority_pair`, unexpired under the clock policy, and not already recorded.
2. `acked_through >= R_p`: every issuer event up to `R_p` is acknowledged here, with no gap.
3. `R_p >= consumer_acked_through` as recorded in the request. This catches an issuer whose
   counter went backwards.
4. **No acknowledged event of any version, including versions above `R_p`, revokes the grant, its
   approval chain or the issuer.** A revocation the consumer already knows refuses dispatch even
   if it was committed after the permit. The in-flight rule applies only to revocations that the
   consumer has not acknowledged when step 4.3 commits.
5. The consumer-owned gates still hold (role revision, `authority_epoch`, worker ownership,
   fencing epoch).

Then, in the same transaction: record the intent, consume the use and write the outbox item, with
`permit_id`, the permit digest, `R_p`, the effective `authority_pair` and `acked_through`.

**Lifetime.** `expires_at` is at most the grant's `expires_at` and at most `issued_at` plus a
permit lifetime fixed by the signed policy, never by the request. The value is an operator
decision; a short bound of the order of the 60-second clock allowance already decided is
recommended. See the stranding risk in section 3.

**Issuer storage (proposed).** One table `dispatch_permits` with `permit_id` primary key,
`grant_id` **unique**, `reservation_id`, `request_digest`, `r_p`, `issued_at`, `expires_at` and a
state. The unique `grant_id` makes "no permit exists other than an identical retry" a database
fact; an identical retry (same grant, reservation and request digest) returns the stored permit.

**Cascade acknowledgement.** The issuer emits revocation and cascade events with a gapless
increasing `version`. The consumer keeps `issuer_cascade_ack(issuer_id, version, event_digest,
applied_at)` and the contiguous high-water mark `acked_through`. A gap or a lag refuses dispatch
and retries later. Nothing is inferred from silence.

## 2. Ordering by owner (resolves the two cascade directions)

| Direction | Originates at | Ordered by | Consumer effect |
| --- | --- | --- | --- |
| Approver or role revoked at the consumer (13.8) | Consumer, `authority_epoch` advances | The consumer transaction that commits the epoch and the durable cascade request | Step 4.3 sees the new epoch and the pending request and refuses; the issuer may still sign a permit in the gap, which is safe because 4.3 is consumer-owned |
| Grant, approval or issuer revoked at the issuer (13.4) | Issuer, `revocation_version` advances | The issuer transaction; a permit records `R_p` | Events up to `R_p` must be acknowledged; **later events that are acknowledged before 4.3 commits also refuse**; only unacknowledged later ones are post-authorization |
| Issuer rolled back from an older snapshot | Operations | The recovery witness (section 8.2) and rule 3 of step 4.3 | The consumer keeps the highest version it ever stored; an issuer whose counter is lower is refused and stays quarantined |

## 3. Replay and crash cases (proposed tests; no executable claim)

| Case | Required outcome |
| --- | --- |
| Issuer crashes before the permit transaction commits | No permit exists; an identical retry decides again |
| Permit committed, response lost | An identical retry returns the same permit; no second permit |
| Consumer crashes after receiving the permit, before step 4.3 commits | On restart the consumer knows from its own store that 4.3 did not commit; an unexpired permit may be used once |
| Permit expires before step 4.3 (including benign clock skew) | Refused and recorded with an expiry reason. **Stranding risk:** with a unique `grant_id` the grant cannot be re-permitted. Default stays conservative (the grant is spent); an operator decision may allow a re-permit only after the consumer proves from its own store that 4.3 never committed and the reservation is released, and only before the grant's own expiry |
| Step 4.3 committed, crash before the outbox send | The outbox protocol of section 4 governs; the attempt is `unknown` if a send may have started |
| Permit presented for another reservation, request digest, `artifact_digest` or `authority_pair` | Refused; no state change |
| Permit replayed after step 4.3 recorded it | Refused as already recorded |
| Revocation committed at the issuer after `R_p`, **acknowledged before 4.3 commits** | Refused (rule 4) |
| Revocation committed at the issuer after `R_p`, not yet acknowledged at 4.3 | Post-authorization: in-flight rule, nothing claimed undone |
| Issuer restored to an older state, so its counter is below `consumer_acked_through` | Permit refused; quarantine until reconciled against the consumer's stored versions |
| Issuer unreachable, permit forged, unbound or expired | Dispatch refused; reported unavailable, never valid |

## 4. Reconciliation of sections 2, 11, 13.2, 13.4, 13.7 and 13.8

| # | Statement | Where | Finding | Proposed resolution |
| --- | --- | --- | --- | --- |
| 1 | Operator principal "May execute: No" | 2 | Resolved by 2.1 (capability versus role) | No change; keep the table-driven test |
| 2 | A bootstrap reconciler "can never by itself" release a hold | 2 (rule 4), 2.1, 11, 13.1 | Reads as absolute, while 13.2 and 13.7 permit one bounded release | Use one phrase everywhere: "cannot release a hold except under the one bounded exception of 13.2, which needs the mechanically verified `NOT_ACCEPTED` assertion and the ledger fence" |
| 3 | Optional second-approver field frozen now; M2 every class requires 1; 2-of-2 later; second principal not enrolled | 11, 13.4, 13.8 | Consistent only if stated once | The field is in the wire now; at M2 no class may require 2; with no enrolled second principal a non-empty `second_approval_ref` cannot verify and is refused; the first 2-of-2 policy needs the enrollment decision (deferred) |
| 4 | Older verifier refuses with `grant.schema_unsupported` | 13.4 | Wrong for the pinned parser (field set first) | Correct as in part 1, section 6 |
| 5 | Consumer-originated and issuer-originated cascades | 13.4, 13.4.1, 13.8 | Two directions described in separate places | Adopt the ordering table in section 2 above |
| 6 | "Oramasys carries no cryptography" versus the consumer verifying a permit | 2 (rule 2), 13.4.1 | Apparent conflict | Verification goes through the injected verifier port that Phylax supplies; Oramasys code still contains no signature primitive |
| 7 | "Serving is verifier-only and never opens the issuer" versus asking the issuer for a permit at dispatch | 2 (rule 1), 13.4.1 | **Real tension** | Rule 1 must say that the serving process never loads signing material and never opens the authority store, but may call the issuer's narrow permit operation over an authenticated channel; issuer availability becomes a dispatch dependency that fails closed |
| 8 | Independent release needs a distinct principal and credential | 2, 13.1, 13.2, 13.8 | Consistent; enrollment deferred | No change; until a second principal is enrolled, no reconciler is `independent` |
| 9 | "Absent means single approval" for `second_approval_ref` | 13.4 | Conflicts with an exact field set, where a missing key is malformed | The wire carries the empty string for "absent"; part 1, section 3.1 records the erratum |
| 10 | The consumer transaction is "the linearization point for revocation versus dispatch" | Durable-effects contract step 4 | **Breaking re-linearization:** issuer-owned facts move to the issuer's permit decision, with consumer acknowledgement of events | Record it as an explicit erratum at ratification (section 5), not as a passing remark |

## 5. Erratum text for the durable-effects contract (not applied here)

Step 4 currently reads as the linearization point for revocation. Proposed wording at ratification:
"The dispatch-authorization transaction (step 4.3) orders the consumer-owned facts (role revision,
`authority_epoch`, worker ownership, fencing epoch). Issuer-owned facts (grant, approval and issuer
revocation, grant use) are ordered at the issuer by the dispatch permit and are enforced here by
`acked_through >= R_p`, `R_p >= consumer_acked_through` and the refusal of any acknowledged
revocation." This pull request does not edit that contract.

## 6. Decisions left to the operator

1. Permit lifetime value and whether it may differ per effect class.
2. Whether an expired, never-committed permit may be re-issued (section 3) or the grant is spent.
3. Resolution 7: issuer availability as a dispatch dependency, or a different mechanism.
4. Which Phylax release carries the version-first parser order, and the `effect_class` registry.
5. Ratification of the integrated contract, by exact commit, after independent review.
