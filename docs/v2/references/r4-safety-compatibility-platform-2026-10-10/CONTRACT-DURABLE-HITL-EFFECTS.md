# Contract — durable human approval and effect protocol

**Status:** proposed under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Design only; record and function names are proposals to freeze at T0. Plan slice:
[T3](PLAN-R4-EXECUTION.md#t3--approval-and-effect-transaction-spine). Builds on the
[refusal/HITL contract](../2026-10-09-compatibility-refusal-hitl-contract.md), which it
does not replace.

## 1. Storage

One host-local transactional SQLite store, owned by Oramasys, behind a versioned
interface. It holds immutable events and transactional current-state projections.
Version transitions use compare-and-swap (CAS); constraints and audit/outbox entries
commit in the same transaction. An append-only event file alone cannot provide CAS.
Do not share the file over a network ([multi-host](CONTRACT-MULTI-HOST-STAGES.md)).

## 2. Records and identities

| Record | Required binding |
| --- | --- |
| Approval request | Principal/audience, logical operation, exact request digest, artifact set, exception IDs, requested scope |
| Decision/grant | Request ID, authenticated decision maker, decision, UTC issuance/expiry, use limit (**exactly one**; multi-use grants are not defined), revocation version |
| Reservation | Operation and grant references, attempt ID, expected versions, fencing epoch, deadline |
| Effect intent | Durable run ID + logical operation ID, effect kind, provider identity/key, request digest, dispatch status |
| Effect receipt | Confirmed applied, confirmed not applied, or unknown; provider evidence; reconciliation disposition |

Identity rules:

- A **logical operation ID** is stable across transport retries. Distinct loop iterations
  and branch activations get distinct IDs; restarting the same activation reuses its ID.
- An **attempt ID** is separate and changes per delivery attempt.
- Reusing an operation ID with changed content is a **conflict**, not a retry.
- A forked run has a new run identity. Old receipts cannot authorize new external writes.
- Only exceptions classified overridable enter this path. Invalid authentication,
  impossible hardware, unsafe endpoints and uncontained SDKs are non-overridable.

Grant state and effect state are **separate machines**. A used grant is not proof of
provider success; provider success is not proof the graph state committed locally.

## 3. State machines

### Grant

`requested → granted → (reserved) → consumed` with terminal side exits
`denied`, `expired`, `revoked`. A denial, expiry or revocation never becomes approval
after restart. Renewal creates a new audited version and cannot expand scope.

### Effect

`intended → reserved → dispatch_authorized → handed_off → provider_accepted →
receipt_recorded → applied_to_state`, with outcome branches `confirmed_applied`,
`confirmed_not_applied` and `unknown`. `unknown` is blocking: it leaves only by
reconciliation or an explicit incident disposition that records evidence.

Persist the separate milestones **authorized**, **handed off** and **provider accepted**.
A revoked queued intent not yet handed off is **suppressed**, never labelled remotely in
flight.

## 4. Dispatch protocol and the linearization boundary

1. Admit the exact artifact and request. Refuse non-overridable failures. Persist an
   eligible pending exception request before exposing it to the operator.
2. Authenticate the human decision. Store approve or deny and a narrowly scoped grant. No
   UI Boolean or framework resume value is a grant by itself.
3. Reserve atomically: validate scope, request and artifact digests, expiry, use count,
   current authority versions and worker ownership. Competing consumers conflict.
4. Revalidate every mandatory gate at **dispatch authorization**: scope, request and
   artifact digests, **grant expiry** (stored UTC plus the high-water rule in §5),
   revocation version, authority versions, fencing epoch and worker ownership. In one
   transaction record the dispatch intent, consume the use and write an outbox item.
   **This transaction is the linearization point for revocation versus dispatch.**
5. Send only the recorded intent through the qualified transport. Revocation before step 4
   blocks dispatch. Revocation after it marks authorized in-flight work, requests
   cancellation where supported and blocks all subsequent operations.
6. Persist the provider outcome separately from applying its result to graph state. Commit
   the result and checkpoint once, or keep a recoverable handshake record.
7. Retry only after proof of non-application or qualified provider dedupe. An unknown
   outcome stays blocked.

Immediately before I/O the transport rechecks current permit, cancellation, fencing and
endpoint admission. That last local check cannot be atomic with a remote socket write: a
revocation after handoff is an in-flight race handled by cancellation and reconciliation,
and no accepted effect is claimed undone.

Expiry never releases an uncertain reservation for automatic reuse. A timeout is not
evidence the provider did nothing. Operator remediation records evidence; it cannot invent
non-application or bypass a non-overridable security check.

## 5. Clock policy (proposed; freeze at T0)

Expiry uses UTC wall-clock time recorded in the store, plus a stored high-water-mark of
the latest accepted timestamp. If the current clock reads **earlier** than the
high-water-mark, treat grants as not valid (refuse and alert) rather than extending them.
In-process deadlines use a monotonic clock. Restart recomputes expiry from stored UTC, not
from process uptime.

## 6. Crash windows and recovery

| Crash boundary | Recovery action |
| --- | --- |
| Before durable reservation | No dispatch authority exists |
| After reservation, before dispatch intent | Revalidate reservation; prove no dispatch before restoring uses |
| After dispatch intent, before known send | Uncertain unless transport evidence proves non-application |
| After handoff, before provider acceptance known | Uncertain; reconcile the stable provider key |
| After remote acceptance, before receipt | Reconcile stable provider key; never blindly resend |
| After cancellation requested, before outcome | Uncertain until reconciliation; cancel is a request, not rollback |
| During reconciliation | Reconciliation is idempotent; resume it, do not restart the effect |
| After receipt, before state commit | Apply the recorded result once; do not call the provider again |
| After state/checkpoint commit, before event publication | Redeliver the outbox projection; do not rerun the node |

An application database and a remote provider share no transaction. A hash chain aids
tamper detection but cannot make those writes atomic.

## 7. Acceptance tests (named, to fail first)

Single-use under concurrent consumers; wrong request digest; pending request survives
restart; denied, expired and revoked never become approved; changed artifact invalidates a
grant; operation-key reuse with a different request is a conflict; corrupt record is
rejected; UTC expiry holds after restart and after a backward clock jump; uncertain
reservation is retained; revocation on each side of step 4; in-flight receipt is never a
false rollback or a silently freed grant; backup/restore and redaction.

## 8. What this contract does not give

No universal exactly-once execution. No production transport (that is
[the transport contract](CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md)). Grants alone enable
nothing.
