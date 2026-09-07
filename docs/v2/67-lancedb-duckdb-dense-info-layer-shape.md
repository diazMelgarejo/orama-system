# 67 — LanceDB/DuckDB Dense Info Layer: Shape for oramasys/* (v2.1), Deferrals to v2.5

**Status:** Accepted (landmark decision), 2026-09-07
**Authority:** builds on the storage roadmap decided in `CLAUDE.md § 8`
(2026-05-15, reaffirmed 2026-07-12), [Doc 43 — GossipBus mesh transport](43-gossipbus-mesh-transport.md),
[Doc 45 / D23 — single-operator LAN threat-model descope](45-single-operator-lan-threat-model-descope.md),
[Doc 55 — observability contract](55-oramasys-agent-observability-contract-adr.md)
**Regime boundary:** this doc specifies v2 (`oramasys/*`) shape only. No PT
implementation changes are authorized here — PT's `orchestrator/gossip_bus.py`
and `orchestrator/memory_store.py` are read as reference for what already
works and ships as-is until a v2 migration lands, per [Doc 62's regime
boundary](62-telos-phylax-authority-gate0-adr.md#regime-boundary-added-2026-09-06-post-gate-1-reconciliation).

## Question this answers

*"What shape should the LanceDB/DuckDB implementation take in the new org
oramasys/* repos, as a RAG/storage/coordination dense info layer on top of
perpetua-core's MiniGraph kernel?"*

## Decision

**v2.1 ships two stores, not one. v2.5 is a superset, not a rewrite.**

| Layer | v2.1 (this decision, scope now) | v2.5 (deferred, scope later) |
| --- | --- | --- |
| Coordination/event log | SQLite+FTS5, carried forward from `gossip_bus.py`'s real shape, with one schema fix (`kind` promoted to a first-class column) | unchanged base; DuckDB gains a materialized/scheduled view over it once query volume justifies one |
| Semantic/RAG memory | LanceDB, one local table per machine, carried forward from `memory_store.py`'s real shape, with the write path formalized into a single background writer | unchanged base; background daemon (below) automates what's manual in v2.1 |
| Cross-machine sync | existing, already-validated GossipBus mesh transport (Doc 43) — delta-sync, idempotent, rate-limited | same transport; no new distributed-systems machinery added at v2.5 either |
| Query/analytics surface | none — direct reads against each store | **DuckDB, as an ephemeral query engine** — the native DuckDB↔Lance SQL extension joins LanceDB and the SQLite coordination log in one statement; DuckDB owns no persisted state of its own |
| Background daemon (auto-vacuum, auto-embed retry, scheduled DuckDB analytics refresh) | **deferred to v2.5** | full implementation |
| Fleet-wide analytics features (cross-agent dashboards, historical trend queries) | **deferred to v2.5** | full implementation |
| Full P2P (witness quorum, reputation-decay, equivocation defense) | **out of scope — descoped by D23**, not merely deferred | revisit only if D23's own re-trigger condition fires (see below) |

### Why two stores, not a merged blob

This isn't a new invention — it's what PT already runs, and it matches
LangGraph's own reference architecture: a short-term, per-thread checkpointer
kept separate from a long-term, cross-thread store, as two distinct SQLite
files even in LangGraph's own default setup. GossipBus (coordination/event
log — who claimed what, when, task lifecycle) and LanceDB (semantic/RAG
memory — embedded content, similarity search) answer different questions
under different access patterns; collapsing them into one store would trade
a clean separation that already works for no real gain.

### The one schema fix carried into v2.1

`gossip_bus.py`'s real `EventType` column is narrow; the actual routing
signal (`task_enqueue`/`task_claim`/`agent_register`/etc., per the
onboarding doc's vocabulary table) lives inside the JSON `payload`, not the
schema. That's fine for `tail()`/`search()` today, but it means `kind` isn't
queryable by SQL — which is exactly the join DuckDB needs for the "dense
info layer" the question asks for. **v2.1 promotes `kind` to a first-class,
indexed column.** This is the only schema change v2.1 requires; everything
else about the coordination log's shape is unchanged from what PT already
runs.

### Why LanceDB stays per-machine, not shared over the network

LanceDB's own concurrency guidance flags concurrent writers over a shared
network filesystem (the EFS/S3 pattern) as a real retry-storm and
consistency hazard, and Lance is fork-unsafe under Python multiprocessing.
Rather than build new locking or coordination machinery to make one shared
table safe across Mac and Windows, v2.1 keeps each machine's LanceDB table
local — exactly what Doc 20's v2.5 sketch already proposed — and lets
cross-machine visibility ride the mesh transport that's already
real-world-validated (Doc 43, validated 2026-07-12 across 2 concurrent
sessions). No new distributed-systems surface is introduced to solve a
problem the mesh transport already solves.

### Why the write path becomes a single background writer

LanceDB's own docs recommend a single-writer queue for concurrent-write
scenarios. `gossip_bus.py` already has the embryo of this pattern —
`schedule_embedding()`'s fire-and-forget `asyncio.create_task()` plus the
bounded `_pending_embeds` set — but it's scoped narrowly to the embedding
sidecar. v2.1 formalizes this into one real background writer per process
(a queue plus one draining task) as LanceDB's actual write path, not just
its embedding path. This is the load-bearing reason a background daemon is
listed as a v2.5 deferral below: v2.1's writer is an in-process task, not a
standalone daemon with its own lifecycle, scheduling, and failure handling —
that promotion is real, additional scope, not a renaming of what v2.1 already
has.

### Why DuckDB is a query engine, not a store, in v2.1

PT's original v2.5 sketch had DuckDB `ATTACH`ing the SQLite file directly. A
native DuckDB↔Lance SQL extension now exists and postdates that sketch — it
lets one SQL statement join vector search over a Lance table with relational
data directly, without a separate ETL or sync step. That makes DuckDB the
actual unifying "dense info layer" surface the question asks for: **it
persists nothing of its own** — it's an ephemeral query engine reading the
coordination log (via its SQLite scanner) and LanceDB (via the `lance`
extension) live. Because it owns no state, standing it up in v2.1 costs
nothing beyond the extension itself; the deferral below is specifically
about *scheduled, fleet-wide analytics features* built on top of that query
capability, not the query capability itself.

### The kernel boundary is unaffected

None of this touches perpetua-core's ~70-line MiniGraph kernel. It's a graph
plugin hooking `CompiledGraph.aobserve()`, filtered to `node.end`/`interrupt`
observations — the same filtering pattern already proven in
`LangChainRunnableAdapter.astream()` (`perpetua_core/graph/adapters/langchain_adapter.py`).
The kernel stays `ainvoke`/`aobserve`/`asteps`-only; storage is an adapter
concern, never a kernel one.

## Explicit deferrals to v2.5 (not silently dropped)

1. **Background daemon** — automating what v2.1 does manually/in-process:
   scheduled vacuum/compaction on the LanceDB tables, retrying failed
   embeddings beyond the current fire-and-forget attempt, and a scheduled
   refresh cycle for any materialized DuckDB view. v2.1 ships with the
   single-writer in-process task described above; a standalone daemon with
   its own lifecycle is v2.5 scope.
2. **DuckDB fleet-analytics features** — cross-agent dashboards, historical
   trend queries, anything that turns the ad-hoc join capability above into
   a standing feature surface with its own UI/API. v2.1 ships the query
   capability; v2.5 ships features built on it.
3. **Full P2P defense machinery** — witness quorum, reputation-decay,
   equivocation detection. This is a **descope, not a timeline deferral** —
   see the tension below.

## The P2P tension, resolved explicitly

D23 (Doc 45, decided 2026-07-12) rules byzantine-defense machinery **out**
for a single-operator LAN topology, with an explicit re-trigger test: does
the pattern's value require an adversary, or does it hold under
honest-but-flaky operation? Patterns that don't need an adversary — delta-
sync, idempotent dedupe, interest filtering, monotonic sequencing, bounded
reorder buffers — are exactly what Doc 43's mesh transport already is, and
D23 explicitly keeps those. What D23 cuts is BFT-style adversarial defense:
witness quorums, reputation decay, equivocation detection.

This decision carries that line forward unchanged. The `oramasys/*` org
split does not, by itself, trip D23's own re-trigger condition — it is the
same operator's repos, reorganized, not a new trust boundary or a new class
of untrusted participant. If that changes (a second operator's machine
joins the mesh, or a participant's honesty can no longer be assumed), D23
is the doc to revisit, not this one — this decision does not re-litigate
D23, it applies it.

## Security note carried in from the research pass

The comparable-architecture research surfaced a real CVE class in LangGraph
checkpointers: unsafe deserialization (SQLi→RCE via msgpack) of data
arriving from outside the trust boundary, mitigated upstream via
`LANGGRAPH_STRICT_MSGPACK=true`. Doc 43's mesh transport already crosses a
machine boundary (Mac↔Windows), which is exactly the kind of boundary that
class of bug lives on. **Any payload arriving via the mesh transport must be
validated against an explicit allow-list of shapes before deserialization** —
this is a concrete hardening addition to Doc 43's spec, not a new document,
and should be checked into that doc's implementation notes when the mesh
transport's next revision lands.

## Known gaps carried forward, not silently resolved

Two real correctness/observability gaps surfaced by the research, both
already present in PT's shipped code and both worth fixing at the v2
migration point rather than carrying forward unexamined:

- `GossipBus.search()` and `EmbeddingStore.search()` both swallow every
  exception to an empty list. That's a reasonable default for best-effort
  retrieval, but the same silent-degrade path currently also covers
  coordination-critical reads. v2's adapter should distinguish the two:
  best-effort reads may degrade silently; coordination-critical reads
  should raise or log loudly.
- The richer `kind` vocabulary (Section "the one schema fix") has, until
  now, been a payload convention documented only in the onboarding
  reference, not enforced by schema. Promoting it closes this gap for v2.1;
  it was never enforced in PT and won't be edited there under the regime
  boundary.

## Explicitly out of scope for this document

- Any PT implementation change (regime boundary — PT's real
  `gossip_bus.py`/`memory_store.py` are read as reference only).
- The actual migration cutover mechanics (how GossipBus's existing SQLite
  data gets imported into the new coordination-log schema) — that's
  implementation-phase work for whichever gate picks this up, not a
  decision this doc needs to make.
- Gate 4's Telos/dialer wiring (Doc 66) — unrelated surface.
