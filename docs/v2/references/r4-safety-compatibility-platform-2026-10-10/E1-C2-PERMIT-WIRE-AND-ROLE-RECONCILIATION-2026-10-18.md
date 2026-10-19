# E1 C2 (part 2): dispatch-permit wire fields and role reconciliation

Status: PROPOSED specification for independent review. Not ratified, no code, no wire change, not
authorization for T3. It fixes the wire choices that E1 section 13.4.1 leaves open and reconciles
the role and revocation text across sections 2, 11, 13.2, 13.4, 13.7 and 13.8. Part 1 is the
[purpose, version and refusal contract](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md).

**Next actions (read this first; the same list closes the document).**

1. Codex: a last exact-head re-review of this branch's head, read-only.
2. Operator: ratify this specification by exact commit if the re-review is clean (decision 6).
   Decision 9 is confirmed: Codex coordinates Phylax release evidence, Claude reviews it
   independently, the operator approves the pin.
3. Merge this record when CI is green. It is a proposal; merging it enables nothing.
4. After the merge, claim the queued implementation task: one conformance pull request per
   affected repository, tests failing first and mutation-proven, after freezing the items listed
   in section 5a. Nothing here is implemented, and nothing enables serving or issuance.
5. Later and separate: the operator's release and pin promotion, only on conformance evidence.

**Naming.** The durable-effects contract numbers its steps 1 to 6; its step 3 is the atomic
reservation and its step 4 is dispatch authorization. Section 13.4.1 splits step 4 into a permit
request, a permit decision and the consumer transaction. This record calls those **4.1, 4.2 and
4.3** and adds **4.2f**, the issuer finalization that fixes the issuer-owned authorization order
just before the consumer commits. "Step 4.3" is the consumer dispatch-authorization transaction.
No issuer call is ever made inside the 4.3 transaction: 4.1, 4.2 and 4.2f all complete first, so
there is still no distributed transaction.

## 0. The design in one page

* **Flow.** Four steps: 4.1 permit request, 4.2 permit, 4.2f finalization, 4.3 the consumer
  transaction that records the intent, consumes the use and writes the outbox item. No issuer
  call is made inside 4.3.
* **Who orders what.** The consumer orders its own facts at 4.3. The issuer orders its facts at
  4.2f, and the finalization is itself an event in the issuer's hash-chained log, so a clean
  rollback of the issuer shows up as a fork (decision 7).
* **Identity.** One durable `attempt_id` names a dispatch attempt from before the first call, so
  every ambiguous outcome can be named and an identical retry never mints a second object.
* **Time.** 90 seconds for permit and finalization, strict expiry, a 15-second minimum window
  before asking for a finalization (decisions 1 and 8).
* **Unavailability.** Only effectful dispatch needs the issuer, and it fails closed. Five
  independent safety controls, two operational ones that only shorten refusals, and one glossary
  of held, released and spent keep an outage from becoming a bypass (decision 3, section 3a).
* **Replacement.** A grant that has any permit gets a new one only through the attested,
  fenced, single-lineage replacement, and only for a transient delay, a cancellation or a loss
  (decisions 2 and 5).
* **Rollout.** One compatible Phylax release, staged by passing evidence, verifiers before
  issuance, promoted by the operator on evidence from a named maintainer (decisions 4 and 9).
* **Ratification.** By exact commit after independent review (decision 6).

## 1. Permit objects (proposed)

Encoding follows the recovery-grant rules: canonical JSON, ASCII keys, strings and safe integers
only, no nulls, six-digit UTC timestamps, unpadded base64url signature, at most 65,536 bytes.

**Permit request (4.1, consumer to issuer, authenticated channel; exactly 12 fields):** `grant_id`,
`grant_payload_digest`, `operation_id`, `request_digest`, `artifact_digest`, `reservation_id`,
`ledger_store_id`, `configuration_policy_epoch`, `authority_epoch`, `consumer_acked_through` (the
consumer's contiguous acknowledged issuer version when it asked), `attempt_id` (the consumer's
stable identifier of this dispatch attempt, generated and recorded durably before the first
issuer call and reused unchanged by every retry and by the finalization request) and
`requested_at`.
`artifact_digest` is **consumer-asserted**: the grant carries none, so the issuer cannot verify it.
It is signed as a binding the issuer saw, and the consumer re-verifies it at step 4.3.

