# RAG Memory Pipeline v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hybrid LanceDB + FTS5 recall on GossipBus, inject merged context into oramasys graph via MemoryNode (RRF), wire LLMClient into dispatch_node.

**Outcome (clarified at autoplan gate):** Enable search in the operator UI + natural language instructions that the Launcher Agent and default orchestrator can understand. Hybrid search available to ALL agents by default via the `@tool gbrain_search` + MemoryNode. This is the retrieval substrate that unlocks UI-level search and context-aware agent routing.

**Follow-on (after this plan lands):** Implement v2.1 EmbeddingCircuitBreaker in `docs/v2/18-rag-and-memory-design.md` — opens after N consecutive LanceDB/Ollama failures, auto-closes after cooldown. Next sprint after this merges.

**Architecture:** Two commits on `feat/rag-gstack-optional-v1`. Commit 1 = retrieval layer (perpetua-core: FTS5 + LanceDB + RRF + MemoryNode). Commit 2 = generation layer (dispatch_node LLMClient wiring).

**Decision trail:** AI initially proposed FTS5-only (zero new deps). User overrode to hybrid LanceDB+FTS5 with RRF — Ollama+bge-m3 is already a hard system requirement so LanceDB is nearly free. AI initially proposed a background daemon for embed sync; user chose fire-and-forget `asyncio.create_task()` inline in `emit()`. User also required a module-level `_pending_embeds: set[asyncio.Task]` to prevent GC of in-flight tasks.

**Tech Stack:** Python 3.11+, aiosqlite, SQLite FTS5 (stdlib), lancedb (1 new dep), Ollama bge-m3 at localhost:11434 (already required), perpetua-core kernel, oramasys FastAPI graph, existing `perpetua_core.llm.LLMClient`

**Repos:** `/Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core` and `/Users/lawrencecyremelgarejo/Documents/oramasys/oramasys`

**Run tests with:** `python -m pytest tests/ -v` (in each repo root)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `perpetua_core/gossip.py` | Modify | FTS5 schema + triggers + `search()` + fire-and-forget `emit()` + `_pending_embeds` |
| `perpetua_core/memory/__init__.py` | Create | Package init |
| `perpetua_core/memory/store.py` | Create | `EmbeddingStore` — LanceDB vector store |
| `perpetua_core/memory/embed.py` | Create | `get_embedding()` — Ollama bge-m3 call |
| `perpetua_core/memory/rrf.py` | Create | `rrf_merge()` — Reciprocal Rank Fusion k=60 |
| `perpetua_core/graph/tools/__init__.py` | Create | Package init |
| `perpetua_core/graph/tools/gbrain_search.py` | Create | `@tool GbrainSearch` subprocess wrapper |
| `tests/test_gossip_search.py` | Create | 5 FTS5 + 2 embed-status tests |
| `tests/memory/test_store.py` | Create | 3 LanceDB store tests |
| `tests/memory/test_rrf.py` | Create | 3 RRF merge tests |
| `tests/graph/tools/test_gbrain_search.py` | Create | 4 graceful degradation tests |
| `orama/graph/nodes/memory_node.py` | Create | MemoryNode: FTS5 + LanceDB + RRF + scratchpad inject |
| `orama/graph/nodes/__init__.py` | Create/modify | Export memory_node |
| `orama/graph/perpetua_graph.py` | Modify | Wire MemoryNode as node 0 |
| `tests/graph/test_memory_node.py` | Create | 4 integration tests |
| `orama/graph/nodes/dispatch_node.py` | Modify | Wire LLMClient with context system prompt |
| `tests/graph/test_dispatch_node.py` | Create | 3 tests |

---

## COMMIT 1: Retrieval Layer

### Task 1 — GossipBus FTS5 schema + embed_status column

**Files:** `perpetua_core/gossip.py`

- [ ] **Step 1: Write failing tests first**

Create `tests/test_gossip_search.py`:

