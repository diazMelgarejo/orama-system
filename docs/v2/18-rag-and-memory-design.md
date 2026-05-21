# 18 — RAG + Memory Design (v2 Forward Plan)

> **Status:** Planning doc — v1 implementation is in `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md`.
> This document records the v2 canonical design for `oramasys/perpetua-core` and `oramasys/oramasys`.
> **No code changes to `oramasys/*` until this plan is reviewed and the v2 brainstorm session begins.**

---

## Why RAG is Deferred from v2.0 Kernel

Per decision D4 (dependency-minimal kernel) from `00-context-and-decisions.md`: the v2.0
kernel avoids vector DB dependencies. `GossipBus` provides sufficient "memory" for
kernel-level routing decisions. Semantic retrieval is an application concern.

The v1 FTS5 implementation confirms this: zero new deps, ships this week, provides
meaningful recall from the audit log. This validates the approach before introducing
a vector store.

---

## v2 Architecture

```
perpetua-core v2.1+
──────────────────────────────────────────────────────────────
gossip.py
  + FTS5 (v1 — already planned)                 ← DONE in v1
  + search(query, limit, event_type)             ← DONE in v1
  + vector_search(embedding, limit) [v2.1]       ← uses LanceDB

memory/
  __init__.py
  store.py       ← EmbeddingStore (LanceDB-backed)
  ingest.py      ← doc ingestion pipeline: GossipBus + markdown docs
  node.py        ← MemoryNode (subgraph node)

graph/plugins/
  memory.py      ← MemoryPlugin (wraps EmbeddingStore, registers MemoryNode)
  tool.py        ← GbrainSearchTool (already planned in v1)

oramasys v2.1+
──────────────────────────────────────────────────────────────
graph/
  nodes/
    context_node.py    ← FTS5 recall (v1 — already planned)
    memory_node.py     ← LanceDB vector recall [v2.1]
    dispatch_node.py   ← LLMClient wired (v1 — already planned)
```

---

## v2.1 — LanceDB Vector Store

### Rationale for LanceDB

| Property | LanceDB | Alternatives |
|----------|---------|--------------|
| Dependencies | 1 pip install (`lancedb`) | Chroma (heavy), Qdrant (server), pgvector (Postgres required) |
| Storage | Local Arrow files, no server | n/a |
| Embedding | Any `numpy` array | n/a |
| Python version | 3.8+ | n/a |
| Disk footprint | ~50MB for 10K docs | n/a |
| Aligns with plan | `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` says LanceDB for orama-internal RAG | ✅ |

### EmbeddingStore API

```python
class EmbeddingStore:
    """LanceDB-backed vector store for RAG retrieval.

    Embedding model: Ollama bge-m3 (1024-dim) via localhost:11434
    — same model as gbrain + code-review-graph for unified vector space.
    Falls back to no-op if Ollama unavailable.
    """

    def __init__(self, db_path: str = "lance_memory.db"):
        ...

    async def ingest_gossip(self, bus: GossipBus, since: float = 0.0) -> int:
        """Embed and store GossipBus events. Returns count ingested."""
        ...

    async def ingest_docs(self, doc_dir: str) -> int:
        """Embed and store markdown files from doc_dir. Returns count."""
        ...

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Vector similarity search. Returns top-k hits with scores."""
        ...
```

### MemoryNode

Replaces `ContextNode` in v2.1. Queries both FTS5 (exact) and LanceDB (semantic),
merges results with Reciprocal Rank Fusion (RRF), injects into scratchpad.

```python
async def memory_node(state: PerpetuaState) -> dict:
    prompt = state.scratchpad.get("prompt", "")
    fts_hits    = await gossip.search(prompt, limit=5)
    vector_hits = await store.search(prompt, limit=5)
    merged = _rrf(fts_hits, vector_hits, k=60)[:5]
    return {"scratchpad": {**state.scratchpad, "context": merged}}
```

---

## v2.5 — DuckDB Fleet Analytics

DuckDB enables analytical queries over the GossipBus history across all sessions and
agents. Use cases:
- "Which agents had the highest error rate this week?"
- "What are the most common task_types routed to Windows?"
- "Show me all sessions where the model timed out."

**Schema:** Export GossipBus SQLite → DuckDB via `duckdb.connect().execute("ATTACH 'gossip.db' AS gossip_sqlite (TYPE SQLITE)")`

**No new storage format** — DuckDB reads the existing SQLite file directly.

**Planned endpoint:** `GET /api/analytics/sessions?since=7d&group_by=event_type`

---

## v2 Kernel Spec Additions (OQ resolution targets)

| OQ | Topic | v2.1 resolution |
|----|-------|----------------|
| (new) OQ18 | MemoryNode in kernel vs. plugin | Plugin — wraps `EmbeddingStore`, registered via `MemoryPlugin` in `graph/plugins/memory.py`. Consistent with D4. |
| (new) OQ19 | Embedding model for MemoryNode | Ollama bge-m3 (1024-dim) — unified with gbrain + CRG vector space |
| (new) OQ20 | LanceDB vs. Chroma vs. Qdrant | LanceDB: no server, 1 dep, Arrow-backed, already planned in `2026-05-19-gbrain-crg-embedding-integration.md` |
| (new) OQ21 | FTS5 + vector RRF merge strategy | k=60 Reciprocal Rank Fusion — same as CRG hybrid search implementation |

---

## v2 Implementation Prerequisites

Before implementing v2.1 RAG in oramasys/*:

1. v1 FTS5 + ContextNode + LLMClient wiring must be DONE and tested
2. Ollama bge-m3 must be running and verified via smoke test
3. `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` Phase 0 must be complete
4. OQ12 (max_steps safety guard) must be resolved in perpetua-core/engine.py

Do not start v2.1 until all four are green.

---

## Migration from v1 to v2

v1 (FTS5 only):
```
ContextNode → gossip.search(prompt) → scratchpad["context"]
```

v2.1 (FTS5 + LanceDB):
```
MemoryNode → RRF(gossip.search(), store.search()) → scratchpad["context"]
```

The `scratchpad["context"]` key and shape are identical. `dispatch_node` requires no
changes — context injection is already in place from v1.

**Upgrade path:** swap `context_node` for `memory_node` in `perpetua_graph.py` add_node call.
One line change. All tests continue to pass (different retrieval backend, same interface).