**Permit (4.2, issuer-signed; exactly 21 fields):** `schema_version` (the integer 1), every request
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
`permit_digest`, `attempt_id` (the value the permit request carried; a different one is refused),
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

**Finalization event encoding.** The finalization event's body is exactly the one-field object
`{"finalization_id":"<opaque random identifier>"}`. It deliberately carries neither a grant nor
a consumer identifier. Its `event_digest` is the SHA-256 hexadecimal digest of the UTF-8 bytes of
the canonical JSON object:

```json
{"body":{"finalization_id":"<opaque random identifier>"},"kind":"finalization","previous_event_digest":"<previous digest>","version":<R_f>}
```

Canonical JSON means `json.dumps` with `sort_keys=True`, `separators=(",", ":")`,
`ensure_ascii=False`, and `allow_nan=False`; no whitespace or alternate representation is valid.
The event's detached issuer signature covers this digest and is not part of its preimage.
Both the issuer's append and the consumer's rule-5 verification construct precisely this object;
`finalization_id` is a field in the body, not the body or the digest by itself. For the first event
of a chain, `previous_event_digest` is 64 `0` characters.

**Finalization retry identity.** A finalization retry is validated on `permit_id`,
`permit_digest`, `attempt_id`, `reservation_id`, `ledger_store_id` and `authority_epoch`
against the stored permit and finalization; a changed value is `finalization.conflict`. A later
`requested_at` and a legitimately advanced `consumer_acked_through` never mint another
finalization. The issuer applies the current rollback floor, then returns the original signed
bytes with their original recorded request fields, so the one signed object and the one chain
event are preserved. The catch-up envelope is separate: it is not covered by the finalization's
signature, may differ per retry with the requested acknowledgement, and carries events that are
each signed by the issuer.

**Catch-up in the response, and an opaque shared stream.** The chain is issuer-wide, so a consumer
would otherwise have to acknowledge every other grant's and consumer's finalization events before
it could finalize, and heavy traffic would stall it inside its 90-second window. The finalization
response therefore also carries the issuer-signed events above the request's
`consumer_acked_through` up to `R_f`, bounded by signed policy; a larger gap is refused as
`finalization.catchup_required` and the consumer catches up on the stream first. On first
admission the issuer decides catch-up feasibility before appending the finalization event, so a
`finalization.catchup_required` refusal creates no event and no finalization. The consumer
ingests them contiguously and checks them for divergence exactly as it checks stream events.
Finalization events on the shared stream carry no grant or consumer identifier: only the version,
the kind, `finalization_id` (an opaque random identifier) and the previous digest.

**Capacity and retention.** There is one chain and one serialization domain per issuer, so
finalization throughput is bounded by one issuer transaction and one signature each. No ceiling is
claimed here, sharding is not adopted, and the catch-up bound is a signed-policy value measured
before the permit path is enabled. Retention follows the seven-year audit retention of E1 section
13.3 for signed permit and finalization bytes, chain events, `aborted` rows, audit records and the
section 8.2 witness. A consumer needs only an issuer-signed chain checkpoint (version and digest)
at its acknowledged point plus the events since; events below the lowest acknowledged version
across consumers may be pruned only after such a checkpoint is published.

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
own event, and the response carries the events below it, so no stream round trip is needed
before step 4.3. The counter is issuer-wide, so nothing keyed to its
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
   the one authoritative store. The fence read, the use consumption and the intent write are one
   consumer transaction at serializable isolation or under the attempt's row lock.

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
restarts, and the tests cover boundary offsets and restart. The consumer clock must stay within
the signed-policy skew; a backward step is handled by the contract's clock policy (section 8.2)
and quarantines dispatch until reconciled. See the stranding risk in section 3.

**Retry identity (proposed).** A unique `grant_id` stops a second row but does not prove that a
repeat request is the same request. The issuer therefore persists a **binding digest** with the
permit: the canonical digest (the manifest encoding rules) of the object made of exactly these
nine immutable request fields: `grant_id`, `grant_payload_digest`, `operation_id`,
`request_digest`, `artifact_digest`, `reservation_id`, `ledger_store_id`,
`configuration_policy_epoch` and `authority_epoch`. On any request for a grant that already has a
permit, the issuer recomputes the digest and compares it with the stored one:

