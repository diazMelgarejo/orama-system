# Contract — R4 durable continuation


**Status:** approved design contract under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Design only. Plan slice: [T5](PLAN-R4-EXECUTION.md#t5--r4-cursor-frontier-and-effect-aware-continuation).
Supersedes nothing; it is the proposed realization of doc 57 §11
("durability before resume") once ratified.


## 1. Legacy snapshot versus durable continuation


Today a loaded snapshot is fed to `ainvoke`, which restarts at `START`. That is an
explicit **compatibility path**, kept as is. It is marked non-resumable:


- It supports a **new traversal** only, with effect safeguards and a **new run ID**.
- Migration may reconstruct state but never a missing cursor or external outcome by
  assumption.
- Ordinary `ainvoke(state)` and durable continuation are distinct entry points until
  facade semantics are qualified.


Durable continuation requires a new validated checkpoint contract and capability. No
legacy snapshot is reinterpreted as one.


## 2. `DurableCheckpointV1` (neutral, proposed)


| Group | Content |
| --- | --- |
| Identity | Checkpoint ID, parent ID, durable run ID, lineage/fork identity, record version |
| Binding | Structural `graph_id`, executable binding, semantics and state-schema versions |
| Position | Detached serialized state; committed logical cursor/frontier; activation IDs |
| Region | Region activation, branch outcomes and receipts, join/reducer identities, commit status |
| Interrupts | Pending interrupts with stable IDs; resume-input bindings and consumption status |
| Authority refs | Effect and approval references; controller lease and fencing epoch; remaining budgets |
| Evidence | Critical-observer offsets, durable event sequence, integrity and provenance refs |


Core consumes **neutral** continuation data and an admission result through protocols.
Application-owned policy, provider and grant details stay opaque references validated by
Oramasys. No application policy schema enters GraphSpec, and Core's continuation entry
never accepts an Oramasys approval model. The Core engine imports no storage backend; the
storage adapter lives outside it.


## 3. Recovery algorithm


1. Authenticate the resume request, resolve authoritative run ownership and acquire a new
   **fencing epoch** by CAS. Stale workers cannot commit or create new dispatch
   authorizations. Already authorized or handed-off work remains subject to the in-flight
   cancellation and reconciliation rules; it is never blindly resent.
2. Verify checkpoint integrity, parent lineage, version support and artifact binding.
   Reject changed code or policy unless a separately approved migration supplies proof.
3. Reconcile every reachable **unknown effect** before further progress. Replay pure
   computation only under its declared deterministic contract. Never replay writes.
4. Validate pending grants and interrupt decisions against current authority and expiry. A
   resume value supplies **data only**, never effect authority.
5. Rebuild the neutral cursor and unfinished activations. Reuse stored successful branch
   outcomes; do not rerun a completed effect branch to rebuild fan-in.
6. Continue through the same `_run()` scheduler. Persist state, frontier and
   effect-application receipts atomically when co-located; otherwise use a versioned
   prepare/commit handshake with explicit recovery. Never infer a cross-store commit.
