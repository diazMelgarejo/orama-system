# Contract — internal consistency and multi-host stages

**Status:** proposed under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Plan slice: [T10](PLAN-R4-EXECUTION.md#t8t10--follow-on-slices). Operates under
[doc 45](../../45-single-operator-lan-threat-model-descope.md): multiple hosts do not
imply multiple principals, witness quorums or BFT.

## 1. One contract owner per field

Registry conformance checks complete producer and consumer inventories, exact owners and
records, schema versions and literals. Validate duplicates and unknown keys **before**
normalization or dictionary indexing can erase a violation. A generated policy summary,
dashboard or event is a projection, never an authority.

## 2. Stages

| Stage | Authority and deployment | Required proof |
| --- | --- | --- |
| H0 | Single authoritative host; local durable store | Restart, crash, CAS and backup qualification |
| H1 | Same single authority plus authenticated, contained remote workers | Leases, fencing, partition/cancel/reconciliation, capability and transport checks |
| H2 | Larger fleet with a qualified authority backend or failover | Transactional backend, migration, stale-leader fencing, recovery/RPO/RTO evidence |

H1 may expose a narrow authority API backed by host-local SQLite. Never share the SQLite
file over the LAN and never infer distributed locking from gossip. H2 persistence and
failover need their own ADR after measured needs; PostgreSQL is a candidate, not an
approved mandatory dependency.

## 3. Fencing

Split-brain prevention requires one valid writer epoch. A lease alone cannot fence an
external provider that ignores it, so such providers still need dedupe, containment and
reconciliation guarantees. Stale epochs cannot commit or create new dispatch
authorizations; authorized or handed-off requests still require deduplication and
reconciliation (see the [continuation contract](CONTRACT-DURABLE-CONTINUATION.md) step 1).

## 4. Principals and trust

H1 depends on authenticated worker identity (docs 49 and 61). H2 does **not** enable
multi-principal co-signature automatically: reassess real witnesses, trust boundaries and
observed failure modes first. Mesh, MCP and A2A provide transport and projections, not job
authority.

## 5. Failure tests (T10)

Controller restart; delayed or replayed messages; duplicate delivery; clock jumps; stale
principal state; expired leases; lost worker receipts; interrupted streams; network
partition; split-brain attempts. Safety may sacrifice availability: the system reports
blocked or unknown work rather than a duplicate-dispatch success.