```python
import asyncio
import pytest
import tempfile
import os
from perpetua_core.gossip import GossipBus


@pytest.fixture
async def bus(tmp_path):
    db = str(tmp_path / "test.db")
    b = GossipBus(db)
    await b.init_db()
    return b


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty(bus):
    await bus.emit("dispatch", {"prompt": "hello world"})
    result = await bus.search("")
    assert result == []


@pytest.mark.asyncio
async def test_search_finds_exact_payload_keyword(bus):
    await bus.emit("dispatch", {"prompt": "find the blue widget"})
    await bus.emit("route",    {"intent": "unrelated thing"})
    hits = await bus.search("blue widget")
    assert len(hits) == 1
    assert hits[0]["event_type"] == "dispatch"
    assert "blue widget" in hits[0]["payload"]["prompt"]


@pytest.mark.asyncio
async def test_search_filters_by_event_type(bus):
    await bus.emit("dispatch", {"prompt": "run the calculation"})
    await bus.emit("error",    {"prompt": "run the calculation", "error": "timeout"})
    hits = await bus.search("run the calculation", event_type="error")
    assert len(hits) == 1
    assert hits[0]["event_type"] == "error"


@pytest.mark.asyncio
async def test_search_returns_empty_for_no_match(bus):
    await bus.emit("dispatch", {"prompt": "completely different content"})
    hits = await bus.search("xyzzy_no_match_ever")
    assert hits == []


@pytest.mark.asyncio
async def test_rebuild_fts_handles_existing_rows(tmp_path):
    """_rebuild_fts() must populate FTS from existing gossip rows."""
    db = str(tmp_path / "existing.db")
    import aiosqlite
    async with aiosqlite.connect(db) as conn:
        await conn.execute(
            "CREATE TABLE gossip (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ts REAL NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "embed_status TEXT NOT NULL DEFAULT 'pending')"
        )
        await conn.execute(
            "INSERT INTO gossip (ts, event_type, payload_json) VALUES (1.0, 'dispatch', ?)",
            ('{"prompt": "pre-existing row"}',)
        )
        await conn.commit()

    bus = GossipBus(db)
    await bus.init_db()  # must detect existing rows and rebuild FTS

    hits = await bus.search("pre-existing row")
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_emit_sets_embed_status_pending(tmp_path):
    """New rows must have embed_status='pending' until embedded."""
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()
    await bus.emit("dispatch", {"prompt": "test row"})
    import aiosqlite
    async with aiosqlite.connect(db) as conn:
        cursor = await conn.execute("SELECT embed_status FROM gossip LIMIT 1")
        row = await cursor.fetchone()
    # Row starts as 'pending' (embed is async; may still be in flight)
    assert row[0] in ("pending", "embedded", "failed")


@pytest.mark.asyncio
async def test_pending_embeds_set_prevents_gc(tmp_path):
    """_pending_embeds module set must hold strong references to in-flight tasks."""
    from perpetua_core.gossip import _pending_embeds
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()
    await bus.emit("dispatch", {"prompt": "gc test"})
    # After emit() returns, the set must contain the task (not yet done)
    # OR be empty (task completed synchronously in test event loop).
    # Either is valid — what's NOT valid is the set being garbage collected itself.
    assert isinstance(_pending_embeds, set)
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/test_gossip_search.py -v
```

Expected: 7 failures (FTS5 + embed_status not yet implemented)

- [ ] **Step 3: Implement FTS5 + embed_status in gossip.py**

Add module-level constants and GC guard after imports:

```python
import asyncio
import json
import time
from typing import Literal, AsyncIterator, Optional

# GC guard: strong references to in-flight embed tasks.
# Without this, asyncio.create_task() tasks can be garbage-collected
# before completion because the event loop only holds a weak reference.
# User-required; AI omission corrected.
_pending_embeds: set[asyncio.Task] = set()

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
```

Update `CREATE_TABLE` to include `embed_status`:

```python
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS gossip (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL    NOT NULL,
    event_type   TEXT    NOT NULL,
    payload_json TEXT    NOT NULL,
    embed_status TEXT    NOT NULL DEFAULT 'pending'
)
"""
```

For existing databases that predate this schema, add migration in `init_db()`:

```python
async def init_db(self) -> None:
    async with aiosqlite.connect(self._db_path) as db:
        await db.execute(CREATE_TABLE)
        # Migrate: add embed_status to pre-existing schemas (idempotent)
        try:
            await db.execute(
                "ALTER TABLE gossip ADD COLUMN embed_status TEXT NOT NULL DEFAULT 'pending'"
            )
        except Exception:
            pass  # Column already exists — safe to ignore
        await db.execute(_CREATE_FTS)
        await db.execute(_CREATE_FTS_AI)
        await db.execute(_CREATE_FTS_AD)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_gossip_embed_status "
            "ON gossip(embed_status) WHERE embed_status != 'embedded'"
        )
        await db.commit()
        # Populate FTS from pre-existing rows (idempotent migration)
        cursor = await db.execute("SELECT COUNT(*) FROM gossip_fts")
        (fts_count,) = await cursor.fetchone()
        cursor = await db.execute("SELECT COUNT(*) FROM gossip")
        (row_count,) = await cursor.fetchone()
        if row_count > 0 and fts_count == 0:
            await db.execute(
                "INSERT INTO gossip_fts(rowid, event_type, payload_json) "
                "SELECT id, event_type, payload_json FROM gossip"
            )
            await db.commit()
```