* **Equal binding and equal `attempt_id`:** an identical retry. The stored permit is returned
  unchanged, including its original `issued_at`, `expires_at` and `requested_at`. An expired
  stored permit is not revived.
* **Different binding, same `attempt_id`:** a conflicting request for the same grant. It is
  refused with a closed permit refusal (proposed name `permit.conflict`, to be fixed in the
  integrated schema review). The stored permit is **not** returned, nothing is created or
  changed, and a sanitized audit record may be written.
* **A new `attempt_id` on a grant that already has a permit**, with an equal or a changed
  binding: refused as `permit.conflict` while the grant's latest permit is nonterminal,
  including one that has expired but is not yet abandoned. If the latest permit is `abandoned`
  and has no successor, the request is the successor request. The issuer validates it as a fresh
  issuance (every 4.2 check, so a new reservation is allowed) and, in one conditional
  transaction, records `replaces_permit_id` itself. A concurrent second successor request loses
  on the unique `replaces_permit_id`. So an expired permit never lets an ordinary request mint a
  second one, and no wire field is needed to name the predecessor.

`requested_at` and `consumer_acked_through` are **excluded** from the binding digest, and so is
`attempt_id`, which leaves the nine fields unchanged but is part of retry identity. `requested_at`
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

A successor is needed only when the permit is expired, abandoned or lost, or the attempt is
cancelled (decision 2). The attested transition is **abandon**: it marks the prior permit, and any
finalization, `abandoned`, and never requires a successor. A successor is issued only when a new
attempt asks for one, as above. The causes it accepts are a transient delay, a cancellation
(including a grant revoked after the permit was issued) and a loss (including an admission that
won an abort race). It requires the durable fence and proof that step 4.3 did not commit, together
with a release-pending record for the reservation; it does not require a release that has already
happened, because the release is authorized by the abandon. The proof is a **consumer
attestation** over the authenticated channel that names the `attempt_id`, the `permit_id`, the
consumer's fencing epoch, the fence and non-commit evidence, the release-pending record and a
statement that no intent for that permit exists. The issuer cannot see the consumer's store, so it
records the attestation as audit evidence and does not claim to verify it; the safety does not
rest on it. The issuer conditionally records the abandon, and an identical abandon retry returns
the recorded outcome. The consumer durably records the authenticated abandon outcome and performs
the reservation release in the same local transaction.

Five invariants carry it. First, the consumer commits a terminal fence for the attempt before
attesting (the one fence object, also called the abandonment record). Fence creation, together
with its check that the attempt has not committed, takes the attempt's row lock, the same lock
step 4.3 takes: 4.3 reads the fence, consumes the use and writes the intent in one transaction
under that lock, so exactly one of fence and commit wins. The issuer never sees the fence, so a
finalization already committed at the issuer stays live there; it is safe because 4.3 refuses a
fenced attempt. Second, the issuer refuses a finalization once the permit is `abandoned`,
re-reading the permit state under the permit's row lock. Third, abandon and successor issuance are
each conditional: abandon applies only while the permit is nonterminal and has no successor, and a
successor insert applies only while the predecessor is `abandoned` and has none, so of two
concurrent attestations or two concurrent successor requests one wins and the other writes
nothing. Fourth, issuance and finalization reject a `ledger_store_id` different from the signed
grant's, the authenticated capability is scoped to the authorized consumer, and a restored or
alternate consumer store cannot independently authorize the same grant (it stays quarantined until
the section 8.2 reopen conditions hold). Fifth, the grant's consumed-use record is unique in one
authoritative store shared by competing consumers. A wrong attestation cannot cause a second
dispatch: the consumer consumes the grant's single use inside 4.3, and refuses any later permit or
finalization for a use it has already consumed, whatever the issuer holds.

