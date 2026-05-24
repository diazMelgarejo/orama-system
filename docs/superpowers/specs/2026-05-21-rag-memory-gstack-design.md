# Design: Minimal RAG Memory Pipeline + gstack Optional Submodule

**Date:** 2026-05-21
**Status:** Approved for planning — implementation pending manual review
**Branch:** `feat/rag-gstack-optional-v1`
**Repos in scope (v1):** `diazMelgarejo/orama-system`, `diazMelgarejo/Perpetua-Tools`
**Canonical v2 repos (plan only):** `oramasys/perpetua-core`, `oramasys/oramasys`

---

## Decision Trail: AI Suggestion vs User Override

This section documents each architectural decision with the original AI suggestion and the user override, so the reasoning is reproducible.

| # | Topic | AI Suggestion | User Decision | Rationale |
|---|-------|--------------|---------------|-----------|
| D1 | Storage backend | FTS5 only (zero new deps) | **Hybrid LanceDB + FTS5 (RRF)** | Maximum robustness + disaster recovery; FTS5 always available as fallback |
| D2 | Embed sync strategy | Background worker daemon | **Fire-and-forget `asyncio.create_task()` inline in `emit()`** | Eliminates background process complexity; revisit daemon in v2.5 for fleet-distributed dataset |
| D3 | GC safety for tasks | Not addressed | **Module-level `_pending_embeds: set[asyncio.Task]`** | Prevents Python GC from collecting fire-and-forget tasks before completion |
| D4 | LanceDB timing | v2.1 (deferred) | **v1 (this week, pulled forward)** | Ollama + bge-m3 already a hard system requirement (CLAUDE.md); zero marginal cost to add LanceDB now |
| D5 | RAG merge strategy | Not specified | **RRF k=60** | Reciprocal Rank Fusion — same strategy as CRG hybrid search; proven approach |
| D6 | Embed latency budget | Not specified | **`asyncio.create_task()` adds ~50ms to every `emit()`** | Acceptable; GossipBus is an audit log, not a hot path; emit() returns immediately |
| D7 | v2.5 scope | Not specified | **Reaper daemon + DuckDB + fleet-distributed Lance dataset** | Deferred scope is explicit; prevents scope creep in v1 |

---

## Problem Statement

The orama-system v0.9.9.9 agent runtime has zero retrieval capability. Every `/v1/jobs`
call starts cold from the LLM's context window alone. The GossipBus logs every session
event but exposes no search interface. Agents cannot recall relevant past interactions,
routing decisions, or skill invocations.