Update `emit()` with fire-and-forget embed:

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
    # AI suggested a background daemon; user chose inline task.
    # _pending_embeds holds a strong reference so GC cannot collect the task.
    # Size cap prevents unbounded accumulation if Ollama is consistently slow.
    if len(_pending_embeds) < 500:
        task = asyncio.create_task(self._embed_and_store(row_id, payload))
        _pending_embeds.add(task)
        task.add_done_callback(_pending_embeds.discard)
    else:
        # Backpressure: drop embed when queue is full, row stays 'pending'
        # (reaper will retry in v2.5; FTS5 fallback still works)
        pass

async def _embed_and_store(self, row_id: int, payload: dict) -> None:
    """Embed payload via Ollama bge-m3 and store in LanceDB."""
    try:
        from perpetua_core.memory.embed import get_embedding
        from perpetua_core.memory.store import get_lance_store
        text = json.dumps(payload)
        embedding = await get_embedding(text)
        store = get_lance_store()  # uses default path; overrideable via env
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

Add `search()` method:

```python
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    event_type: Optional[str] = None,
) -> list[dict]:
    """BM25 full-text search over GossipBus event history. Always works."""
    if not query.strip():
        return []
    async with aiosqlite.connect(self._db_path) as db:
        if event_type:
            cursor = await db.execute(
                """SELECT g.id, g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ? AND g.event_type = ?
                   ORDER BY rank LIMIT ?""",
                (query, event_type, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT g.id, g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        rows = await cursor.fetchall()
    return [
        {"row_id": r[0], "ts": r[1], "event_type": r[2], "payload": json.loads(r[3])}
        for r in rows
    ]


async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    event_type: Optional[str] = None,
) -> list[dict]:
    """BM25 full-text search over GossipBus event history. Always works.

    Wraps FTS5 MATCH in try/except: real prompts with quotes, colons, or
    FTS5 operators raise OperationalError — degrade gracefully to [].
    """
    if not query.strip():
        return []
    try:
        async with aiosqlite.connect(self._db_path) as db:
            if event_type:
                cursor = await db.execute(
                    """SELECT g.id, g.ts, g.event_type, g.payload_json
                       FROM gossip_fts f
                       JOIN gossip g ON g.id = f.rowid
                       WHERE gossip_fts MATCH ? AND g.event_type = ?
                       ORDER BY rank LIMIT ?""",
                    (query, event_type, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT g.id, g.ts, g.event_type, g.payload_json
                       FROM gossip_fts f
                       JOIN gossip g ON g.id = f.rowid
                       WHERE gossip_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (query, limit),
                )
            rows = await cursor.fetchall()
        return [
            {"row_id": r[0], "ts": r[1], "event_type": r[2], "payload": json.loads(r[3])}
            for r in rows
        ]
    except Exception:
        return []  # FTS5 OperationalError on malformed query — degrade gracefully
```

- [ ] **Step 4: Run tests — verify 7 pass**

```bash
python -m pytest tests/test_gossip_search.py -v
```

Expected: 7 passed

- [ ] **Step 5: Run full perpetua-core suite**

```bash
python -m pytest tests/ -v
```

Expected: all prior tests pass + 7 new

---

### Task 2 — LanceDB EmbeddingStore + embed helper + RRF

**Files:** `perpetua_core/memory/__init__.py`, `perpetua_core/memory/store.py`, `perpetua_core/memory/embed.py`, `perpetua_core/memory/rrf.py`

- [ ] **Step 1: Install lancedb and verify aiohttp**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
.venv/bin/pip install lancedb aiohttp
# Check if aiohttp already in pyproject.toml
grep "aiohttp" pyproject.toml
```

Edit `pyproject.toml` — add to `[project] dependencies` (if not already present):
```toml
"lancedb>=0.6",
"aiohttp>=3.9",
```

Note: `aiohttp` is used by `memory/embed.py` for Ollama bge-m3 calls. If `httpx` is already present in the deps, use that instead — update `embed.py` accordingly. Do NOT assume `aiohttp` is present without checking pyproject.toml first.

- [ ] **Step 2: Write failing tests**

Create `tests/memory/__init__.py` (empty).

Create `tests/memory/test_store.py`:

```python
import pytest
import asyncio
from perpetua_core.memory.store import EmbeddingStore