**Issuer storage (proposed).** One table `dispatch_permits` with `permit_id` primary key,
`grant_id`, `attempt_id` (unique), `binding_digest`, `ledger_store_id`, `reservation_id`,
`request_digest`, `r_p`, `consumer_acked_through`, `requested_at`, `issued_at`, `expires_at`,
`permit_bytes` (the canonical signed permit), `finalization_bytes` and `finalization_id` when
present, a state and an optional `replaces_permit_id`. The stored states are `issued`,
`finalized`, `abandoned` and `aborted`. An `aborted` row is the abort tombstone: it holds the
`attempt_id`, the `grant_id`, the operator disposition reference and no permit bytes. Because
admission and abort both insert a row under the unique `attempt_id`, exactly one of them can win,
with no reliance on isolation level. Expiry is computed from `expires_at` and is never the
authority; a sweep may record `expired` for audit only, so an expired permit still counts as
nonterminal until it is abandoned. Three constraints, which count only rows that hold a permit,
enforce the rules in the database and not only in code: at most one original permit (no
`replaces_permit_id`) per `grant_id`; at most one nonterminal permit per grant; and
`replaces_permit_id` unique where present. A new attempt on a grant whose only row is `aborted`
has no permit and proceeds.

**Issuer serialization (proposed).** Every issuer transition for a grant (admission, abort,
finalization, abandon, replacement) takes that grant's row lock first. Finalization then takes the
chain-head lock, and version assignment, the catch-up bound check and the append happen under that
one head lock, so two finalizations cannot compute the same `R_f`, fork the chain or return a
stale bundle. Locks are always taken in that order, grant then head, so they cannot deadlock.

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
| Consumer crashes after receiving the permit, before step 4.3 commits | On restart the consumer knows from its own store that 4.3 did not commit; it continues to 4.2f, and an unexpired permit with its finalization may be used once |
| Permit expires before step 4.3 (including benign clock skew) | Refused and recorded with an expiry reason. A successor is allowed only after the consumer attests, from its own store, that 4.3 never committed (fence committed, release pending), and only before the grant's own expiry, and only when the attested cause is a transient delay, a cancellation or a loss; the issuer records the attestation and does not claim to verify it. Any other cause, and any unknown or pending outcome, is treated as spent and the grant remains unavailable (decision 2, section 6) |
| Step 4.3 committed, crash before the outbox send | The outbox protocol of section 4 governs; the attempt is `unknown` if a send may have started |
| Permit presented for another reservation, request digest, `artifact_digest` or `authority_pair` | Refused; no state change |
| Permit replayed after step 4.3 recorded it | Refused as already recorded |
| Revocation committed at the issuer before finalization | Refused by the issuer finalization transaction. The permit that was issued can never finalize and expires within its lifetime; the reservation is released through the attested abandon (cause: cancellation) once the fence is committed, and no successor is issued |
| Revocation committed after finalization | Post-authorization; the finalization receipt fixes the issuer-owned authorization order and nothing claims the completed authorization undone |
| Finalization committed, response lost | An identical request (same `permit_id` and `attempt_id`) returns the stored finalization while it is unexpired; no second `R_f` is recorded. After its expiry it is not returned as usable: the retry is refused as expired and the attested abandon applies |
| Finalization requested for a different `attempt_id`, binding, expired, abandoned or unknown permit | `finalization.conflict` or a permit refusal; nothing changes and nothing is returned |
| Consumer crashes after receiving the finalization, before step 4.3 commits | The consumer knows from its own store that 4.3 did not commit. The finalization is used only if still unexpired; otherwise the replacement path with an attestation applies |
| Finalization expires before step 4.3 | Refused at 4.3; the same replacement path applies, never a silent retry of 4.3 |
| Step 4.3 already consumed the grant's use, and the issuer later issues or holds another permit | The consumer refuses it: the consumer-owned single use is the backstop against a second dispatch |
| Issuer restored to an older state, so its counter is below `consumer_acked_through` | Permit refused; quarantine until reconciled against the consumer's stored versions |
| Issuer restored from a clean older snapshot after the consumer acknowledged later events, before the finalization request | The request's `consumer_acked_through` exceeds the restored counter: refused at 4.2f, and by rule 5 at step 4.3 if a finalization is returned anyway |
| The same restore, but the consumer acknowledges the lost events only after sending the request | The issuer's finalization event reuses a version the consumer holds with a different digest: divergence, refused at step 4.3 and quarantined. A digest of an existing event could not show this, because a snapshot has the same history up to its own point |
| Issuer restored, and the consumer never acknowledged the lost events | Not visible at the consumer, which has nothing to compare. Covered by the issuer's recovery quarantine and the witness of E1 section 8.2, not by this protocol |
| Issuer rolled back between permit and finalization, so `R_f` is below the request's `consumer_acked_through` or below `R_p` | Finalization refused at 4.2f; a finalization that is nevertheless returned is refused at step 4.3 rule 5. Either way the issuer stays quarantined and nothing is consumed |
| First permit request: the response is lost and no `permit_id` is known | The consumer retries identically under the same `attempt_id` inside the deadline; the issuer returns the stored permit or decides once. No second permit |
| Abort races a delayed admission, in either transaction order, or a late response arrives | Exactly one wins. Admission first: the abort returns the existing record and release is not authorized. Abort first: later admission is refused and a late response is dropped by the consumer's fence. Never both records |
| A signed refusal arrives while an earlier permit, finalization or response is outstanding | The refusal governs only its named phase and request; known state is retained and nothing is released on the refusal code |
| Finalization retry after a lost response with a higher acknowledgement, a later `requested_at`, or after a restart | The original signed bytes are returned, exactly one finalization and one event exist; a changed binding is `finalization.conflict` |
| First finalization needs more catch-up than the bound | `finalization.catchup_required`; no event and no finalization are created; a retry after stream catch-up admits once |
| Admission cannot be proved by the deadline | Held, spent and quarantined; no attested release; leaves only by authenticated reconciliation by `attempt_id` under an operator disposition |
| Equal binding, different `attempt_id`, while a nonterminal permit exists | `permit.conflict`; a replacement only by the attested path |
| Issuer unreachable, permit forged, unbound or expired | Dispatch refused; reported unavailable, never valid; the layered containment of section 3a applies |

