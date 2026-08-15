# Contract Migration Vertical-Slice Method

Use this method when a change alters a persisted value, return shape, event
envelope, transport payload, lifecycle hook, or other contract that crosses a
module boundary. A correct local edit is not enough: the migration is complete
only when every affected layer agrees on the same contract.

## When To Apply It

Apply this method before changing any of the following:

- database columns, constraints, identifiers, or serialized state;
- function return values, tuple positions, result objects, or exceptions;
- API, SSE, queue, or worker message envelopes;
- auth, middleware, startup, shutdown, or retry behavior;
- compatibility adapters and callers that unpack or reconstruct the value.

For a narrow internal refactor with no externally observable contract, record
why the boundary does not apply. Do not use that exception when persistence or
asynchronous delivery is involved.

## The Required Vertical Slice

Build a migration ledger before editing. Name the owner, the old contract, the
new contract, and a proving test for every affected layer.

| Layer | Questions to answer | Required evidence |
| --- | --- | --- |
| Persistence | What is canonical at rest? Can existing data migrate safely and idempotently? | Fresh-store and existing-store tests |
| Contract | What exact value, field, ordering, and error semantics cross the boundary? | Schema or return-contract assertion |
| Callers | Which consumers unpack, branch on, transform, or forward the value? | Exhaustive caller search and focused tests |
| Transport | Which request, response, event, or envelope carries it? | Endpoint or producer-to-consumer test |
| Lifecycle | Which startup, worker, retry, cancellation, or cleanup path creates it? | Lifecycle and failure-path test |
| Operations | What is observable, recoverable, and safe to roll back? | Runbook note and failure evidence |

Search callers and data constructors before changing arity or field names. A
leaf-only patch that makes one call site pass while another still uses the old
shape is an incomplete migration.

## Contract Procedure

1. Write the old and new contracts in a short ledger, including ownership and
   compatibility policy.
2. Find every producer, persistence point, caller, serializer, and test that
   depends on the old contract.
3. Make storage and creation paths establish the new invariant first.
4. Update the public contract and all direct consumers as one coherent change.
5. Adapt transport and lifecycle paths so retries, duplicate delivery, and
   shutdown retain the same semantics.
6. Add regression tests for the old failure mode and the complete new slice.
7. Record an explicit rollback or compatibility decision before requesting
   review.

Prefer named result objects when the contract is expected to grow. When a
tuple remains appropriate, document its ordering and update every unpacking
site in the same migration. Do not catch broad exceptions to paper over an
incomplete schema or contract migration.

## Sanitized UUID Migration Case Study

A distributed event system needed a durable event identifier instead of using
a storage-local primary key as peer identity. The complete repair required all
six layers:

1. Persist a globally unique identifier with an idempotent uniqueness
   constraint and a migration for existing stores.
2. Return the identifier and inserted-state semantics from the storage
   operation.
3. Update every caller that unpacked the previous return value.
4. Include the identifier in the HTTP or event response envelope.
5. Ensure worker-thread initialization and replay paths use the same canonical
   insert operation.
6. Test first delivery, duplicate replay, response preservation, existing-store
   migration, and side effects occurring only after a fresh insert.

The lesson is not that every event needs a UUID. It is that identity,
persistence, idempotency, and transport visibility form one contract; they
must be reviewed together.

## Regression Matrix

At minimum, cover the cases that apply:

- fresh storage establishes the new invariant;
- an existing store migrates without data loss and can restart safely;
- a new request or event returns the complete new contract;
- duplicate replay preserves idempotency and does not repeat side effects;
- every direct caller accepts the exact new return shape;
- serialization and transport preserve required fields and redact prohibited
  fields;
- worker startup, retries, cancellation, and shutdown retain the invariant;
- a failed migration or provider call leaves accounting and durable state
  consistent.

## Review Gate

Before merge, include the migration ledger, changed-file list, tests actually
run, compatibility/rollback decision, and any operational follow-up. Reviewers
should reject a change that fixes only one vertical layer when the contract
crosses others.

This reference is intentionally implementation-neutral. Individual repository
plans remain authoritative for the concrete schema, rollout window, and
ownership decision.