@pytest.mark.asyncio
async def test_store_add_and_search(tmp_path):
    """Add a row, search for it by embedding."""
    store = EmbeddingStore(str(tmp_path / "test.lance"))
    embedding = [0.1] * 1024
    await store.add(row_id=1, text="blue widget task", embedding=embedding)
    results = await store.search(embedding, limit=5)
    assert len(results) >= 1
    assert results[0]["row_id"] == 1


@pytest.mark.asyncio
async def test_store_search_empty_returns_empty(tmp_path):
    """Search on empty store returns empty list."""
    store = EmbeddingStore(str(tmp_path / "empty.lance"))
    results = await store.search([0.0] * 1024, limit=5)
    assert results == []


@pytest.mark.asyncio
async def test_store_search_never_raises_on_bad_input(tmp_path):
    """Malformed embedding → empty list, no exception."""
    store = EmbeddingStore(str(tmp_path / "bad.lance"))
    try:
        results = await store.search([], limit=5)
        assert isinstance(results, list)
    except Exception as e:
        pytest.fail(f"store.search raised: {e}")
```

Create `tests/memory/test_rrf.py`:

```python
from perpetua_core.memory.rrf import rrf_merge


def test_rrf_fts_only_when_no_vec():
    """If vec_hits empty, return fts_hits unchanged."""
    fts = [{"row_id": 1}, {"row_id": 2}]
    result = rrf_merge(fts, [])
    assert result == fts


def test_rrf_merges_and_deduplicates():
    """Same row_id in both lists appears once in output."""
    fts = [{"row_id": 1, "text": "a"}, {"row_id": 2, "text": "b"}]
    vec = [{"row_id": 2, "text": "b"}, {"row_id": 3, "text": "c"}]
    result = rrf_merge(fts, vec)
    row_ids = [r["row_id"] for r in result]
    assert len(row_ids) == len(set(row_ids))  # no duplicates
    assert set(row_ids) == {1, 2, 3}


def test_rrf_top_ranked_item_appears_first():
    """Item ranked #1 in both lists gets highest RRF score."""
    fts = [{"row_id": 10}, {"row_id": 20}]
    vec = [{"row_id": 10}, {"row_id": 30}]
    result = rrf_merge(fts, vec)
    assert result[0]["row_id"] == 10  # #1 in both → highest fused score
```

- [ ] **Step 3: Run tests — verify 6 fail**

```bash
python -m pytest tests/memory/ -v
```

- [ ] **Step 4: Create `perpetua_core/memory/__init__.py`** (empty)

- [ ] **Step 5: Create `perpetua_core/memory/store.py`**

```python
"""EmbeddingStore — LanceDB-backed vector store for GossipBus embeddings."""
import asyncio
from typing import Optional

try:
    import lancedb
    import pyarrow as pa
    _LANCEDB_AVAILABLE = True
except ImportError:
    _LANCEDB_AVAILABLE = False


class EmbeddingStore:
    """Local LanceDB vector store. Falls back to no-op if unavailable."""

    def __init__(self, db_path: str = "lance_memory.lance"):
        self._db_path = db_path
        self._table = None

    def _get_schema(self):
        import pyarrow as pa
        return pa.schema([
            pa.field("row_id", pa.int64()),
            pa.field("text", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), 1024)),
        ])

    async def _ensure_table(self):
        if not _LANCEDB_AVAILABLE or self._table is not None:
            return
        loop = asyncio.get_event_loop()
        def _open():
            db = lancedb.connect(self._db_path)
            if "gossip" in db.table_names():
                return db.open_table("gossip")
            return db.create_table("gossip", schema=self._get_schema())
        self._table = await loop.run_in_executor(None, _open)

    async def add(self, row_id: int, text: str, embedding: list[float]) -> None:
        if not _LANCEDB_AVAILABLE:
            return
        await self._ensure_table()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._table.add([{"row_id": row_id, "text": text, "vector": embedding}])
        )

    async def search(self, query_embedding: list[float], limit: int = 10) -> list[dict]:
        if not _LANCEDB_AVAILABLE or not query_embedding:
            return []
        try:
            await self._ensure_table()
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._table.search(query_embedding).limit(limit).to_list()
            )
            return [
                {"row_id": r["row_id"], "text": r["text"], "score": r.get("_distance", 0.0)}
                for r in results
            ]
        except Exception:
            return []


# Path-keyed singletons — one per db_path to avoid test isolation failures.
# (A module-level singleton without path keying locks to the first path seen,
# causing tests that use tmp_path to silently share state. Fixed in autoplan.)
_lance_stores: dict[str, "EmbeddingStore"] = {}