## 3a. Issuer unavailability: layered containment (decision 3)

Decision 3 scopes the issuer dependency to effectful dispatch. That scoping holds only if no
configuration, classification mistake or bug can create an effect path that skips the permit. The
controls below are independent, so one failing still leaves dispatch refused. The terms are used
exactly as defined here:

| Term | Meaning |
| --- | --- |
| held | The attempt's reservation is kept and not freed |
| released | The reservation is freed, only on a proof: never transmitted, an abort that won, or an attested non-commit under the fence |
| spent | No new attempt for the grant is started until a proof reopens it. It does not mean the use was consumed: only step 4.3 consumes the use, never a timeout and never the issuer |
| quarantined | Not a separate state: held and spent, with an alert |
| fence | The consumer's one terminal record for an attempt (also called the abandonment record), checked by step 4.3 and by late-response handling |
| lost | A permit or finalization the consumer knows exists, or that an abort found, but whose object or record it cannot use |
| terminal | A permit state of `abandoned` or `aborted`; `finalized` is nonterminal and stays retryable |

The governing rule:
**unavailability is a state, never a verdict.** When the issuer cannot be reached, or its answer
cannot be used, the only legal outcomes are to refuse and report unavailable and to hold the
reservation. What may follow depends on what can be proved, as item 4 separates.

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
4. **Ambiguity is not denial, and each outcome is its own state.** A timeout, a dropped
   connection, an unsigned or malformed response, or one that fails verification is *unknown*,
   not an issuer refusal. The consumer records the attempt under its `attempt_id` before the
   first call, so every outcome below can be named even when no `permit_id` exists yet.

   * *Signed issuer refusal* (conflict, revocation): a verdict on the named phase and the exact
   request. It creates no new authority and does not prove the absence of an earlier permit,
   finalization or consumer intent. Known state is retained, and the reservation is released only
   through the fenced non-commit procedure or the serialized abort below, never on the refusal
   code alone.
   * *Admitted, response lost:* an identical retry inside the deadline returns the stored permit
     or finalization, never a second one. A permit request is identical when binding and
     `attempt_id` match; a finalization request when `permit_id` and `attempt_id` match.
   * *A permit or finalization the consumer holds and cannot use* (expired, abandoned, lost):
     the replacement path of decision 2, by attestation naming the `attempt_id` and the
     `permit_id`.
   * *Admission cannot be proved* (no verified response by the deadline, so a request may have
   been admitted unseen): held, spent and quarantined. This is not an attested-release case, and
   it leaves quarantine only by reconciliation, never by a timeout. The read-only,
   operator-authenticated lookup by `attempt_id` is for inspection and can never authorize a
   release.

      The release path is one ordered transition. (1) The consumer first commits the fence for the
   attempt. (2) The operator then requests an issuer **abort** bound to that attempt, the grant
   and the authorized consumer. (3) In the same issuer transaction as admission, under the unique
   `attempt_id`, the issuer rechecks that no permit or finalization exists and only then records
   the `aborted` row. If admission won, the issuer returns its existing record: the abort does not
   authorize release, and the attempt continues as a *lost* permit, abandoned under the fence by
   the attested procedure of section 1, which does authorize it. If the abort won, every later
   admission for that `attempt_id` is refused, a late response is dropped by the fence, and the
   reservation may be released once the consumer durably records the authenticated abort outcome;
   an interruption leaves it held, and reconciliation retries idempotently. A lookup followed by
   an unconditional tombstone is not allowed: a delayed admission could commit between the two.
   Whichever order occurs, exactly one wins. After an abort that won, a new attempt for the grant
   may proceed under a new `attempt_id`, because the old attempt is fenced and tombstoned and the
   grant's use was never consumed.

   **Reconciliation is an explicit transition.** The actor is an authenticated operator acting for
   the authorized consumer scope. The input is the `attempt_id` and the grant. The outcomes are: a
   permit or finalization found, which is a *lost* case and goes to the attested abandon; nothing
   found, which goes to the abort above; or the issuer unreachable, which leaves the attempt
   quarantined and creates no new authority. There is no timeout path. Quarantine is bounded by
   the one active attempt a consumer may hold per grant, so an outage can quarantine at most the
   attempts in flight at its onset; the operator drains them with a bulk disposition that applies
   the same conditional abort to each attempt independently, and the alert repeats until the queue
   is empty.
