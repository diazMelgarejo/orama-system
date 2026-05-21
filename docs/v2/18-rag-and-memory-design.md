# 18 — RAG + Memory Design (v2 Forward Plan)

> **Status:** Planning doc — v1 implementation is in `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md`.
> This document records the v2 canonical design for `oramasys/perpetua-core` and `oramasys/oramasys`.
> **No code changes to `oramasys/*` until this plan is reviewed and the v2 brainstorm session begins.**

---

## What Shipped in v1 (2026-05-21 — pulled forward from v2.1)

> **Decision trail:** AI originally deferred LanceDB to v2.1 (vector DB dependency).
> User overrode: Ollama+bge-m3 is already a hard system requirement per CLAUDE.md,
> so LanceDB has zero marginal cost. Pulled forward to v1 this week.

### v1 retrieval layer (`diazMelgarejo/orama-system` branch `feat/rag-gstack-optional-v1`)

| Module | File | Status |
|--------|------|--------|
| FTS5 on GossipBus | `perpetua_core/gossip.py` | Planned (v1) |
| LanceDB EmbeddingStore | `perpetua_core/memory/store.py` | Planned (v1) |
| Ollama bge-m3 embed | `perpetua_core/memory/embed.py` | Planned (v1) |
| RRF merge (k=60) | `perpetua_core/memory/rrf.py` | Planned (v1) |
| Fire-and-forget inline embed | `GossipBus.emit()` | Planned (v1) |
| `_pending_embeds` GC guard | `gossip.py` module-level | Planned (v1) |
| `embed_status` column | `gossip` table | Planned (v1) — groundwork for v2.5 reaper |
| MemoryNode (FTS5+LanceDB+RRF) | `orama/graph/nodes/memory_node.py` | Planned (v1) |
| GbrainSearchTool @tool | `perpetua_core/graph/tools/gbrain_search.py` | Planned (v1) |
| LLMClient wiring | `orama/graph/nodes/dispatch_node.py` | Planned (v1) |

**v1 embed sync strategy:** `asyncio.create_task()` inline in `emit()`. ~50ms latency
added to every event emit. No daemon process. Module-level `_pending_embeds: set[asyncio.Task]`
holds strong references to prevent GC of in-flight tasks.

---

## Why v1 Already Has LanceDB (Decision D4)

Per `00-context-and-decisions.md` D4 (dependency-minimal kernel) — the kernel itself
avoids vector DB deps, but the application layer (oramasys) always had leeway to add one.

The original D4 rationale was "avoid vector DB at the kernel level." LanceDB lives in
`perpetua_core/memory/` (a new sub-package, not the kernel) and in `oramasys`. It never
touches the kernel's hot path. The `emit()` embed is fire-and-forget — it does not block
any kernel operation.

---

## v2 Architecture

```
perpetua-core v2.1+
──────────────────────────────────────────────────────────────
gossip.py
  + FTS5 + LanceDB (v1 — DONE)
  + search() + _embed_and_store()  (v1 — DONE)
  + embed_status tracking           (v1 — DONE, enables v2.5 reaper)

memory/
  store.py       ← EmbeddingStore (LanceDB, v1 — DONE)
  embed.py       ← get_embedding via Ollama bge-m3 (v1 — DONE)
  rrf.py         ← rrf_merge k=60 (v1 — DONE)

  # v2.1 additions:
  circuit_breaker.py  ← EmbeddingCircuitBreaker — disables vector on N consecutive failures
  reaper.py           ← DEFERRED to v2.5 — retries rows where embed_status='failed'

graph/plugins/
  tool.py        ← GbrainSearchTool (v1 — DONE)

oramasys v2.1+
──────────────────────────────────────────────────────────────
graph/
  nodes/
    memory_node.py    ← FTS5+LanceDB+RRF (v1 — DONE)
    # v2.1: add HealthCheckNode or circuit-breaker awareness
    dispatch_node.py  ← LLMClient wired (v1 — DONE)
```

---

## v2.1 — Circuit Breaker + Fallback Hardening

**Goal:** After N consecutive LanceDB/Ollama failures, automatically switch to
FTS5-only mode without operator intervention. Re-enable on successful health check.

Currently in v1, `memory_node` already falls back to FTS5-only via `try/except`.
The v2.1 addition makes this state persistent across job invocations:

```python
# perpetua_core/memory/circuit_breaker.py  (v2.1 addition)

class EmbeddingCircuitBreaker:
    """Tracks LanceDB/Ollama failures. Opens after N consecutive errors.

    State is in-memory (per process). Resets on first success after
    the cooldown period.
    """

    def __init__(self, threshold: int = 5, cooldown_s: float = 60.0):
        self._failures = 0
        self._threshold = threshold
        self._opened_at: float = 0.0
        self._cooldown = cooldown_s

    def is_open(self) -> bool:
        """True = circuit open = skip vector search, use FTS5 only."""
        if self._failures < self._threshold:
            return False
        if time.monotonic() - self._opened_at > self._cooldown:
            self._failures = 0  # allow one probe
            return False
        return True

    def record_success(self):
        self._failures = 0

    def record_failure(self):
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
```