def get_lance_store(db_path: str = "lance_memory.lance") -> "EmbeddingStore":
    if db_path not in _lance_stores:
        _lance_stores[db_path] = EmbeddingStore(db_path)
    return _lance_stores[db_path]
```

- [ ] **Step 6: Create `perpetua_core/memory/embed.py`**

```python
"""get_embedding() — Ollama bge-m3 embedding via localhost:11434."""
import asyncio
import json
import os
from typing import Optional

import aiohttp

_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")


async def get_embedding(text: str) -> list[float]:
    """Call Ollama bge-m3 to embed text. Returns 1024-dim float list.

    Raises on failure — callers should try/except and fall back to FTS5-only.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{_OLLAMA_URL}/api/embeddings",
            json={"model": _EMBED_MODEL, "prompt": text},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["embedding"]
```

Note: `aiohttp` is likely already a dep in perpetua-core; if not, add it. Alternatively
use `httpx` if that's already present.

- [ ] **Step 7: Create `perpetua_core/memory/rrf.py`**

```python
"""Reciprocal Rank Fusion — merges FTS5 and LanceDB result lists."""


def rrf_merge(
    fts_hits: list[dict],
    vec_hits: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge FTS5 and vector hits via RRF (k=60, per CRG hybrid search convention).

    Disaster recovery posture: if vec_hits is empty (Ollama down, LanceDB
    error), returns fts_hits unmodified so the system always has context.
    """
    if not vec_hits:
        return fts_hits

    scores: dict[int, float] = {}
    id_to_item: dict[int, dict] = {}

    for rank, hit in enumerate(fts_hits):
        rid = hit.get("row_id", -(rank + 1))
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[rid] = hit

    for rank, hit in enumerate(vec_hits):
        rid = hit.get("row_id", -(rank + 10000))
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
        if rid not in id_to_item:
            id_to_item[rid] = hit

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [id_to_item[rid] for rid, _ in ranked]
```

- [ ] **Step 8: Run 6 tests — verify they pass**

```bash
python -m pytest tests/memory/ -v
```

- [ ] **Step 9: Run full perpetua-core suite**

```bash
python -m pytest tests/ -v
```

---

### Task 3 — GbrainSearchTool @tool (perpetua-core)

**Files:** `perpetua_core/graph/tools/gbrain_search.py` (create), `tests/graph/tools/test_gbrain_search.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/tools/__init__.py` (empty).
Create `tests/graph/tools/test_gbrain_search.py`:

```python
import pytest
import subprocess
import json
from unittest.mock import patch
from perpetua_core.graph.tools.gbrain_search import gbrain_search


def test_gbrain_search_returns_empty_when_cli_absent():
    """FileNotFoundError (gbrain not on PATH) → empty list, no raise."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_returns_empty_on_timeout():
    """TimeoutExpired → empty list, no raise."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gbrain", timeout=10)):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_returns_empty_on_nonzero_exit():
    """returncode != 0 → empty list."""
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=fake):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_parses_json_output():
    """Valid JSON stdout → parsed list."""
    payload = [{"title": "test page", "score": 0.9}]
    fake = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(payload), stderr=""
    )
    with patch("subprocess.run", return_value=fake):
        result = gbrain_search(query="test")
    assert result == payload
```

- [ ] **Step 2: Run tests — verify 4 fail**

```bash
python -m pytest tests/graph/tools/test_gbrain_search.py -v
```

- [ ] **Step 3: Create `perpetua_core/graph/tools/__init__.py`** (empty)

- [ ] **Step 4: Create `perpetua_core/graph/tools/gbrain_search.py`**

```python
"""GbrainSearch — optional semantic memory tool via gbrain CLI subprocess.

Gracefully returns [] if gbrain is not installed, times out, or errors.
Never raises — callers treat absence as no results.
"""
import asyncio
import json
import subprocess
from perpetua_core.graph.plugins.tool import tool