5. **One deadline.** An attempt's deadline is its permit's `expires_at`, or, until a permit is
   held, the attempt's start plus the permit lifetime. The deadline bounds admission and
   finalization only: authenticated reconciliation, abort and abandon calls remain allowed
   after it under their own bounded recovery-call timeouts (signed policy), because forbidding
   them would strand a held reservation. They never extend a permit's or finalization's
   validity and never authorize dispatch. An attempt that ends locally as unavailable is
   released at once if its durable record shows the first call was never transmitted, and is
   otherwise held, spent and quarantined. A `finalization.catchup_required` loop is bounded to
   one stream catch-up per attempt, after which the attempt ends as unavailable. Every issuer
   call carries the remaining budget as its timeout, retries are identical requests with
   bounded backoff, and no new admission or finalization request is made for that permit after
   the deadline. A finalization is requested only while at least the minimum window of decision
   8 remains; otherwise the attempt ends locally as unavailable, so a slow issuer cannot hand
   over a finalization that is dead on arrival.
6. **Outage containment** (operational: it only shortens refusals and carries no safety
   guarantee). Per issuer and consumer scope, the consumer keeps a circuit breaker.
   After the threshold of decision 8 consecutive authenticated transport-or-verification
   failures, effectful dispatch is refused at once without calling; a signed issuer refusal is
   not a failure. One half-open probe per interval tests the issuer, and the breaker resets only
   after an authenticated, usable response. It is consumer-local and only shortens a refusal; it
   never relaxes a check. Non-effect operations never consult it.
7. **Visible, never silent** (operational, as item 6). The consumer reports
   `dispatch.issuer_unavailable`, a consumer-side status that is not one of the issuer's closed
   `permit.*` refusals, writes a sanitized audit record, and raises an alert after the
   sustained-outage threshold of decision 8. It is never reported as valid, and never as
   pending-as-success.

**Failure-injection tests (proposed, to be written failing first).** Issuer down at 4.1;
response lost at 4.2 and at 4.2f (identical retry returns the stored object); issuer down after
finalization so the finalization expires before 4.3; a slow issuer past the deadline; an unsigned,
wrong-key, malformed or other-reservation response; a restore mid-attempt (divergence, section 1);
breaker open, half-open and closing; an unregistered `effect_class` treated as effectful; an
outbox insert without a permit refused; a non-effect operation proceeding while the issuer is
down; an attempt after its deadline refused; interleaved grants, where one grant's finalization never
invalidates another's permit; abort against admission in both orders and with a delayed
response; a refusal after issuance; finalization retries (higher acknowledgement, changed
binding, catch-up then retry, restart); and every refusal above leaving the reservation
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

