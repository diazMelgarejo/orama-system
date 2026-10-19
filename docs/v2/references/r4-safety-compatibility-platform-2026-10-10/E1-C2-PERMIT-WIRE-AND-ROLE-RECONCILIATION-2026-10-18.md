# E1 C2 (part 2): dispatch-permit wire fields and role reconciliation

Status: PROPOSED specification for independent review. Not ratified, no code, no wire change, not
authorization for T3. It fixes the wire choices that E1 section 13.4.1 leaves open and reconciles
the role and revocation text across sections 2, 11, 13.2, 13.4, 13.7 and 13.8. Part 1 is the
[purpose, version and refusal contract](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md).

**Naming.** The durable-effects contract numbers its steps 1 to 6; its step 3 is the atomic
reservation and its step 4 is dispatch authorization. Section 13.4.1 splits step 4 into a permit
request, a permit decision and the consumer transaction. This record calls those **4.1, 4.2 and
4.3** and adds **4.2f**, the issuer finalization that fixes the issuer-owned authorization order
just before the consumer commits. "Step 4.3" is the consumer dispatch-authorization transaction.
No issuer call is ever made inside the 4.3 transaction: 4.1, 4.2 and 4.2f all complete first, so
there is still no distributed transaction.

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

**Issuer decision (4.2).** In one issuer transaction, load the signed grant identified by
`grant_id`. For a new permit against a signed effect grant (schema v2; permits are not issued for the
recovery grant), refuse unless `grant_payload_digest` equals the grant's signed
`payload_digest`, and `operation_id`, `request_digest` and `ledger_store_id` equal the
corresponding signed grant fields. Then refuse if the grant, its approval chain or the issuer is
revoked or a cascade for them is pending; refuse if `R_p` (the issuer's own counter) would be **below
`consumer_acked_through`**, because an issuer that is behind a version the consumer already
acknowledged has been rolled back and must stay quarantined; otherwise record the permit at `R_p`
and return it.

**Finalization (4.2f, issuer, one transaction).** After the permit and before it opens the 4.3
transaction, the consumer sends a **finalization request** (exactly 8 fields): `permit_id`,
`permit_digest`, `attempt_id` (the consumer's stable identifier of this dispatch attempt),
`reservation_id`, `ledger_store_id`, `consumer_acked_through`, `authority_epoch` and
`requested_at`. In one issuer transaction the issuer refuses unless the permit exists, is not
terminal, has not expired and matches the request (including its `ledger_store_id`); re-reads the
grant, approval chain and issuer revocation state and refuses on any revocation or pending
cascade; **refuses if its current counter is below the request's `consumer_acked_through` or below
the permit's `R_p`**, because an issuer behind a version the consumer already acknowledged, or
behind its own earlier permit, has been rolled back and must stay quarantined (the same rule as
4.2, applied again because the consumer may have acknowledged more since the permit); appends one
**finalization event** to its gapless event chain in the same transaction, so `R_f` is that
event's version (always above the counter it read) and `revocation_event_digest` is its
`event_digest`; and returns an issuer-signed **finalization** (exactly 15 fields, domain
`phylax-dispatch-finalization-v1\x00`): `schema_version` (the integer 1), the eight request
fields, `finalization_id`, `revocation_version` (written `R_f`), `revocation_event_digest`,
`issued_at`, `expires_at` and `issuer_signature`. The finalization is idempotent per (`permit_id`,
`attempt_id`): an identical retry returns the stored bytes and appends no second event, and a
different `attempt_id` or binding for the same permit is refused (proposed name
`finalization.conflict`). Its lifetime is at most the permit's `expires_at` and at most the
signed-policy finalization lifetime, which is 90 seconds (decision 1, section 6).

**Why the finalization is a chain event.** The scalar floors catch a rollback that happened
before the finalization request: the consumer had already acknowledged versions past the restored
counter, so the request's `consumer_acked_through` exceeds it and 4.2f refuses. They cannot catch
a rollback in the window after the request is sent and before step 4.3, when the consumer
acknowledges events the issuer has already lost while the signed request value is stale. A
counter, or the digest of an event that already exists, cannot expose that either: a clean
restore has the same history up to its snapshot, and the lost events look like events the issuer
might legitimately create later. A new event is what differs. After a restore the issuer's next
event, at the latest its finalization event, takes a version the consumer may already hold with a
different digest, because each `event_digest` commits to the previous one. The consumer sees the
fork without clocks and without trusting the issuer's counter. The finalization also delivers its
own event, so no stream round trip is needed for that event itself; events up to `R_f - 1`
must still have been acknowledged, as before. The counter is issuer-wide, so nothing keyed to its
value alone may invalidate a permit (see retry identity).

**Step 4.3 (consumer transaction) requires all of:**

1. The permit is authentic, bound to this reservation, request digest, `artifact_digest` and
   `authority_pair`, unexpired under the clock policy, and not already recorded.
2. `acked_through >= R_p`: every issuer event up to `R_p` is acknowledged here, with no gap.
3. `R_p >= consumer_acked_through` as recorded in the permit, which is the acknowledgement of the
   request the permit answered, never a later retry's. This catches an issuer whose counter went
   backwards.
4. **No acknowledged event of any version, including versions above `R_p`, revokes the grant, its
   approval chain or the issuer.** A revocation the consumer already knows refuses dispatch even
   if it was committed after the permit.
5. The finalization obtained in 4.2f before this transaction opened is authentic, bound to this
   permit, attempt and reservation, unexpired and not already recorded, `R_f > R_p`, `R_f >`
   the finalization's signed `consumer_acked_through` (rule 3 again, read from the signed
   finalization rather than trusting the issuer's refusal at 4.2f), and `acked_through >=
   R_f - 1`. The finalization delivers its own event: the consumer recomputes the event digest
   for version `R_f` from its stored digest at `R_f - 1`, the version, kind `finalization` and
   `finalization_id`, requires it to equal `revocation_event_digest`, and then records event
   `R_f` as acknowledged. If it already holds version `R_f` with a different digest, or has
   recorded any divergence, it refuses. A mismatch or a divergence means the issuer's chain
   differs from what was acknowledged: refuse and keep the issuer quarantined. It is the
   linearization point for issuer-owned revocation versus dispatch: a revocation the issuer
   committed before finalization was refused there, and a later one is post-authorization, not
   an unobserved exception to a consumer-side check.
6. The consumer-owned gates still hold: role revision, `authority_epoch`, worker ownership and
   fencing epoch; the grant's signed `consumer_lease_epoch` is valid under the current fencing
   authority; no abandonment record fences this attempt; and the grant's use is unconsumed in
   the one authoritative store.

Then, in the same consumer transaction: record the intent, consume the use and write the outbox
item, with `permit_id`, the permit and finalization digests, `R_p`, `R_f`, the effective
`authority_pair` and `acked_through`.

**Lifetime.** `expires_at` is at most the grant's `expires_at` and at most `issued_at` plus a
permit lifetime fixed by the signed policy, never by the request. The value is decided: **90
seconds**, the same for the permit and the finalization and for every effect class (decision 1,
section 6). Expiry is strict: a permit or finalization is refused when `now >= expires_at`, with
no grace extension. The 60-second figures elsewhere are not extra validity: E1 section 13.2
allows 60 seconds for the provider `NOT_ACCEPTED` evidence window, and the pinned Phylax verifier
accepts a grant issued up to 60 seconds in the future while still rejecting `now >= expires_at`.
A consumer clock 60 seconds fast therefore has about 30 seconds of nominal use at issuance.
Deadlines run on a monotonic in-process clock with a durable UTC high-water check across
restarts, and the tests cover boundary offsets and restart. See the stranding risk in section 3.

**Retry identity (proposed).** A unique `grant_id` stops a second row but does not prove that a
repeat request is the same request. The issuer therefore persists a **binding digest** with the
permit: the canonical digest (the manifest encoding rules) of the object made of exactly these
nine immutable request fields: `grant_id`, `grant_payload_digest`, `operation_id`,
`request_digest`, `artifact_digest`, `reservation_id`, `ledger_store_id`,
`configuration_policy_epoch` and `authority_epoch`. On any request for a grant that already has a
permit, the issuer recomputes the digest and compares it with the stored one:

* **Equal:** an identical retry. The stored permit is returned unchanged, including its original
  `issued_at`, `expires_at` and `requested_at`. An expired stored permit is not revived.
* **Different:** a conflicting request for the same grant. It is refused with a closed permit
  refusal (proposed name `permit.conflict`, to be fixed in the integrated schema review). The
  stored permit is **not** returned, nothing is created or changed, and a sanitized audit record
  may be written. A different binding never receives the stored permit.

`requested_at` and `consumer_acked_through` are **excluded** from the binding digest. `requested_at`
is the consumer's own clock reading: it is recorded on the first request, never used for identity,
freshness or expiry, and a later retry's value is ignored. `consumer_acked_through` is consumer
state that legitimately grows, and a growing acknowledgement never invalidates a permit by
itself: the counter is issuer-wide, so one grant's finalization, or any unrelated event, moves it
for every other grant. An identical retry whose acknowledgement exceeds the stored `R_p`
therefore returns the stored permit unchanged, with its original recorded acknowledgement,
after applying the 4.2 floor to the retry: if the issuer's current counter is below the retry's
`consumer_acked_through`, it has been rolled back and stays quarantined instead of answering.
Nothing is lost by this: 4.2f re-reads the grant, approval chain and issuer revocation state at
the current counter and refuses on any relevant revocation, pending cascade or fork, and rule 4
of step 4.3 refuses any acknowledged event above `R_p` that revokes this grant, its approval
chain or the issuer; an acknowledged revocation of an unrelated grant blocks nothing.

A replacement is needed only when the permit is expired, abandoned or lost (decision 2). It
requires durable proof that step 4.3 did not commit and that the reservation was released. The
proof is a **consumer attestation** over the authenticated channel that names the `permit_id`,
the `attempt_id`, the consumer's fencing epoch, the reservation-release record and a statement
that no intent for that permit exists. The issuer cannot see the consumer's store, so it records
the attestation as audit evidence and does not claim to verify it; the safety does not rest on
it. Four invariants carry it. First, before attesting, the consumer commits a terminal
abandonment record that fences the old attempt, and step 4.3 rechecks it, so an old finalization
cannot race a release. Second, the replacement is made atomically against the expected prior
permit and records `replaces_permit_id` under a unique constraint, so concurrent or replayed
attestations cannot create two live successors. Third, issuance and finalization reject a
`ledger_store_id` different from the signed grant's, the authenticated capability is scoped to
the authorized consumer, and a restored or alternate consumer store cannot independently
authorize the same grant (a restored consumer stays quarantined, section 8.2). Fourth, the
grant's consumed-use record is unique in one authoritative store shared by competing consumers.
If a new reservation changes the immutable binding, the replacement transition validates the new
binding; an ordinary retry with a changed binding stays `permit.conflict`. The issuer then marks
the prior permit (and any finalization) `abandoned`, retains its signed bytes, and issues one new
permit at its current counter. Otherwise the grant remains conservatively unavailable. A wrong
attestation cannot cause a second dispatch: the consumer consumes the grant's single use inside
4.3, and refuses any later permit or finalization for a use it has already consumed, whatever
the issuer holds.

**Issuer storage (proposed).** One table `dispatch_permits` with `permit_id` primary key,
`grant_id`, `binding_digest`, `ledger_store_id`, `reservation_id`, `request_digest`, `r_p`,
`consumer_acked_through`, `requested_at`, `issued_at`, `expires_at`, `permit_bytes` (the canonical
signed permit), `finalization_bytes` and `finalization_id` when present, a state (`issued`,
`finalized`, `expired` or `abandoned`) and an optional `replaces_permit_id`, unique where present.
A partial unique constraint permits at most one nonterminal permit for a grant; a replacement is
allowed only by the proved-abandoned transition above, never by a second ordinary request.

**Cascade acknowledgement.** The issuer emits revocation and cascade events with a gapless
increasing `version`. Each event's `event_digest` commits to the previous event's digest and to
its own version, kind and body, so equal digests at one version imply an identical history. The
finalization event has kind `finalization` and revokes nothing: rule 4 of step 4.3 ignores it as
a revocation, and the consumer acknowledges it from the finalization itself (rule 5). The consumer keeps
`issuer_cascade_ack(issuer_id, version, event_digest, applied_at)` and the contiguous high-water
mark `acked_through`. An event for a version the consumer already holds with a different digest
is a **divergence**: the chain forked from what was acknowledged, dispatch is refused and the
issuer stays quarantined. A gap or a lag refuses dispatch and retries later. Nothing is inferred
from silence. `revocation_version` is the ordered issuer-event version: an increment is not
itself a revocation, and audit consumers must not count it as one. The canonical event bytes
(the manifest encoding over version, kind, body and previous digest) are frozen in the
integrated schema review before any implementation. The chain gives bounded detection only:
history that neither the consumer nor an independent witness retained cannot be revealed by it,
so the section 8.2 witness and quarantine stay required.

## 2. Ordering by owner (resolves the two cascade directions)

| Direction | Originates at | Ordered by | Consumer effect |
| --- | --- | --- | --- |
| Approver or role revoked at the consumer (13.8) | Consumer, `authority_epoch` advances | The consumer transaction that commits the epoch and the durable cascade request | Step 4.3 sees the new epoch and the pending request and refuses; the issuer may still sign a permit in the gap, which is safe because 4.3 is consumer-owned |
| Grant, approval or issuer revoked at the issuer (13.4) | Issuer, `revocation_version` advances | The issuer finalization transaction; a permit records `R_p` and finalization records `R_f` | The issuer refuses any revocation visible at finalization; the consumer acknowledges through `R_f`; only events after finalization are post-authorization |
| Issuer rolled back from an older snapshot | Operations | The recovery witness (section 8.2) and rules 3 and 5 of step 4.3 | The consumer keeps the highest version it ever stored; an issuer whose counter is lower is refused and stays quarantined |

## 3. Replay and crash cases (proposed tests; no executable claim)

| Case | Required outcome |
| --- | --- |
| Issuer crashes before the permit transaction commits | No permit exists; an identical retry decides again |
| Permit committed, response lost | An identical retry (equal binding digest) returns the same permit; no second permit |
| Same grant, any one immutable binding field different (reservation, request digest, artifact digest, ledger store, epoch pair) | `permit.conflict`; the stored permit is not returned; nothing changes |
| Same grant, identical binding, different `requested_at` | Identical retry; the original permit is returned; the new `requested_at` is ignored |
| Same grant, identical binding, higher `consumer_acked_through` than the stored `R_p` | Identical retry: the stored permit is returned unchanged. The finalization re-reads revocation state at the current counter and uses the current acknowledgement for its floors; a relevant revocation, pending cascade or fork refuses |
| Two grants hold permits at version 10; grant A finalizes (event 11); grant B acknowledges 11 and retries | B keeps its permit, finalizes above 11 against its current acknowledgement and dispatches; nothing forces an abandonment or a replacement |
| The same interleaving, but event 11 revokes B's approval chain | B's finalization refuses on the relevant revocation, and rule 4 of step 4.3 would too; B's reservation stays held until released |
| The same interleaving, but B's finalization comes from an issuer restored from an older snapshot | Divergence at step 4.3: refused, and the issuer stays quarantined |
| A finalization races the consumer's release of the same attempt | The abandonment record committed before attestation fences the attempt; step 4.3 rechecks it and refuses the old finalization |
| An attestation arrives after the use was consumed, or is replayed or sent twice concurrently | The consumer refuses any later permit for a consumed use; the unique `replaces_permit_id` lets one replacement win; no second live successor |
| Permit or finalization for a ledger other than the signed grant's, a stale `consumer_lease_epoch`, or a restored consumer store | Refused; a restored consumer stays quarantined |
| Consumer crashes after receiving the permit, before step 4.3 commits | On restart the consumer knows from its own store that 4.3 did not commit; an unexpired permit may be used once |
| Permit expires before step 4.3 (including benign clock skew) | Refused and recorded with an expiry reason. A replacement is allowed only after the consumer attests, from its own store, that 4.3 never committed and the reservation is released, and only before the grant's own expiry, and only when the attested cause is a transient delay, a cancellation or a loss; the issuer records the attestation and does not claim to verify it. Any other cause, and any unknown or pending outcome, is treated as spent and the grant remains unavailable (decision 2, section 6) |
| Step 4.3 committed, crash before the outbox send | The outbox protocol of section 4 governs; the attempt is `unknown` if a send may have started |
| Permit presented for another reservation, request digest, `artifact_digest` or `authority_pair` | Refused; no state change |
| Permit replayed after step 4.3 recorded it | Refused as already recorded |
| Revocation committed at the issuer before finalization | Refused by the issuer finalization transaction |
| Revocation committed after finalization | Post-authorization; the finalization receipt fixes the issuer-owned authorization order and nothing claims the completed authorization undone |
| Finalization committed, response lost | An identical request (same `permit_id` and `attempt_id`) returns the stored finalization; no second `R_f` is recorded |
| Finalization requested for a different `attempt_id`, binding, expired, abandoned or unknown permit | `finalization.conflict` or a permit refusal; nothing changes and nothing is returned |
| Consumer crashes after receiving the finalization, before step 4.3 commits | The consumer knows from its own store that 4.3 did not commit. The finalization is used only if still unexpired; otherwise the replacement path with an attestation applies |
| Finalization expires before step 4.3 | Refused at 4.3; the same replacement path applies, never a silent retry of 4.3 |
| Step 4.3 already consumed the grant's use, and the issuer later issues or holds another permit | The consumer refuses it: the consumer-owned single use is the backstop against a second dispatch |
| Issuer restored to an older state, so its counter is below `consumer_acked_through` | Permit refused; quarantine until reconciled against the consumer's stored versions |
| Issuer restored from a clean older snapshot after the consumer acknowledged later events, before the finalization request | The request's `consumer_acked_through` exceeds the restored counter: refused at 4.2f, and by rule 5 at step 4.3 if a finalization is returned anyway |
| The same restore, but the consumer acknowledges the lost events only after sending the request | The issuer's finalization event reuses a version the consumer holds with a different digest: divergence, refused at step 4.3 and quarantined. A digest of an existing event could not show this, because a snapshot has the same history up to its own point |
| Issuer restored, and the consumer never acknowledged the lost events | Not visible at the consumer, which has nothing to compare. Covered by the issuer's recovery quarantine and the witness of E1 section 8.2, not by this protocol |
| Issuer rolled back between permit and finalization, so `R_f` is below the request's `consumer_acked_through` or below `R_p` | Finalization refused at 4.2f; a finalization that is nevertheless returned is refused at step 4.3 rule 5. Either way the issuer stays quarantined and nothing is consumed |
| Issuer unreachable, permit forged, unbound or expired | Dispatch refused; reported unavailable, never valid; the layered containment of section 3a applies |

## 3a. Issuer unavailability: layered containment (decision 3)

Decision 3 scopes the issuer dependency to effectful dispatch. That scoping holds only if no
configuration, classification mistake or bug can create an effect path that skips the permit. The
controls below are independent, so one failing still leaves dispatch refused. The governing rule:
**unavailability is a state, never a verdict.** When the issuer cannot be reached, or its answer
cannot be used, the only legal outcomes are to refuse and report unavailable, hold the
reservation, and wait for the attested-release path of decision 2.

1. **Default-deny classification.** An operation is non-effect only if its `effect_class` is
   registered as non-effect. An unknown, missing or unregistered class is effectful. A
   misclassification can therefore only add a permit requirement, never remove one.
2. **No issuerless path exists to configure.** Not adopted, and not to be added: a break-glass
   or degraded mode, a pre-signed, cached, prefetched or pooled permit, local or consumer-side
   signing, signing material in the serving process, and any switch that skips 4.2f.
3. **A structural precondition at the effect boundary.** The outbox item written inside 4.3 has
   required `permit_id`, permit digest, finalization digest, `R_p` and `R_f`, and nothing else
   writes or sends one. The sender refuses an item whose recorded intent lacks them. A bug that
   skips the gate still cannot produce a sendable item.
4. **Ambiguity is not denial.** A timeout, a dropped connection, an unsigned or malformed
   response, or one that fails verification is *unknown*, not an issuer refusal. The reservation
   stays held and the attempt is recorded as unavailable under its `attempt_id`. The only
   continuations are an identical retry inside the deadline, which returns the stored permit or
   finalization and never a second one, or the attested-release path, where an unknown or
   pending outcome is treated as spent. A refusal the issuer actually signed (conflict,
   revocation) is a verdict and is recorded as one.
5. **One deadline.** An attempt's deadline is its permit's `expires_at`. Every issuer call
   carries the remaining budget as its timeout, retries are identical requests with bounded
   backoff, and no new request is made for that permit after the deadline. A finalization is
   requested only while at least the minimum window of decision 8 remains; otherwise the attempt
   ends locally as unavailable, so a slow issuer cannot hand over a finalization that is dead on
   arrival.
6. **Outage containment.** Per issuer, the consumer keeps a circuit breaker: after the
   threshold of decision 8 consecutive failures, effectful dispatch is refused at once without
   calling, and a periodic probe closes it. The breaker is consumer-local and only shortens a
   refusal; it never relaxes a check. Non-effect operations never consult it.
7. **Visible, never silent.** The consumer reports `dispatch.issuer_unavailable`, a consumer-side
   status that is not one of the issuer's closed `permit.*` refusals, writes a sanitized audit
   record, and raises an alert after the sustained-outage threshold of decision 8. It is never
   reported as valid, and never as pending-as-success.

**Failure-injection tests (proposed, to be written failing first).** Issuer down at 4.1;
response lost at 4.2 and at 4.2f (identical retry returns the stored object); issuer down after
finalization so the finalization expires before 4.3; a slow issuer past the deadline; an unsigned,
wrong-key, malformed or other-reservation response; a restore mid-attempt (divergence, section 1);
breaker open, half-open and closing; an unregistered `effect_class` treated as effectful; an
outbox insert without a permit refused; a non-effect operation proceeding while the issuer is
down; an attempt after its deadline refused; interleaved grants, where one grant's finalization never
invalidates another's permit; and every refusal above leaving the reservation
held, the grant's use unconsumed and no second permit issued.

## 4. Reconciliation of sections 2, 11, 13.2, 13.4, 13.7 and 13.8

| # | Statement | Where | Finding | Proposed resolution |
| --- | --- | --- | --- | --- |
| 1 | Operator principal "May execute: No" | 2 | Resolved by 2.1 (capability versus role) | No change; keep the table-driven test |
| 2 | A bootstrap reconciler "can never by itself" release a hold | 2 (rule 4), 2.1, 11, 13.1 | Reads as absolute, while 13.2 and 13.7 permit one bounded release | Use one phrase everywhere: "cannot release a hold except under the one bounded exception of 13.2, which needs the mechanically verified `NOT_ACCEPTED` assertion and the ledger fence" |
| 3 | Optional second-approver field frozen now; M2 every class requires 1; 2-of-2 later; second principal not enrolled | 11, 13.4, 13.8 | Consistent only if stated once | The field is in the wire now; at M2 no class may require 2; with no enrolled second principal a non-empty `second_approval_ref` cannot verify and is refused; the first 2-of-2 policy needs the enrollment decision (deferred) |
| 4 | Older verifier refuses with `grant.schema_unsupported` | 13.4 | Wrong for the pinned parser (field set first) | Correct as in part 1, section 6 |
| 5 | Consumer-originated and issuer-originated cascades | 13.4, 13.4.1, 13.8 | Two directions described in separate places | Adopt the ordering table in section 2 above |
| 6 | "Oramasys carries no cryptography" versus the consumer verifying a permit | 2 (rule 2), 13.4.1 | Apparent conflict | Verification goes through the injected verifier port that Phylax supplies; Oramasys code still contains no signature primitive |
| 7 | "Serving is verifier-only and never opens the issuer" versus asking the issuer for a permit at dispatch | 2 (rule 1), 13.4.1 | **Real tension** | Rule 1 must say that the serving process never loads signing material and never opens the authority store, but may call the issuer's narrow permit operation over an authenticated channel; issuer availability becomes a dispatch dependency that fails closed. **Decided 2026-10-19 (decision 3):** no new hard dependency for serving, verification or any non-effect operation. Effectful dispatch still needs a permit and fails closed when the issuer is unreachable, because an issuerless path would bypass replay protection; the layered containment is section 3a |
| 8 | Independent release needs a distinct principal and credential | 2, 13.1, 13.2, 13.8 | Consistent; enrollment deferred | No change; until a second principal is enrolled, no reconciler is `independent` |
| 9 | "Absent means single approval" for `second_approval_ref` | 13.4 | Conflicts with an exact field set, where a missing key is malformed | The wire carries the empty string for "absent"; part 1, section 3.1 records the erratum |
| 10 | The consumer transaction is "the linearization point for revocation versus dispatch" | Durable-effects contract step 4 | **Breaking re-linearization:** issuer-owned facts move to issuer finalization, with consumer acknowledgement of its receipt | Record it as an explicit erratum at ratification (section 5), not as a passing remark |

## 5. Erratum text for the durable-effects contract (not applied here)

Step 4 currently reads as the linearization point for revocation. Proposed wording at ratification:
"The dispatch-authorization transaction (step 4.3) orders the consumer-owned facts (role revision,
`authority_epoch`, worker ownership, fencing epoch). Issuer-owned grant, approval and issuer
revocation are ordered by the issuer's finalization transaction; the consumer verifies its receipt
and acknowledges through `R_f`. Grant use is consumed at the consumer only after that finalization
and its own gates pass." This pull request does not edit that contract.

## 6. Operator decisions

**Decided 2026-10-19 (operator):**

* **Decision 1, lifetime.** 90 seconds for the permit and the finalization, uniform across
  effect classes. No per-class override is adopted; one needs a new decision.
* **Decision 2, expired never-committed permit.** Assume spent first. A replacement is allowed
  only on the consumer's authenticated attestation that the cause is a transient delay, a
  cancellation or a loss; an unknown or pending outcome is treated as spent.
* **Decision 3, issuer availability.** Confirmed: no new hard dependency for serving,
  verification or non-effect operations. Effectful dispatch still fails closed without a
  permit, and an issuerless dispatch path is not adopted. Layered containment is section 3a.
* **Decision 4, Phylax release.** Adopted, with the gate widened after review. One compatible
  release carries the version-first parser order and the `effect_class` registry, because the
  registry means nothing without the parser. It is staged: parser and registry with legacy wire
  regressions; the full purpose, refusal, domain, canonicalization and audit-privacy tests;
  verifier rollout and consumer conformance at exact pins, against an explicit inventory of
  participating verifiers (an unknown or old member cannot join effect dispatch, and unrelated
  read-only services need no upgrade); then separately authorized v2 issuance, which stays off
  until every participating verifier pin carries the parser, since an older verifier refuses a v2
  grant as `grant.malformed`. The permit, finalization and replacement endpoints pass their own
  transaction, concurrency, crash, expiry, fork and replacement tests before effect dispatch is
  enabled. It is scheduled by passing evidence and a named owner (decision 9), never by a date or
  an invented release number. Oramasys adopts it by one exact-commit pin change through the
  existing qualification path, never a floating reference.
* **Decision 5, re-permit attestation.** An authenticated-channel statement only, as written.
  No consumer-signed record.
* **Decision 6, ratification.** Of the integrated contract: by exact commit, after independent
  review.
* **Decision 7, finalization event.** Accepted: the issuer counter advances on every
  finalization, so `R_f` and the event chain count finalizations as well as revocations.
  Issuer-signed timestamps and the section 8.2 witness alone are not adopted.

**Still open:**

* **Decision 9, release owner and milestones.** A named owner for the Phylax release and for
  each test milestone above, assigned by the operator. No owner is invented here.

* **Decision 8, containment numbers** (signed policy, section 3a). *Recommended:* request a
  finalization only while at least one third of the permit lifetime (30 seconds of 90) remains;
  open the breaker after 5 consecutive failures and probe every 15 seconds; alert after 2
  minutes of sustained unavailability. These are starting values, not safety boundaries: any
  value keeps the fail-closed behaviour, and a wrong one only changes how soon a refusal is
  returned.