@tool
async def gbrain_search(query: str, limit: int = 5) -> list[dict]:
    """Search gbrain semantic memory for relevant past knowledge.

    Returns an empty list if gbrain CLI is unavailable — never raises.
    Runs subprocess in executor to avoid blocking the async event loop.
    """
    def _run():
        try:
            result = subprocess.run(
                ["gbrain", "query", query, "--limit", str(limit), "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            return json.loads(result.stdout) if result.stdout.strip() else []
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)
```

- [ ] **Step 5: Run 4 tests — verify they pass**

```bash
python -m pytest tests/graph/tools/test_gbrain_search.py -v
```

- [ ] **Step 6: Run full perpetua-core suite**

```bash
python -m pytest tests/ -v
```

---

### Task 4 — MemoryNode in oramasys

**Files:** `orama/graph/nodes/memory_node.py` (create), `orama/graph/perpetua_graph.py` (modify)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/__init__.py` (empty if not existing).
Create `tests/graph/test_memory_node.py`:

```python
import asyncio
import os
import pytest
from unittest.mock import patch, AsyncMock
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus


@pytest.mark.asyncio
async def test_memory_node_empty_db_returns_empty_context(tmp_path):
    """Empty GossipBus + empty LanceDB → context is empty list."""
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()

    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db, "LANCE_DB_PATH": str(tmp_path / "l.lance")}):
        from orama.graph.nodes.memory_node import memory_node
        state = PerpetuaState(session_id="t1", scratchpad={"prompt": "hello"})
        delta = await memory_node(state)

    assert delta.get("scratchpad", {}).get("context") == []


@pytest.mark.asyncio
async def test_memory_node_fts5_finds_relevant_hits(tmp_path):
    """FTS5 hits from GossipBus injected into scratchpad even when LanceDB fails."""
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()
    await bus.emit("dispatch", {"prompt": "summarize the quarterly report"})

    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db, "LANCE_DB_PATH": str(tmp_path / "l.lance")}):
        # LanceDB will be empty — RRF falls back to FTS5 only
        from orama.graph.nodes.memory_node import memory_node
        state = PerpetuaState(session_id="t2", scratchpad={"prompt": "quarterly report"})
        delta = await memory_node(state)

    hits = delta.get("scratchpad", {}).get("context", [])
    assert len(hits) >= 1
    assert any("quarterly" in str(h) for h in hits)


@pytest.mark.asyncio
async def test_memory_node_graceful_on_lance_failure(tmp_path):
    """LanceDB error → falls back to FTS5 hits only, no exception raised."""
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()
    await bus.emit("dispatch", {"prompt": "test prompt"})

    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db}):
        with patch("perpetua_core.memory.store.EmbeddingStore.search",
                   new_callable=AsyncMock, side_effect=Exception("lance down")):
            from orama.graph.nodes.memory_node import memory_node
            state = PerpetuaState(session_id="t3", scratchpad={"prompt": "test prompt"})
            try:
                delta = await memory_node(state)
            except Exception as e:
                pytest.fail(f"memory_node raised: {e}")

    # Must have context from FTS5 fallback
    hits = delta.get("scratchpad", {}).get("context", [])
    assert isinstance(hits, list)


@pytest.mark.asyncio
async def test_memory_node_empty_prompt_returns_empty(tmp_path):
    """Empty prompt → empty context, no search attempted."""
    db = str(tmp_path / "test.db")
    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db}):
        from orama.graph.nodes.memory_node import memory_node
        state = PerpetuaState(session_id="t4", scratchpad={"prompt": ""})
        delta = await memory_node(state)
    assert delta["scratchpad"]["context"] == []
```

- [ ] **Step 2: Run tests — verify 4 fail**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/graph/test_memory_node.py -v
```

- [ ] **Step 3: Create `orama/graph/nodes/__init__.py`** (empty or verify exists)

- [ ] **Step 4: Create `orama/graph/nodes/memory_node.py`**

```python
"""MemoryNode — first graph node. Hybrid FTS5 + LanceDB recall with RRF merge."""
import os
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus
from perpetua_core.memory.store import get_lance_store
from perpetua_core.memory.embed import get_embedding
from perpetua_core.memory.rrf import rrf_merge

_GOSSIP_DB = os.environ.get("GOSSIP_DB_PATH", "perpetua_core.db")
_LANCE_DB  = os.environ.get("LANCE_DB_PATH",  "lance_memory.lance")


async def memory_node(state: PerpetuaState) -> dict:
    """Retrieve context via FTS5 (always) + LanceDB (try/except) + RRF merge.

    Disaster recovery posture: if LanceDB or Ollama is unavailable, FTS5
    keyword recall still works. RRF falls back to FTS5-only when vec_hits=[].
    """
    prompt = state.scratchpad.get("prompt", "")
    if not prompt:
        return {"scratchpad": {**state.scratchpad, "context": []}}

    # FTS5 keyword recall — always works (stdlib, no external deps)
    try:
        bus = GossipBus(_GOSSIP_DB)
        await bus.init_db()
        fts_hits = await bus.search(prompt, limit=10)
    except Exception:
        fts_hits = []

    # LanceDB vector recall — opportunistic, graceful fallback
    vec_hits: list[dict] = []
    try:
        embedding = await get_embedding(prompt)
        store = get_lance_store(_LANCE_DB)
        vec_hits = await store.search(embedding, limit=10)
    except Exception:
        pass  # Fall through to FTS5-only via rrf_merge([...], [])

    merged = rrf_merge(fts_hits, vec_hits)[:5]
    return {"scratchpad": {**state.scratchpad, "context": merged}}
```

- [ ] **Step 5: Wire MemoryNode into `orama/graph/perpetua_graph.py`**

Find the existing graph construction. Replace `ContextNode` with `MemoryNode`:

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

- [ ] **Step 6: Run tests — verify 4 pass, prior 4 still pass**

```bash
python -m pytest tests/ -v
```

---

### Task 5 — Commit 1

- [ ] **Step 1: Verify all tests pass in perpetua-core**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/ -v
```

Expected: 32 prior + 17 new = 49 passing

- [ ] **Step 2: Verify all tests pass in oramasys**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/ -v
```

Expected: 4 prior + 4 new = 8 passing

- [ ] **Step 3: Commit perpetua-core**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
git add perpetua_core/gossip.py \
        perpetua_core/memory/__init__.py \
        perpetua_core/memory/store.py \
        perpetua_core/memory/embed.py \
        perpetua_core/memory/rrf.py \
        perpetua_core/graph/tools/__init__.py \
        perpetua_core/graph/tools/gbrain_search.py \
        tests/test_gossip_search.py \
        tests/memory/__init__.py \
        tests/memory/test_store.py \
        tests/memory/test_rrf.py \
        tests/graph/tools/__init__.py \
        tests/graph/tools/test_gbrain_search.py \
        pyproject.toml
git commit -m "$(cat <<'EOF'
feat(rag): FTS5 + LanceDB hybrid GossipBus search with RRF + GbrainSearchTool

Hybrid retrieval layer for GossipBus:
- FTS5 virtual table + BM25 triggers (always-available keyword recall)
- LanceDB EmbeddingStore (vector recall via Ollama bge-m3)
- fire-and-forget asyncio.create_task() embed in emit()
- _pending_embeds: set[Task] to prevent GC of in-flight tasks
- embed_status column ('pending'/'embedded'/'failed') for v2.5 reaper
- rrf_merge() k=60 RRF fusion — falls back to FTS5-only if LanceDB unavailable
- GbrainSearchTool @tool — graceful subprocess wrapper (returns [] on any failure)

Decision trail: AI proposed FTS5-only + background daemon.
User overrode to hybrid LanceDB+FTS5 with inline fire-and-forget.

Tests: 17 new passing (7 FTS5 + 3 LanceDB + 3 RRF + 4 gbrain tool).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Commit oramasys**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
git add orama/graph/nodes/__init__.py \
        orama/graph/nodes/memory_node.py \
        orama/graph/perpetua_graph.py \
        tests/graph/__init__.py \
        tests/graph/test_memory_node.py
git commit -m "$(cat <<'EOF'
feat(graph): MemoryNode — hybrid FTS5+LanceDB recall with RRF, replaces ContextNode

MemoryNode (node 0 in perpetua_graph):
- Queries FTS5 (always) + LanceDB (try/except) in parallel
- Merges results with RRF k=60
- Injects top-5 merged hits into scratchpad["context"]
- Graceful: FTS5-only mode when LanceDB/Ollama unavailable
- Graceful: empty context when DB absent or prompt empty

Tests: +4 (8 total, all passing).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## COMMIT 2: Generation Layer

### Task 6 — Wire LLMClient into dispatch_node

**Files:** `orama/graph/nodes/dispatch_node.py` (modify), `tests/graph/test_dispatch_node.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/test_dispatch_node.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, patch
from perpetua_core.state import PerpetuaState


@pytest.mark.asyncio
async def test_dispatch_node_calls_llm_with_context():
    """dispatch_node must pass context hits in the system prompt."""
    context_hits = [
        {"ts": 1.0, "event_type": "dispatch", "payload": {"prompt": "prior task"}}
    ]
    state = PerpetuaState(
        session_id="t1",
        scratchpad={"prompt": "new task", "context": context_hits},
    )
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value="LLM answer")

    with patch("orama.graph.nodes.dispatch_node.LLMClient", return_value=mock_client):
        from orama.graph.nodes.dispatch_node import dispatch_node
        delta = await dispatch_node(state)

    assert delta["scratchpad"]["response"] == "LLM answer"
    call_args = mock_client.chat.call_args
    messages = call_args[0][0]
    system_msg = next(m for m in messages if m["role"] == "system")
    assert "prior task" in system_msg["content"]