## 5a. Implementation delta and adoption (not applied here)

The merged `decide_permit` in the runtime repository is an isolated helper with fake-store tests
and no production caller. It predates this text and does not implement it: its request has neither
`attempt_id` nor `consumer_acked_through`, so it neither binds nor floor-checks an
acknowledgement; its stored versions are opaque strings where the wire needs validated safe
integers; its store lookup returns only nonterminal permits, so with terminal history hidden an
ordinary request mints a second permit; and it has no durable transaction, schema, finalization,
catch-up, abort, replacement or consumer integration. Nothing here is a claim about the current
runtime.

Ownership stays split. The issuer's signing, persistence and local transactions belong to Phylax.
Oramasys owns consumer attempts, fences, use consumption and the outbox, reaching the issuer
through ports; the neutral helper must not become a second authority store.

Before implementation, freeze: the canonical event and envelope bytes, the field types and limits
(safe integers, sizes), the refusal vocabulary, key selection and the resource bounds. The
conformance work is one coherent pull request per affected repository with matched contract
vectors and cross-repository interop, covering fresh and existing schemas, all three uniqueness
constraints, the `aborted` row, real two-connection races, terminal history, finalization,
replacement, expiry and fork cases, catch-up, the outbox sender, and crash and restart recovery.
Safety-critical guards are mutation-proven. It starts after this record merges and is tracked as a
queued follow-up.

## 6. Operator decisions

**Decided 2026-10-19 (operator):**

* **Decision 1, lifetime.** 90 seconds for the permit and the finalization, uniform across
  effect classes. No per-class override is adopted; one needs a new decision.
* **Decision 2, expired never-committed permit.** Assume spent first. A replacement is allowed
  only on the consumer's authenticated attestation that the cause is a transient delay, a
  cancellation or a loss. An unknown or pending outcome, including an admission that cannot be
  proved, stays spent, held and quarantined until reconciled (section 3a); it is not an
  attested-release case, but once reconciliation finds a permit the ordinary replacement path
  applies.
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
  review. Implementation conformance gates adoption and enablement of the permit path; it is not
  a prerequisite for ratifying the specification.
* **Decision 7, finalization event.** Accepted: the issuer counter advances on every
  finalization, so `R_f` and the event chain count finalizations as well as revocations.
  Issuer-signed timestamps and the section 8.2 witness alone are not adopted.
* **Decision 8, containment numbers** (signed or measured policy, section 3a). A 15-second
  minimum window before requesting a finalization (30 seconds would consume the whole nominal
  window of a consumer clock 60 seconds fast). The breaker opens after 5 consecutive
  authenticated transport-or-verification failures, takes one half-open probe per issuer and
  consumer scope every 15 seconds, and resets only on an authenticated usable response. Alert
  after 2 minutes of sustained unavailability. These are starting values, not safety
  boundaries: any value keeps the fail-closed behaviour.
* **Decision 9, release authority and evidence.** Confirmed by the operator on 2026-10-19: Codex
  coordinates the Phylax release evidence and Claude reviews it independently; the operator
  remains the release authority and approves the pin, and a reviewer's endorsement cannot promote.
  Milestones, in order: the corrected contract and an ownership matrix; Phylax producer
  transaction and wire evidence; an Oramasys consumer vertical slice; paired exact-commit interop
  with independent review; operator promotion.

**Still open:** nothing that blocks ratification. The remaining work is the implementation
conformance in section 5a.

## 7. Next actions

1. Codex: a last exact-head re-review of this branch's head, read-only.
2. Operator: ratify this specification by exact commit if the re-review is clean (decision 6).
   Decision 9 is confirmed: Codex coordinates Phylax release evidence, Claude reviews it
   independently, the operator approves the pin.
3. Merge this record when CI is green. It is a proposal; merging it enables nothing.
4. After the merge, claim the queued implementation task: one conformance pull request per
   affected repository, tests failing first and mutation-proven, after freezing the items listed
   in section 5a. Nothing here is implemented, and nothing enables serving or issuance.
5. Later and separate: the operator's release and pin promotion, only on conformance evidence.