Additionally, gbrain (the team's pgvector semantic search system) is excellent but only
accessible to developers via CLI — agents cannot call it at runtime.

gstack (which ships gbrain) should be available on new installations but must never block
users who already have it installed or who choose not to install it.

---

## Dependency Budget

**v1 (this week):**
- FTS5: bundled in Python's `sqlite3` module (available since Python 3.4) — zero new deps
- LanceDB: `pip install lancedb` — one new dep, ~50MB, no server required
- Ollama bge-m3: already a hard system requirement per CLAUDE.md — zero marginal cost
- gbrain @tool: subprocess call to existing `gbrain` CLI (already on PATH for dev machines)
- LLMClient: already implemented in `perpetua_core/llm.py`
- gstack submodule: `git submodule` only — no pip installs

> **AI initially suggested:** FTS5-only (zero new deps).
> **User override:** Add LanceDB now — Ollama+bge-m3 is already required, so the vector
> store is nearly free to add. One dep for semantic recall is a net win at v1.

**v2.5 (future):** Reaper daemon + DuckDB analytics + fleet-distributed Lance dataset.

---

## Architecture Overview

```
perpetua-core (kernel changes)           oramasys (graph changes)
─────────────────────────────           ──────────────────────────
GossipBus                                MemoryNode  (NEW, node 0 — replaces ContextNode)
  + FTS5 virtual table (NEW)              ├── gossip.search(prompt, k=10)   [always works]
  + LanceDB EmbeddingStore (NEW)          ├── lance.search(prompt, k=10)    [try/except]
  + _pending_embeds: set[Task] (NEW)      ├── rrf_merge(fts_hits, vec_hits, k=60)[:5]
  + embed_status column (NEW)             └── scratchpad["context"] = merged top-5
  + search(query, limit) (NEW)                  ↓
  + emit() fire-and-forget embed          route_node  (existing, node 1)
                                          dispatch_node  (WIRED, node 2)
perpetua_core/graph/tools/               ├── LLMClient.chat(messages=[
  gbrain_search.py (NEW)                 │     system: context + policy,
    @tool GbrainSearch                   │     user: state.prompt
    subprocess: gbrain query             │   ])
    graceful: empty list if CLI absent   └── scratchpad["response"] = LLM output
                                         respond_node  (existing, node 3)
                                           └── state.output = scratchpad["response"]
```

### Data flow (single job request)

```
POST /v1/jobs {prompt: "..."}
  → JobSpec created
  → OrchestrationSupervisor._dispatch()
  → oramasys /run endpoint
  → MiniGraph.ainvoke(state)
      → MemoryNode
          fts_hits  = gossip.search(state.prompt, limit=10)    ← always
          vec_hits  = lance.search(state.prompt, limit=10)     ← try/except []
          merged    = rrf_merge(fts_hits, vec_hits)[:5]
          scratchpad["context"] = merged
      → route_node (hardware affinity gate — unchanged)
      → dispatch_node
          LLMClient.chat([
            {"role": "system", "content": SYSTEM_PROMPT + context},
            {"role": "user",   "content": state.prompt}
          ])
          → model response into scratchpad["response"]
      → respond_node
          state.output = scratchpad["response"]
  ← RunResponse {output: "...", context_used: [...]}
```

---

## Sub-Project 1: GossipBus Hybrid Search

**File:** `perpetua_core/gossip.py` (modify)
**Tests:** `tests/test_gossip_search.py` (create)

### Schema changes to `init_db()`

```python
# 1. FTS5 virtual table + triggers (keyword recall — always available)
_CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS gossip_fts
USING fts5(event_type, payload_json, content='gossip', content_rowid='id')
"""

_CREATE_FTS_AI = """
CREATE TRIGGER IF NOT EXISTS gossip_fts_ai
AFTER INSERT ON gossip BEGIN
  INSERT INTO gossip_fts(rowid, event_type, payload_json)
  VALUES (new.id, new.event_type, new.payload_json);
END
"""

_CREATE_FTS_AD = """
CREATE TRIGGER IF NOT EXISTS gossip_fts_ad
AFTER DELETE ON gossip BEGIN
  INSERT INTO gossip_fts(gossip_fts, rowid, event_type, payload_json)
  VALUES ('delete', old.id, old.event_type, old.payload_json);
END
"""

# 2. embed_status column for disaster recovery tracking
# AI didn't suggest this — added for v2.5 reaper daemon groundwork
_ADD_EMBED_STATUS = """
ALTER TABLE gossip ADD COLUMN embed_status TEXT NOT NULL DEFAULT 'pending'
"""

_CREATE_EMBED_IDX = """
CREATE INDEX IF NOT EXISTS idx_gossip_embed_status
ON gossip(embed_status) WHERE embed_status != 'embedded'
"""
```

### Module-level GC guard (user-requested, AI omission)

```python
# Prevent Python GC from collecting fire-and-forget embed tasks.
# AI's initial design omitted this; user explicitly required it.
# Without it, tasks scheduled via asyncio.create_task() can be GC'd
# before completion if no strong reference is held anywhere.
_pending_embeds: set[asyncio.Task] = set()
```

### New `emit()` with fire-and-forget embed

```python
async def emit(self, event_type: EventType, payload: dict) -> None:
    async with aiosqlite.connect(self._db_path) as db:
        cursor = await db.execute(
            "INSERT INTO gossip (ts, event_type, payload_json, embed_status) "
            "VALUES (?, ?, ?, 'pending')",
            (time.time(), event_type, json.dumps(payload)),
        )
        row_id = cursor.lastrowid
        await db.commit()
    # Fire-and-forget embed — never blocks emit() return.
    # AI initially suggested a background daemon; user chose inline task.
    # Backpressure: cap _pending_embeds at 500 tasks. When full, drop the embed
    # (row stays embed_status='pending' for v2.5 reaper); FTS5 still works.
    if len(_pending_embeds) < 500:
        task = asyncio.create_task(self._embed_and_store(row_id, payload))
        _pending_embeds.add(task)
        task.add_done_callback(_pending_embeds.discard)
```

### `_embed_and_store()` — async embed + LanceDB write

```python
async def _embed_and_store(self, row_id: int, payload: dict) -> None:
    """Embed payload and store in LanceDB. Updates embed_status column."""
    try:
        from perpetua_core.memory.embed import get_embedding
        from perpetua_core.memory.store import get_lance_store
        text = json.dumps(payload)
        embedding = await get_embedding(text)
        store = get_lance_store()  # path-keyed singleton; overrideable via env
        await store.add(row_id=row_id, text=text, embedding=embedding)
        await self._update_embed_status(row_id, "embedded")
    except Exception:
        await self._update_embed_status(row_id, "failed")

async def _update_embed_status(self, row_id: int, status: str) -> None:
    async with aiosqlite.connect(self._db_path) as db:
        await db.execute(
            "UPDATE gossip SET embed_status = ? WHERE id = ?", (status, row_id)
        )
        await db.commit()
```

### New method: `search()` — FTS5 keyword recall

```python
# FTS5 reserves these tokens — sanitize user input before passing to MATCH ?
# Without this, an apostrophe or `AND` in user text raises sqlite3.OperationalError
# and the search silently returns []. See v1 plan §_sanitize_fts_query for tests.
import re

_FTS5_RESERVED = re.compile(r'[^\w\s]')

def _sanitize_fts_query(raw: str) -> str:
    """Strip FTS5-reserved punctuation and wrap each token to avoid syntax errors."""
    cleaned = _FTS5_RESERVED.sub(' ', raw)
    tokens = [t for t in cleaned.split() if t]
    return ' '.join(f'"{t}"' for t in tokens) if tokens else ''


async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    event_type: Optional[str] = None,
) -> list[dict]:
    """BM25 full-text search over GossipBus event history. Always works."""
    safe_query = _sanitize_fts_query(query)
    if not safe_query:
        return []
    async with aiosqlite.connect(self._db_path) as db:
        if event_type:
            cursor = await db.execute(
                """SELECT g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ? AND g.event_type = ?
                   ORDER BY rank LIMIT ?""",
                (safe_query, event_type, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (safe_query, limit),
            )
        rows = await cursor.fetchall()
    return [
        {"ts": r[0], "event_type": r[1], "payload": json.loads(r[2])}
        for r in rows
    ]
```

### EmbeddingStore — LanceDB vector recall

```python
# perpetua_core/memory/store.py (new file)
import lancedb
import asyncio
import os
from pathlib import Path

# Embedding dim is determined at runtime by probe_embed_dim() (see v1 plan).
# Default 1024 matches bge-m3 (Ollama default); override via EMBED_DIM env or
# the EmbeddingStore(dim=...) ctor. Hardcoding here would force schema migration
# every time the embedder changes.
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))


class EmbeddingStore:
    """LanceDB-backed vector store. Falls back gracefully to no-op if unavailable.

    The vector column dimension is set at table-create time from `dim` (defaults
    to module-level `EMBED_DIM`). Path-keyed singleton — different db_path =
    different store, so swapping embedders mid-run doesn't collide schemas.
    """

    def __init__(self, db_path: str = "lance_memory.lance", dim: int = EMBED_DIM):
        self._db_path = db_path
        self._dim = dim
        self._table = None

    async def _ensure_table(self):
        if self._table is None:
            db = lancedb.connect(self._db_path)
            if "gossip" in db.table_names():
                self._table = db.open_table("gossip")
            else:
                import pyarrow as pa
                schema = pa.schema([
                    pa.field("row_id", pa.int64()),
                    pa.field("text", pa.utf8()),
                    pa.field("vector", pa.list_(pa.float32(), self._dim)),
                ])
                self._table = db.create_table("gossip", schema=schema)

    async def add(self, row_id: int, text: str, embedding: list[float]) -> None:
        await self._ensure_table()
        self._table.add([{"row_id": row_id, "text": text, "vector": embedding}])

    async def search(self, query_embedding: list[float], limit: int = 10) -> list[dict]:
        try:
            await self._ensure_table()
            results = self._table.search(query_embedding).limit(limit).to_list()
            return [{"row_id": r["row_id"], "text": r["text"], "score": r["_distance"]}
                    for r in results]
        except Exception:
            return []
```

### RRF merge

```python
import uuid

def rrf_merge(
    fts_hits: list[dict],
    vec_hits: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion — merges FTS5 and vector results.

    k=60 per CRG hybrid search convention. Falls back to fts_hits-only
    if vec_hits is empty (disaster recovery posture).

    Synthetic key strategy: when a hit lacks a real `row_id` (gbrain results,
    rare GossipBus desync), we MUST NOT fall back to `rank` — that key
    collides across fts_hits and vec_hits and silently dedupes unrelated
    rows. UUID4 is generated per-hit, so synthetic keys never collide.
    """
    if not vec_hits:
        return fts_hits
    # Use object keys (str) so int row_ids and uuid hex strings coexist.
    scores: dict[str, float] = {}
    id_to_item: dict[str, dict] = {}
    for rank, hit in enumerate(fts_hits):
        rid = str(hit.get("row_id") or f"fts-{uuid.uuid4().hex}")
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[rid] = hit
    for rank, hit in enumerate(vec_hits):
        rid = str(hit.get("row_id") or f"vec-{uuid.uuid4().hex}")
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[rid] = hit
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [id_to_item[rid] for rid, _ in ranked]
```

---

## Sub-Project 2: MemoryNode + GbrainSearchTool

### MemoryNode (`orama/graph/nodes/memory_node.py`, create)

Replaces the simpler ContextNode from the original FTS5-only design.

```python
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus
from perpetua_core.memory.store import EmbeddingStore
from perpetua_core.memory.embed import get_embedding
from perpetua_core.memory.rrf import rrf_merge
import os

_GOSSIP_DB = os.environ.get("GOSSIP_DB_PATH", "perpetua_core.db")
_LANCE_DB  = os.environ.get("LANCE_DB_PATH",  "lance_memory.lance")

_lance_store = EmbeddingStore(_LANCE_DB)


async def memory_node(state: PerpetuaState) -> dict:
    """Retrieve context via FTS5 (always) + LanceDB (try/except) + RRF merge."""
    prompt = state.prompt or state.scratchpad.get("prompt", "")
    if not prompt:
        return {"scratchpad": {**state.scratchpad, "context": []}}

    bus = GossipBus(_GOSSIP_DB)
    await bus.init_db()

    # FTS5 — always works (disaster recovery baseline)
    fts_hits = await bus.search(prompt, limit=10)

    # LanceDB — opportunistic, graceful fallback
    try:
        embedding = await get_embedding(prompt)
        vec_hits = await _lance_store.search(embedding, limit=10)
    except Exception:
        vec_hits = []

    merged = rrf_merge(fts_hits, vec_hits)[:5]
    return {"scratchpad": {**state.scratchpad, "context": merged}}
```

### GbrainSearchTool (`perpetua_core/graph/tools/gbrain_search.py`, create)

```python
import subprocess
import json
from perpetua_core.graph.plugins.tool import tool

@tool
async def gbrain_search(query: str, limit: int = 5) -> list[dict]:
    """Search gbrain semantic memory for relevant past knowledge.

    Returns empty list if gbrain CLI is not installed (graceful degradation).
    Never raises — failure is treated as no results.
    Uses run_in_executor to avoid blocking the async event loop.
    """
    import asyncio

    def _run() -> list[dict]:
        try:
            result = subprocess.run(
                ["gbrain", "query", query, "--limit", str(limit), "--format", "json"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return []
            return json.loads(result.stdout) if result.stdout.strip() else []
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return []

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)
    except Exception:
        return []
```

### Wire MemoryNode into graph (`orama/graph/perpetua_graph.py`, modify)

```python
from orama.graph.nodes.memory_node import memory_node

graph = (
    MiniGraph()
    .add_node("memory",   memory_node)
    .add_node("route",    route_node)
    .add_node("dispatch", dispatch_node)
    .add_node("respond",  respond_node)
    .add_edge(START,      "memory")
    .add_edge("memory",   "route")
    .add_edge("route",    "dispatch")
    .add_edge("dispatch", "respond")
    .add_edge("respond",  END)
)
```

---

## Sub-Project 3: LLMClient Wiring in dispatch_node

**File:** `orama/graph/nodes/dispatch_node.py` (modify — currently echo stub)
**Tests:** `tests/graph/test_dispatch_node.py` (create)

Same as original design — LLMClient wiring is unchanged by the hybrid storage decision.
Context is injected from `scratchpad["context"]` regardless of whether it came from FTS5,
LanceDB, or RRF-merged results.

---

## Sub-Project 4: gstack Optional Git Submodule

Unchanged from original design. gstack is always optional, always idempotent.
Detection order: (1) gbrain on PATH → (2) `~/.claude/skills/gstack` → (3) `tools/gstack/`.

---

## Commit Plan (v1 feature branch)

**Commit 1 — Retrieval layer**

```
feat(rag): FTS5 + LanceDB hybrid GossipBus search + MemoryNode (RRF)
```

Files: `perpetua_core/gossip.py`, `perpetua_core/memory/`, `orama/graph/nodes/memory_node.py`,
`orama/graph/perpetua_graph.py`, all related tests.

**Commit 2 — Generation layer**

```
feat(dispatch): wire LLMClient into dispatch_node with context injection
```

Files: `orama/graph/nodes/dispatch_node.py`, `tests/graph/test_dispatch_node.py`.

---

## v2 Upgrade Path (planning only — implement in oramasys/* later)

| v1 (this week) | v2.1 | v2.5 |
|---|---|---|
| FTS5 + LanceDB hybrid (RRF k=60) | FTS5 fallback hardening + circuit breaker | Reaper daemon for `embed_status='failed'` rows |
| Fire-and-forget inline embed | Auto-retry on embed failure | Fleet-distributed Lance dataset |
| gbrain @tool subprocess | gbrain as first-class ToolNode | DuckDB analytical queries over GossipBus history |
| gstack optional submodule | gstack optional sidecar (OCI) | gstack fleet coordinator |

See `docs/v2/20-rag-and-memory-design.md` for full v2 forward-plan.

---

## Open Questions (resolved)

| Question | Answer |
|----------|--------|
| LanceDB this week? | **Yes** — user pulled forward from v2.1; Ollama+bge-m3 already required |
| FTS5 still needed? | **Yes** — disaster recovery fallback; RRF merge uses both |
| Background daemon for embeds? | **No** — fire-and-forget inline in emit() for v1; daemon deferred to v2.5 |
| `_pending_embeds` GC guard needed? | **Yes** — explicitly user-required; prevents task GC before completion |
| DuckDB this week? | **No** — deferred to v2.5 |
| gstack mandatory? | **Never** — always optional, always idempotent |
| gbrain at runtime? | Via @tool subprocess wrapper, graceful fallback to empty list |