@pytest.mark.asyncio
async def test_dispatch_node_falls_back_on_llm_error():
    """LLMClient exception → error stored in scratchpad, no raise."""
    state = PerpetuaState(session_id="t2", scratchpad={"prompt": "test"})
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("model unreachable"))

    with patch("orama.graph.nodes.dispatch_node.LLMClient", return_value=mock_client):
        from orama.graph.nodes.dispatch_node import dispatch_node
        delta = await dispatch_node(state)

    assert "error" in delta["scratchpad"]["response"].lower()


@pytest.mark.asyncio
async def test_dispatch_node_empty_context_uses_default_string():
    """No context hits → system prompt contains fallback text."""
    state = PerpetuaState(session_id="t3", scratchpad={"prompt": "hello", "context": []})
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value="response")

    with patch("orama.graph.nodes.dispatch_node.LLMClient", return_value=mock_client):
        from orama.graph.nodes.dispatch_node import dispatch_node
        delta = await dispatch_node(state)

    messages = mock_client.chat.call_args[0][0]
    system_msg = next(m for m in messages if m["role"] == "system")
    assert "No prior context" in system_msg["content"]
```

- [ ] **Step 2: Run tests — verify 3 fail**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/graph/test_dispatch_node.py -v
```

- [ ] **Step 3: Implement dispatch_node.py**

