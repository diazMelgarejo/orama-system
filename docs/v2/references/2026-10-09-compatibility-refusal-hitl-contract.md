# Durable refusal and HITL approval contract — draft

**Status:** new design contract; not implemented or ratified by publication.
**Owner:** Oramasys upper application layer; Agate, Phylax and Telos retain
their existing policy authority. Extends
[historical HITL accountability](HUMAN-IN-LOOP-ACCOUNTABILITY.md), whose in-memory
single-use tracking is insufficient for crash recovery. Canonical companion:
[revision 3 execution index](loop-graph-compatibility-2026-10-09/README.md).

## Required runtime behavior

All applicable hardware, authorization and egress checks run before effects.
Execute automatically only if every required authority permits the operation.
Any disallowance produces a sanitized structured refusal and an operator-facing
escalation request. Independent admitted work may continue. Noninteractive
requests stay denied/pending, never self-approve or wait indefinitely.

Approval does not bypass policy: it authorizes a precisely scoped supported
exception or policy change. Revalidate every gate afterward, before each effect,
on resume and on relevant target/request changes. Physical impossibility,
invalid authentication or a non-overridable invariant requires remediation;
an approval flag cannot turn it into an allowed operation.

## Bound records and durable state machine

| Record | Required binding |
| --- | --- |
| Refusal | Durable run/thread ID, logical operation ID, canonical request digest, upstream API/version, authority/policy revision, returned denial rules, remediation and escalation state |
| Operator decision | Authenticated operator identity, refusal reference, exact request digest, policy revision, bounded action/resource scope, timezone-aware issue/expiry interval, use limit, decision and signature/provenance |
| Reservation | Approval reference, operation/request identity, durable atomic reserved-use accounting, effect identity and unknown-outcome state |
| Outcome | Reservation reference, revalidation evidence, provider reconciliation/idempotency reference, completion/failure and sanitized evidence digest |

Persist decision and use accounting transactionally. A unique operation identity
prevents multiple workers consuming the same grant concurrently. Do not release
a reservation after a crash unless non-application is proved. Unknown remote
completion is `reconcile-required`, not unused approval. Revocation and changed
policy/request invalidate execution until a new scoped decision is obtained.

Effect identity is `(durable_run_id, logical_operation_id)` bound to effect kind
and canonical request digest. Retries share it; attempts get separate IDs.
Never derive authority from model output or natural-language instructions.

## Release gate

Test authentication, wrong scope/digest/revision, expiry, revocation, concurrent
consumption, restart/replay, changed target, multiple independent denials and
crashes both before and after remote application. Validate persisted schemas,
callers, transports, lifecycle and provider reconciliation as one vertical slice.
Export no tokens, raw content or concrete local topology (doc 47).

Until that vertical slice passes, every override path is denied/pending. This
document is not a security implementation and adds no bypass to v1 or Core.
