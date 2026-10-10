# Contract — durable human approval and effect protocol


**Status:** approved design contract under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
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