```python
"""dispatch_node — calls LLMClient with context-injected system prompt."""
import json
import os
from perpetua_core.state import PerpetuaState
from perpetua_core.llm import LLMClient

_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1")
_LLM_MODEL    = os.environ.get("LLM_MODEL", "default")

_SYSTEM_TEMPLATE = """\
You are an AI assistant with access to relevant context from past sessions.

Context from memory:
{context}

Hardware tier: {tier}
Task type: {task_type}
"""


async def dispatch_node(state: PerpetuaState) -> dict:
    """Dispatch to LLMClient with MemoryNode context in system prompt."""
    context_hits = state.scratchpad.get("context", [])
    if context_hits:
        context_str = "\n".join(
            f"[{h.get('event_type', 'event')}] {json.dumps(h.get('payload', h))}"
            for h in context_hits[:5]
        )
    else:
        context_str = "No prior context available."

    system = _SYSTEM_TEMPLATE.format(
        context=context_str,
        tier=getattr(state, "target_tier", "unknown"),
        task_type=getattr(state, "task_type", ""),
    )
    prompt = state.scratchpad.get("prompt", "")

    try:
        client = LLMClient(base_url=_LLM_BASE_URL, model=_LLM_MODEL)
        response = await client.chat([
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ])
    except Exception as exc:
        response = f"[dispatch error: {exc}]"

    return {"scratchpad": {**state.scratchpad, "response": response}}
```

- [ ] **Step 4: Run 3 tests — verify they pass**

```bash
python -m pytest tests/graph/test_dispatch_node.py -v
```

- [ ] **Step 5: Run full suite**

```bash
python -m pytest tests/ -v
```

Expected: 8 prior + 3 new = 11 passing

---

### Task 7 — Commit 2

- [ ] **Step 1: Final test run across both repos**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core && python -m pytest tests/ -v
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys && python -m pytest tests/ -v
```

All must be green.

- [ ] **Step 2: Commit (oramasys)**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
git add orama/graph/nodes/dispatch_node.py \
        tests/graph/test_dispatch_node.py
git commit -m "$(cat <<'EOF'
feat(dispatch): wire LLMClient into dispatch_node with context injection

Replace echo stub with real LLMClient.chat() call. System prompt
includes top-5 merged hits from MemoryNode (FTS5+LanceDB RRF).
Graceful fallback on LLM error — stores error string in scratchpad.
LLM_BASE_URL and LLM_MODEL configured via env vars.

Tests: +3 (11 total, all passing).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Verification After Both Commits

```bash
# 1. perpetua-core: all tests green
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/ -v  # expect 49+ passing

# 2. oramasys: all tests green
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/ -v  # expect 11+ passing

# 3. Smoke test (requires Ollama running at localhost:11434)
curl -s http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What did we work on last time?"}' | jq .

# Expected: output contains LLM response with context from GossipBus history
# LanceDB+FTS5 → merged top-5 hits in system prompt
# If Ollama not running → FTS5-only fallback still returns context
# If LM Studio not running → "[dispatch error: ...]" — graceful
```