Updated `memory_node` in v2.1:

```python
_breaker = EmbeddingCircuitBreaker()

async def memory_node(state: PerpetuaState) -> dict:
    fts_hits = await bus.search(prompt, limit=10)

    vec_hits = []
    if not _breaker.is_open():
        try:
            embedding = await get_embedding(prompt)
            vec_hits = await store.search(embedding, limit=10)
            _breaker.record_success()
        except Exception:
            _breaker.record_failure()

    merged = rrf_merge(fts_hits, vec_hits)[:5]
    return {"scratchpad": {**state.scratchpad, "context": merged}}
```

---

## v2.5 — Reaper Daemon + DuckDB + Fleet-Distributed Lance Dataset

> **Decision trail:** AI initially suggested the background daemon in v1.
> User deferred it explicitly to v2.5 along with DuckDB and fleet features.

### Reaper daemon

Reads `embed_status='failed'` rows from GossipBus and retries embedding:

```python
# perpetua_core/memory/reaper.py  (v2.5 addition)

async def run_reaper(bus: GossipBus, store: EmbeddingStore, batch_size: int = 50):
    """Retry embedding for rows where embed_status='failed'."""
    async with aiosqlite.connect(bus._db_path) as db:
        cursor = await db.execute(
            "SELECT id, payload_json FROM gossip WHERE embed_status='failed' LIMIT ?",
            (batch_size,)
        )
        rows = await cursor.fetchall()
    for row_id, payload_json in rows:
        try:
            embedding = await get_embedding(payload_json)
            await store.add(row_id=row_id, text=payload_json, embedding=embedding)
            await bus._update_embed_status(row_id, "embedded")
        except Exception:
            pass
```

### DuckDB fleet analytics

DuckDB reads the existing SQLite GossipBus directly — no new storage format:

```python
import duckdb
conn = duckdb.connect()
conn.execute("ATTACH 'perpetua_core.db' AS gossip_sqlite (TYPE SQLITE)")
```

Planned endpoint: `GET /api/analytics/sessions?since=7d&group_by=event_type`

### Fleet-distributed Lance dataset

LanceDB supports Arrow IPC serialization. The v2.5 plan:
- Each node writes local `lance_memory.lance`
- A fleet aggregator merges tables via Arrow Flight
- No schema changes — the v1 LanceDB schema already supports this

---

## OQ Resolutions

| OQ | Topic | Resolution |
|----|-------|------------|
| (new) OQ18 | MemoryNode in kernel vs. plugin | Plugin in `memory/` sub-package — consistent with D4. Kernel unchanged. |
| (new) OQ19 | Embedding model for MemoryNode | Ollama bge-m3 (1024-dim) — unified with gbrain + CRG vector space |
| (new) OQ20 | LanceDB vs. Chroma vs. Qdrant | LanceDB: no server, 1 dep, Arrow-backed, pulled forward to v1 |
| (new) OQ21 | FTS5 + vector RRF merge strategy | k=60 Reciprocal Rank Fusion — same as CRG hybrid search |
| (new) OQ25 | Background daemon timing | Deferred to v2.5 — fire-and-forget inline in v1 |
| (new) OQ26 | `_pending_embeds` GC guard | Module-level set — user-required; prevents task GC before completion |
| (new) OQ27 | `embed_status` column | Added in v1 as groundwork — enables v2.5 reaper without schema migration |

---

## v2 Implementation Prerequisites

Before implementing v2.1 circuit breaker in `oramasys/*`:

1. v1 FTS5 + LanceDB + RRF + MemoryNode + LLMClient must be DONE and tested
2. Ollama bge-m3 verified via smoke test in v1 environment
3. v1 `embed_status` column confirmed in production schema
4. `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` Phase 0 complete
5. OQ12 (max_steps safety guard) resolved in perpetua-core/engine.py

Do not start v2.1 until all five are green.

---

## Migration from v1 to v2.1

v1 (FTS5 + LanceDB, fire-and-forget):
```
MemoryNode → FTS5 + LanceDB + RRF → scratchpad["context"]
emit() → FTS5 trigger sync + async embed task
```

v2.1 (adds circuit breaker):
```
MemoryNode → FTS5 + (LanceDB if breaker closed) + RRF → scratchpad["context"]
```

The `scratchpad["context"]` key and shape are identical. `dispatch_node` requires no changes.

**Upgrade path:** add `EmbeddingCircuitBreaker` instance to `memory_node` module scope.
Two new method calls (`is_open()`, `record_success()/failure()`). All v1 tests continue
to pass — the circuit starts closed and only opens after real failures.
