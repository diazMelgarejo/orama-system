# Contract — dispatch gate: commit publication, batch reservation, adjustment grants

**Status:** frozen design contract by operator direction (2026-10-10 UTC) under
[D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md). It closes the three freeze
blockers in [revision 3](P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md) §4 and §6.
Design only: no code, pin or capability is enabled by this file. Names are the T0 freeze
candidates; implementation still needs failing tests, review, qualification and human merge.

Owners do not move. Core supplies the neutral `DispatchGate` protocol and the one
scheduler. Oramasys implements the gate and owns the single-writer ledger and terminal
outcomes. Phylax decides adjustment authority. Telos secures any endpoint involved. The
[clock policy](CONTRACT-DURABLE-HITL-EFFECTS.md#5-clock-policy-approved-freeze-implementation-details-at-t0)
governs every expiry below.

## 1. Commit publication (three steps)

SQLite and the in-memory graph delta are **not one atomic transaction**. Neither a
synchronous SQLite call inside the scheduler (unbounded lock and fsync latency) nor an
in-memory snapshot alone (no durable authority) is sufficient. The boundary is:

1. **Prepare (await, durable).** The single ledger writer records a `CommitIntent`
   bound to `run_id`, `attempt_id`, `hold_id`, the result digest and the fence epoch.
   No intent, no publication.
2. **Publish (synchronous, no `await`).** Recheck the locally observed lease authority
   and expiry, stop state, delivery health and that the current fence epoch equals the
   intent's epoch. If all hold, publish the prepared delta to graph state in the same
   synchronous section. If any fails, do not publish; the attempt's charge stays and the
   outcome is refused or `unknown`, never success.
3. **Settle (await, idempotent).** Record settlement for the hold before the run may
   dispatch further work. A duplicate settlement for the same attempt returns the
   recorded result.

| Crash window | Recovery |
| --- | --- |
| Before intent | Hold and start marker exist; attempt is `unknown`, conservative hold kept |
| After intent, before publish | Same; the intent proves no publication authority was used |
| After publish, before settle | Same; local state was not durable (no T5), so nothing resumes |

Recovery never replays the attempt or the run. Remote revocation is not atomic with local
publication: the window between the last observed revocation epoch and publication is
stated in evidence, not hidden.

Tests: crash at each window by subprocess kill; stale epoch at publish; expiry between
prepare and publish (injected clock); duplicate settlement; publish without intent refused.

## 2. Batch reservation for fan-out

Before Core starts **any** branch of a fan-out step, the gate reserves the whole proposed
branch batch in **one ledger transaction**: `reserve_batch(run_id, batch_id, attempts)`.

- All or nothing. Insufficient run or lease budget creates no new holds, no charges and no
  branch execution; the gate returns `refuse(budget)` for the batch.
- Already executed work remains charged; refusal adds nothing to any branch in the batch.
- `batch_id` is idempotent: the same payload returns the same holds; a changed payload
  under the same `batch_id` refuses.
- Each branch then follows §1 independently. R3 settle-all semantics, name-ordered folds
  and the single scheduler are unchanged; a reducer or custom join runs only after its own
  single-attempt reservation.
- Unstarted holds after a crash are released only by the single writer after the fence
  epoch advances, proving no dispatch can race the release.

Tests: insufficient budget asserts **no incremental charge to any branch in the failed
batch**; crash before dispatch; concurrent contention across runs sharing a limit; duplicate
and conflicting `batch_id`; partial-start crash keeps started branches `unknown`.

## 3. Adjustment grants for unknown holds

Only an authenticated adjustment may settle or release an `unknown` hold. Nothing is
released automatically, edited or deleted.

**Authority.** Phylax issues the grant for an authenticated principal from the configured
identity mechanism (category only; no identity literals in tracked files). Telos secures
any network endpoint used to obtain or verify it. Oramasys validates and consumes it.

**Grant fields.** Unique single-use `grant_id`; principal; `run_id`; `hold_id`; adjustment
kind (`settle` or `release`) and integer units; evidence digest; expected fence epoch;
payload digest over all of these; issued and expiry UTC; issuer attestation reference;
revocation reference.

**Consumption (one ledger transaction).** Verify the attestation through the Phylax
interface; refuse if expired, revoked as last observed, the payload digest differs, the
epoch differs from the hold's current fence epoch, the units exceed the hold's
**remaining balance**, or `grant_id` was already consumed. The remaining balance is the
held units minus every prior settlement and adjustment, computed inside the same ledger
transaction as the consumption, so two distinct grants can never release more than the
hold reserved. Then append the adjustment event and the grant consumption together. The
original `unknown` event stays.

- Identical retry (same `grant_id`, same payload): returns the recorded result.
- Changed payload under a consumed or known `grant_id`: refuses.
- Release requires that fencing proves no dispatch or late commit can race it; uncertain
  external effects need explicit evidence and disposition, not a budget refill.
- Expiry alone does not prevent replay; single-use consumption does.

If Phylax lacks this capability, an owner contract comes first and production refuses
every adjustment until it exists.

Tests: two distinct grants that together exceed the hold (second refused); replay of a
consumed grant; altered units, hold or epoch; expired and revoked grants; concurrent
consumption of one grant; release racing a late commit; missing Phylax.

## 4. What this contract does not give

No T3 effect grant, T4 provider transport, T5 continuation, remote worker, exactly-once
delivery or proof that cancelled work stopped. A refusal never disguises an unknown
in-flight effect as safe.
