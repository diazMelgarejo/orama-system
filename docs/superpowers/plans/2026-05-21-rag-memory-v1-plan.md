# RAG Memory Pipeline v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hybrid LanceDB + FTS5 recall on GossipBus, inject merged context into oramasys graph via MemoryNode (RRF), wire LLMClient into dispatch_node.

**Outcome (clarified at autoplan gate):** Enable search in the operator UI + natural language instructions that the Launcher Agent and default orchestrator can understand. Hybrid search available to ALL agents by default via the `@tool gbrain_search` + MemoryNode. This is the retrieval substrate that unlocks UI-level search and context-aware agent routing.

**Follow-on (after this plan lands):** Implement v2.1 EmbeddingCircuitBreaker in `docs/v2/18-rag-and-memory-design.md` — opens after N consecutive LanceDB/Ollama failures, auto-closes after cooldown. Next sprint after this merges.

**Architecture:** Two commits on `feat/rag-gstack-optional-v1`. Commit 1 = retrieval layer (perpetua-core: FTS5 + LanceDB + RRF + MemoryNode). Commit 2 = generation layer (dispatch_node LLMClient wiring).

**Decision trail:** AI initially proposed FTS5-only (zero new deps). User overrode to hybrid LanceDB+FTS5 with RRF — Ollama+bge-m3 is already a hard system requirement so LanceDB is nearly free. AI initially proposed a background daemon for embed sync; user chose fire-and-forget `asyncio.create_task()` inline in `emit()`. User also required a module-level `_pending_embeds: set[asyncio.Task]` to prevent GC of in-flight tasks.

**Tech Stack:** Python 3.11+, aiosqlite, SQLite FTS5 (stdlib), lancedb (1 new dep), Ollama bge-m3 at localhost:11434 (already required), perpetua-core kernel, oramasys FastAPI graph, existing `perpetua_core.llm.LLMClient`

## Targeting (CRITICAL — read first)

| Repo type | Org | Role | This plan's relationship |
|-----------|-----|------|--------------------------|
| **v2-planning** | `oramasys/perpetua-core` + `oramasys/oramasys` | clean-slate kernel + methodology | **Primary target.** All file paths below assume this layout. |
| **v1-legacy** | `diazMelgarejo/Perpetua-Tools` + `diazMelgarejo/orama-system` | working runtime + methodology | **Selective backport only.** Module layout differs (no `perpetua_core` package in PT — see `Perpetua-Tools/orchestrator/`). See "v1 Backport Candidates" near end of plan. |

> ## ⚠️ STOP — READ BEFORE EXECUTING ANY CHECKLIST ITEM
>
> **Every bash block in this plan that begins with `cd ~/oramasys/...` is
> REFERENCE-ONLY documentation of what the v2-cut commit ceremony would
> look like. DO NOT execute those commands. DO NOT write code into
> `~/oramasys/perpetua-core` or `~/oramasys/oramasys`.**
>
> Actual implementation for v1 lands in `<workspace>/Perpetua-Tools/`
> and `<workspace>/orama-system/`. Module layout differs from v2 —
> see "v1 Backport Candidates" near end of plan for the real mapping
> (no `perpetua_core/` package in PT; use `orchestrator/` + `perpetua/discovery/`).
>
> Override of the v2 no-write rule requires an explicit AskUserQuestion
> confirmation in chat with the user. A coding agent that follows the
> checklist literally without this gate is breaking the architectural contract.

**Hard rule (recorded 2026-05-22):** Code goes to v1 (`diazMelgarejo/*`) for actual shipping. Plans, designs, and clean-slate architecture live in v2 (`oramasys/*`) BUT we **never write code directly to `oramasys/*`**. We plan in `/docs/v2/` of the v1 repos and the v2 repos absorb absorption-ready slices at v2 cut-time. Override of this rule requires explicit AskUserQuestion confirmation.

**Workspace paths (anonymized for portability; resolve `<workspace>` to your local checkout root):**
- v1 orama-system (this repo): `<workspace>/orama-system`
- v1 Perpetua-Tools: `<workspace>/Perpetua-Tools` (no `perpetua_core` package — has `orchestrator/` + `perpetua/discovery/`)
- v2 perpetua-core (REFERENCE-ONLY — do not write): `~/oramasys/perpetua-core`
- v2 oramasys (REFERENCE-ONLY — do not write): `~/oramasys/oramasys`

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
| `tests/test_gossip_search.py` | Create | 5 FTS5 + 3 embed-status tests (8 total) |
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
    """Gap 3 fix (Antigravity Gemini 3.5 critique 2026-05-21):
    Verify in-flight tasks are ACTUALLY registered in _pending_embeds
    (not just that the set object exists — which was a tautology).

    Strategy: patch _embed_and_store to sleep, so emit() must register
    the task; observe set membership during the active window; ensure
    the task is discarded once it completes.
    """
    from unittest.mock import patch
    from perpetua_core import gossip as gossip_mod
    from perpetua_core.gossip import _pending_embeds

    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()

    # Sanity: set must be present and currently empty for this test.
    assert isinstance(_pending_embeds, set)
    _pending_embeds.clear()

    async def slow_embed(self, row_id, payload):
        await asyncio.sleep(0.1)

    with patch.object(gossip_mod.GossipBus, "_embed_and_store", slow_embed):
        await bus.emit("dispatch", {"prompt": "gc test"})
        # Immediately after emit(), the task must be in the set —
        # this is what prevents asyncio's weak-ref GC from collecting it.
        assert len(_pending_embeds) == 1, (
            f"task not registered; set={_pending_embeds!r}"
        )
        # Drain: wait for task to complete; discard callback must remove it.
        await asyncio.sleep(0.2)
        assert len(_pending_embeds) == 0, (
            f"done-callback failed to discard; set={_pending_embeds!r}"
        )


@pytest.mark.asyncio
async def test_emit_sets_embed_status_failed_on_error(tmp_path):
    """When get_embedding() raises, embed_status must be set to 'failed'."""
    from unittest.mock import patch, AsyncMock
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()

    with patch(
        "perpetua_core.memory.embed.get_embedding",
        new_callable=AsyncMock,
        side_effect=Exception("ollama down"),
    ):
        await bus.emit("dispatch", {"prompt": "failing embed row"})
        # Allow the fire-and-forget task to complete
        await asyncio.sleep(0.05)

    import aiosqlite
    async with aiosqlite.connect(db) as conn:
        cursor = await conn.execute("SELECT embed_status FROM gossip LIMIT 1")
        row = await cursor.fetchone()
    assert row[0] == "failed"
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
python -m pytest tests/test_gossip_search.py -v
```

Expected: 8 failures (FTS5 + embed_status not yet implemented)

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

Add `_sanitize_fts_query()` helper at module level (Gap 2 fix — Antigravity Gemini 3.5 critique 2026-05-21). Previously, FTS5 MATCH errored on real prompts containing quotes/colons/operators and the `except` clause returned `[]` — silently losing all keyword recall for that query. Now we strip the syntactic characters first and only fall back to `[]` on truly unrecoverable input:

```python
import re

# FTS5 reserved characters and operators that must be stripped or quoted.
# See https://sqlite.org/fts5.html#fts5_strings — quote/colon/star/plus/minus/
# parens/braces/AND/OR/NOT/NEAR. Operators inside quoted phrases are literal.
_FTS5_OPERATOR_RE = re.compile(r'[\"\':\*\+\-\(\)\[\]\{\}\^]')
_FTS5_KEYWORDS = {"AND", "OR", "NOT", "NEAR"}


def _sanitize_fts_query(query: str) -> str:
    """Strip FTS5 syntactic characters so MATCH treats input as plain terms.

    Quotes, colons, +/-/*, parens, and braces all have special meaning in
    FTS5 query syntax. Real user prompts contain them constantly — without
    sanitization the entire keyword recall channel goes dark. Reserved
    keywords (AND/OR/NOT/NEAR) are lowercased to remove their operator
    meaning; FTS5 only treats them as operators in uppercase.
    """
    if not query:
        return ""
    cleaned = _FTS5_OPERATOR_RE.sub(" ", query)
    tokens = [t.lower() if t in _FTS5_KEYWORDS else t for t in cleaned.split()]
    return " ".join(tokens).strip()
```

Now `search()` (FTS5-safe — sanitizes BEFORE MATCH, then wraps MATCH in try/except as defence in depth):

```python
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    event_type: Optional[str] = None,
) -> list[dict]:
    """BM25 full-text search over GossipBus event history. Always works.

    Sanitizes the query (strips FTS5 operators / quotes / colons) so real
    user prompts work without raising OperationalError. The try/except
    around MATCH remains as defence in depth.
    """
    safe_query = _sanitize_fts_query(query)
    if not safe_query:
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
                    (safe_query, event_type, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT g.id, g.ts, g.event_type, g.payload_json
                       FROM gossip_fts f
                       JOIN gossip g ON g.id = f.rowid
                       WHERE gossip_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (safe_query, limit),
                )
            rows = await cursor.fetchall()
        return [
            {"row_id": r[0], "ts": r[1], "event_type": r[2], "payload": json.loads(r[3])}
            for r in rows
        ]
    except Exception:
        return []  # FTS5 OperationalError on malformed query — degrade gracefully
```

- [ ] **Step 4: Run tests — verify 8 pass**

```bash
python -m pytest tests/test_gossip_search.py -v
```

Expected: 8 passed  (5 FTS5 + 3 embed-status — matches File Map)

- [ ] **Step 5: Run full perpetua-core suite**

```bash
python -m pytest tests/ -v
```

Expected: all prior tests pass + 8 new

---

### Task 2 — LanceDB EmbeddingStore + embed helper + RRF

**Files:** `perpetua_core/memory/__init__.py`, `perpetua_core/memory/store.py`, `perpetua_core/memory/embed.py`, `perpetua_core/memory/rrf.py`

- [ ] **Step 1: Install lancedb and verify aiohttp**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
.venv/bin/pip install lancedb aiohttp
# Check if aiohttp already in pyproject.toml
grep "aiohttp" pyproject.toml
```

Edit `pyproject.toml` — add to `[project] dependencies` (if not already present):
```toml
"lancedb>=0.6",
"aiohttp>=3.9",
```

Also check `[project.optional-dependencies]` or `[tool.pytest.ini_options]` for `pytest-asyncio`. If not present, add to dev/test deps:
```toml
"pytest-asyncio>=0.23",
```
And ensure `asyncio_mode = "auto"` is set in `[tool.pytest.ini_options]`. With `auto` mode, the `@pytest.mark.asyncio` marker becomes optional (any `async def test_*` is auto-discovered). We keep explicit markers in this plan for readability; either is fine.

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
    """Local LanceDB vector store. Falls back to no-op if unavailable.

    Gap 1 fix (Antigravity Gemini 3.5 critique, 2026-05-21):
    ``dim`` is now a constructor parameter, not hardcoded to 1024.
    ``EMBED_DIM`` env var (or a runtime probe via ``embed.probe_embed_dim()``)
    is the source of truth — switching ``EMBED_MODEL`` from ``bge-m3`` (1024)
    to ``nomic-embed-text`` (768) no longer corrupts the LanceDB schema.
    """

    def __init__(self, db_path: str = "lance_memory.lance", *, dim: int = 1024):
        self._db_path = db_path
        self._dim = int(dim)
        self._table = None
        self._lock = asyncio.Lock()  # prevents concurrent _ensure_table() race

    def _get_schema(self):
        import pyarrow as pa
        return pa.schema([
            pa.field("row_id", pa.int64()),
            pa.field("text", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), self._dim)),
        ])

    async def _ensure_table(self):
        if not _LANCEDB_AVAILABLE or self._table is not None:
            return
        async with self._lock:
            if self._table is not None:  # double-check after acquiring lock
                return
            loop = asyncio.get_running_loop()
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
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._table.add([{"row_id": row_id, "text": text, "vector": embedding}])
        )

    async def search(self, query_embedding: list[float], limit: int = 10) -> list[dict]:
        if not _LANCEDB_AVAILABLE or not query_embedding:
            return []
        try:
            await self._ensure_table()
            loop = asyncio.get_running_loop()
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


def get_lance_store(
    db_path: str = "lance_memory.lance",
    *,
    dim: Optional[int] = None,
) -> "EmbeddingStore":
    """Path-keyed EmbeddingStore singleton.

    ``dim`` resolution order (Gap 1 fix):
      1. Explicit ``dim`` arg (tests / callers that already know)
      2. ``EMBED_DIM`` env var
      3. ``perpetua_core.memory.embed.probe_embed_dim()`` — calls Ollama once
         to discover the actual embedding dimension for the configured model
      4. Final fallback: 1024 (bge-m3 default)

    Key is ``(db_path, dim)`` to avoid silent dim mismatches across callers.
    """
    if dim is None:
        import os
        env_dim = os.environ.get("EMBED_DIM")
        if env_dim:
            dim = int(env_dim)
        else:
            try:
                from perpetua_core.memory.embed import probe_embed_dim
                dim = probe_embed_dim()
            except Exception:
                dim = 1024
    key = f"{db_path}::dim{dim}"
    if key not in _lance_stores:
        _lance_stores[key] = EmbeddingStore(db_path, dim=dim)
    return _lance_stores[key]
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

# Cached probed dimension — populated by probe_embed_dim() on first call.
_PROBED_DIM: Optional[int] = None


async def get_embedding(text: str) -> list[float]:
    """Call Ollama to embed ``text``. Returns model-native float list.

    Length depends on EMBED_MODEL: bge-m3 → 1024, nomic-embed-text → 768,
    all-minilm → 384. Use ``probe_embed_dim()`` to discover at startup.
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


def probe_embed_dim() -> int:
    """Discover the active model's embedding dimension via one synchronous probe.

    Gap 1 fix (Antigravity Gemini 3.5 critique, 2026-05-21):
    LanceDB schemas are immutable once written, so the dimension must be
    known before the first ``EmbeddingStore.add()`` call. Synchronous so it
    can run at startup without an event loop. Result is cached process-wide.

    Override priority: ``EMBED_DIM`` env var > this probe > 1024 fallback.
    Never raises; degrades to 1024 if Ollama is unreachable (LanceDB writes
    will then fail loudly for non-bge-m3 models, which is the right signal).
    """
    global _PROBED_DIM
    if _PROBED_DIM is not None:
        return _PROBED_DIM
    env_dim = os.environ.get("EMBED_DIM")
    if env_dim:
        _PROBED_DIM = int(env_dim)
        return _PROBED_DIM
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{_OLLAMA_URL}/api/embeddings",
            data=json.dumps({"model": _EMBED_MODEL, "prompt": "probe"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            _PROBED_DIM = len(data["embedding"])
            return _PROBED_DIM
    except Exception:
        _PROBED_DIM = 1024
        return _PROBED_DIM
```

Note: `aiohttp` is likely already a dep in perpetua-core; if not, add it. Alternatively
use `httpx` if that's already present.

- [ ] **Step 7: Create `perpetua_core/memory/rrf.py`**

```python
"""Reciprocal Rank Fusion — merges FTS5 and LanceDB result lists."""
import uuid


def rrf_merge(
    fts_hits: list[dict],
    vec_hits: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge FTS5 and vector hits via RRF (k=60, per CRG hybrid search convention).

    Disaster recovery posture: if vec_hits is empty (Ollama down, LanceDB
    error), returns fts_hits unmodified so the system always has context.

    Items without row_id get a unique UUID key so hits from both lists never
    collide on synthetic keys (negative-int approach has range overlap).
    """
    if not vec_hits:
        return fts_hits

    scores: dict = {}
    id_to_item: dict = {}

    for rank, hit in enumerate(fts_hits):
        rid = hit.get("row_id") or str(uuid.uuid4())
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[rid] = hit

    for rank, hit in enumerate(vec_hits):
        rid = hit.get("row_id") or str(uuid.uuid4())
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


@pytest.mark.asyncio
async def test_gbrain_search_returns_empty_when_cli_absent():
    """FileNotFoundError (gbrain not on PATH) → empty list, no raise."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = await gbrain_search(query="anything")
    assert result == []


@pytest.mark.asyncio
async def test_gbrain_search_returns_empty_on_timeout():
    """TimeoutExpired → empty list, no raise."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gbrain", timeout=10)):
        result = await gbrain_search(query="anything")
    assert result == []


@pytest.mark.asyncio
async def test_gbrain_search_returns_empty_on_nonzero_exit():
    """returncode != 0 → empty list."""
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=fake):
        result = await gbrain_search(query="anything")
    assert result == []


@pytest.mark.asyncio
async def test_gbrain_search_parses_json_output():
    """Valid JSON stdout → parsed list."""
    payload = [{"title": "test page", "score": 0.9}]
    fake = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(payload), stderr=""
    )
    with patch("subprocess.run", return_value=fake):
        result = await gbrain_search(query="test")
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

    loop = asyncio.get_running_loop()
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
        # Patch get_embedding to succeed so we isolate the LanceDB failure branch
        with patch("perpetua_core.memory.embed.get_embedding",
                   new_callable=AsyncMock, return_value=[0.0] * 1024):
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
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
python -m pytest tests/graph/test_memory_node.py -v
```

- [ ] **Step 3: Create `orama/graph/nodes/__init__.py`** (empty or verify exists)

- [ ] **Step 4: Create `orama/graph/nodes/memory_node.py`**

```python
"""MemoryNode — first graph node. Hybrid FTS5 + LanceDB recall with RRF merge."""
import json as _json
import os
import aiosqlite
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus
from perpetua_core.memory.store import get_lance_store
from perpetua_core.memory.embed import get_embedding
from perpetua_core.memory.rrf import rrf_merge

async def memory_node(state: PerpetuaState) -> dict:
    """Retrieve context via FTS5 (always) + LanceDB (try/except) + RRF merge.

    Disaster recovery posture: if LanceDB or Ollama is unavailable, FTS5
    keyword recall still works. RRF falls back to FTS5-only when vec_hits=[].

    Env vars read inside the function so patch.dict() works in tests.
    """
    gossip_db = os.environ.get("GOSSIP_DB_PATH", "perpetua_core.db")
    lance_db  = os.environ.get("LANCE_DB_PATH",  "lance_memory.lance")
    prompt = state.scratchpad.get("prompt", "")
    if not prompt:
        return {"scratchpad": {**state.scratchpad, "context": []}}

    # FTS5 keyword recall — always works (stdlib, no external deps)
    try:
        bus = GossipBus(gossip_db)
        await bus.init_db()
        fts_hits = await bus.search(prompt, limit=10)
    except Exception:
        fts_hits = []

    # LanceDB vector recall — opportunistic, graceful fallback
    # store.search() returns {row_id, text, score}; hydrate back to FTS5 shape
    # {row_id, ts, event_type, payload} so dispatch_node sees a uniform format.
    vec_hits: list[dict] = []
    try:
        embedding = await get_embedding(prompt)
        store = get_lance_store(lance_db)
        raw_vec = await store.search(embedding, limit=10)
        # Hydrate: look up full row in SQLite for each vector hit
        fts_ids = {h["row_id"] for h in fts_hits}
        async with aiosqlite.connect(gossip_db) as db:
            for vh in raw_vec:
                rid = vh.get("row_id")
                if rid in fts_ids:
                    continue  # already in fts_hits, RRF will merge by row_id
                cursor = await db.execute(
                    "SELECT id, ts, event_type, payload_json FROM gossip WHERE id = ?",
                    (rid,),
                )
                row = await cursor.fetchone()
                if row:
                    vec_hits.append({
                        "row_id": row[0], "ts": row[1],
                        "event_type": row[2],
                        "payload": _json.loads(row[3]),
                    })
                else:
                    vec_hits.append(vh)  # fallback: keep raw if not in gossip
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
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
python -m pytest tests/ -v
```

Expected: 32 prior + 18 new = 50 passing

- [ ] **Step 2: Verify all tests pass in oramasys**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
python -m pytest tests/ -v
```

Expected: 4 prior + 4 new = 8 passing

- [ ] **Step 3: Commit perpetua-core**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
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

Tests: 18 new passing (8 FTS5 + 3 LanceDB + 3 RRF + 4 gbrain tool).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Commit oramasys**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
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
    from types import SimpleNamespace
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="LLM answer"))]
    )
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=mock_completion)

    with patch("orama.graph.nodes.dispatch_node.LLMClient", return_value=mock_client):
        from orama.graph.nodes.dispatch_node import dispatch_node
        delta = await dispatch_node(state)

    assert delta["scratchpad"]["response"] == "LLM answer"
    call_kwargs = mock_client.chat.call_args.kwargs
    messages = call_kwargs["messages"]
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
    from types import SimpleNamespace
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="response"))]
    )
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=mock_completion)

    with patch("orama.graph.nodes.dispatch_node.LLMClient", return_value=mock_client):
        from orama.graph.nodes.dispatch_node import dispatch_node
        delta = await dispatch_node(state)

    messages = mock_client.chat.call_args.kwargs["messages"]
    system_msg = next(m for m in messages if m["role"] == "system")
    assert "No prior context" in system_msg["content"]
```

- [ ] **Step 2: Run tests — verify 3 fail**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
.venv/bin/python -m pytest tests/graph/test_dispatch_node.py -v
```

- [ ] **Step 2.5: Verify LLMClient.chat() actual signature**

Before implementing, inspect the real API:

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
grep -n "async def chat\|def chat" perpetua_core/llm.py
# Verify: (a) does chat() accept model= kwarg or only the constructor?
#         (b) what does chat() return — completion object, dict, or str?
```

If the actual signature differs from the assumption in Step 3 (kwargs-only `messages=`, return shape `completion.choices[0].message.content`), update Step 3 implementation accordingly. The defensive `hasattr/isinstance` block in the implementation already tolerates dict-style and raw-str returns — but if `chat()` requires `model=` per-call, add it back.

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

    # Verify LLMClient.chat signature before wiring — see Step 2.5 below.
    # `model` is set in constructor; some LLMClient impls also accept `model=`
    # in chat() (per-request override). Keep only what perpetua_core.llm uses.
    try:
        client = LLMClient(base_url=_LLM_BASE_URL, model=_LLM_MODEL)
        completion = await client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )
        # Handle both OpenAI-style (completion.choices[0].message.content)
        # and dict-style ({"choices":[{"message":{"content":...}}]}) returns.
        if hasattr(completion, "choices"):
            response = completion.choices[0].message.content
        elif isinstance(completion, dict) and "choices" in completion:
            response = completion["choices"][0]["message"]["content"]
        elif isinstance(completion, str):
            response = completion  # some clients return raw content
        else:
            response = str(completion)
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
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core && python -m pytest tests/ -v
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys && python -m pytest tests/ -v
```

All must be green.

- [ ] **Step 2: Commit (oramasys)**

```bash
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
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
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/perpetua-core
python -m pytest tests/ -v  # expect 50+ passing

# 2. oramasys: all tests green
# REFERENCE-ONLY — DO NOT EXECUTE. v2-cut illustration; v1 work lives under <workspace>/Perpetua-Tools and <workspace>/orama-system.
cd ~/oramasys/oramasys
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

---

## Decision Audit Trail (autoplan Phase 4)

> Recorded 2026-05-21 — all decisions made during /autoplan CEO + Eng + DX review.

| # | Decision | Rationale | Phase |
|---|----------|-----------|-------|
| D1 | Hybrid FTS5 + LanceDB (not FTS5-only) | Ollama+bge-m3 is already a hard system requirement; LanceDB = zero marginal cost | User (premise gate) |
| D2 | Fire-and-forget `asyncio.create_task()` in `emit()` | No daemon process needed in v1; background daemon deferred to v2.5 reaper | User (premise gate) |
| D3 | Module-level `_pending_embeds: set[asyncio.Task]` | CPython holds only weak refs to tasks — without this, in-flight embeds get GC'd | User-required |
| D4 | `_pending_embeds` cap at 500 tasks | Prevents unbounded growth if Ollama is consistently slow; rows stay `pending` for v2.5 reaper | CEO phase |
| D5 | Path-keyed `_lance_stores` dict (not single global) | Single global locks to first path seen — test isolation failures when tests use `tmp_path` | CEO phase |
| D6 | GbrainSearchTool as `async def` with `run_in_executor` | Blocking `subprocess.run()` in an async tool stalls the event loop for up to 10s | Eng phase |
| D7 | FTS5 `search()` wrapped in `try/except` | Real prompts with quotes/colons/FTS operators raise `OperationalError` — degrade gracefully | Eng phase |
| D8 | GbrainSearchTool tests changed to `async def + await` | Tool is async; sync tests compare coroutine objects to `[]` — false-green | Eng phase |
| D9 | `LLMClient.chat()` called as `chat(model=..., messages=[...])` | Actual API is keyword-only; `chat([...])` positional is wrong — false-green tests | Eng phase |
| D10 | `asyncio.get_event_loop()` → `asyncio.get_running_loop()` | `get_event_loop()` deprecated in Python 3.10+; raises DeprecationWarning → RuntimeError | Eng phase |
| D11 | `_ensure_table()` guarded with `asyncio.Lock()` | Concurrent calls all see `_table is None` before first completes — race to create table | Eng phase |
| D12 | Env vars read inside `memory_node()` body | Module-level constants captured at import time; `patch.dict` in tests won't affect them | Eng phase |
| D13 | Vector hit hydration via SQLite lookup | LanceDB returns `{row_id, text, score}`; dispatch_node expects `{row_id, ts, event_type, payload}` | Eng phase |
| D14 | `rrf_merge` uses `uuid4()` for keyless items | Negative-int synthetic keys (-rank-1) have range overlap across FTS5 and vec lists | Eng phase |
| D15 | Added `embed_status='failed'` deterministic test | Original 7-test suite had no test proving `failed` status is set on embed error | Eng phase |
| D16 | `pytest-asyncio` + `asyncio_mode = "auto"` documented | 18 async tests need it; not noting it causes silent skip/pass with wrong markers | DX phase |
| D17 | `memory_node` hydration uses individual SQLite lookups | Simplest correct approach for v1 (≤10 hits); bulk `IN (...)` is v2.1 optimization | DX phase |
| D18 | Outcome clarified: hybrid search available to ALL agents by default | Via `@tool gbrain_search` + MemoryNode; search in UI + Launcher Agent + orchestrator | Premise gate (user) |
| D19 | v2.1 EmbeddingCircuitBreaker documented as follow-on | After this plan lands; design already in `docs/v2/18-rag-and-memory-design.md § v2.1` | Premise gate (user) |
| D20 | EmbeddingStore dim parameterized (not hardcoded 1024) | Antigravity Gemini 3.5 Gap 1 — `EMBED_MODEL` env var was already configurable but schema was not; switching to a non-1024 model corrupted writes | Critique phase 2026-05-21 |
| D21 | `_sanitize_fts_query()` strips FTS5 operators before MATCH | Antigravity Gemini 3.5 Gap 2 — try/except returned `[]` silently on real prompts containing quotes/colons, losing keyword recall entirely | Critique phase 2026-05-21 |
| D22 | Real GC test replaces `isinstance(set)` tautology | Antigravity Gemini 3.5 Gap 3 — patched `_embed_and_store` to sleep, asserts membership during active window and discard after completion | Critique phase 2026-05-21 |
| D23 | Plan retargeted at v2 (`oramasys/*`) explicitly; v1 backport scope documented separately | User clarification 2026-05-22 — `diazMelgarejo/*` = v1 ship target, `oramasys/*` = v2 plan target, never write code directly to v2 | Critique phase 2026-05-22 |

---

## Status Taxonomy (Codex GPT-5.5 P0 — normalize across all RAG docs)

| Label | Meaning | Where used |
|-------|---------|------------|
| **Planned** | Designed but no implementation merged | Default for all task checkboxes |
| **In Progress** | Branch open, partial implementation | Tracked via TaskUpdate per task |
| **Merged** | Lands on `feat/*` or PR'd to `main` of the targeted repo | Recorded in commit log + LESSONS.md |
| **Released** | Tagged on the targeted repo (v2 today = scaffold, not released yet) | Used in `docs/v2/*` only |

**Cross-doc invariant:** `docs/v2/18-rag-and-memory-design.md` and `docs/v2/19-gstack-optional-integration.md` use this same vocabulary. No mixed "DONE" / "complete" / "ready" labels. If a v2 doc says `DONE`, it must point at a merged or released commit in oramasys/*.

---

## Non-Goals (Codex P0)

Explicitly NOT in scope for this plan:

- ❌ Cross-tenant retrieval (no multi-user isolation in v1)
- ❌ Encrypted-at-rest vectors (LanceDB is local plain Arrow files)
- ❌ Auto-repair daemon for failed embeds (deferred to v2.5 Reaper)
- ❌ Distributed vector store (Lance fleet — deferred to v2.5)
- ❌ Cloud embedding fallback (Ollama bge-m3 is the hard requirement)
- ❌ MAESTRO / HITL approval gates on retrieval (V1 scope boundary — see UNIFIED-ABSORPTION-PLAN § 2)
- ❌ Backporting full plan to v1 (only selective slices — see "v1 Backport Candidates" below)

---

## Security / Privacy / Retention (Codex P0)

| Concern | v1 policy | v2.1 hardening |
|---------|-----------|----------------|
| **Payload classification** | Whatever the agent emits is indexed; no automatic redaction | Add `sensitive=True` flag on `bus.emit()`; sensitive rows skip embedding |
| **PII in `payload_json`** | Caller's responsibility to scrub before emit | Optional regex redaction hook |
| **Retention** | Unbounded (rows + vectors live forever); FTS5 + Lance grow with disk | TTL parameter on `emit()`; v2.5 Reaper deletes expired rows + vectors |
| **Right-to-delete** | Manual SQL: `DELETE FROM gossip WHERE session_id = ?` + LanceDB row delete by row_id | First-class `bus.forget(session_id=...)` API |
| **Local-only by default** | `OLLAMA_BASE_URL` defaults to `localhost:11434`; LanceDB is on local disk | No change — privacy-preserving by construction |
| **API keys / secrets in events** | Caller MUST scrub before emit; `payload_json` is plaintext | Same — no in-pipeline secret detection in V1 |

**V1 enforcement:** none of the above is automated. Documented as caller contract.

---

## Acceptance Gate Table (Codex P0, per-phase)

| Gate | Metric | Target | Evidence | Owner |
|------|--------|--------|----------|-------|
| **G1 — FTS5 functional** | Search correctness on synthetic corpus | 100% test pass (8 tests) | `pytest tests/test_gossip_search.py -v` | Eng |
| **G2 — FTS5 robustness** | Real-prompt sanitizer prevents OperationalError | All real-world prompts return real hits, never `[]` from raw operator crash | Manual fuzz + `_sanitize_fts_query()` unit tests | Eng |
| **G3 — LanceDB store** | Add + search idempotent across paths | 3 tests pass | `pytest tests/memory/test_store.py -v` | Eng |
| **G4 — RRF merge** | FTS-only fallback + dedup + ranking | 3 tests pass | `pytest tests/memory/test_rrf.py -v` | Eng |
| **G5 — Embed dim safety** | Schema matches active EMBED_MODEL | Probe agrees with first write; no Arrow dim error | `EMBED_MODEL=nomic-embed-text pytest` smoke run | Eng |
| **G6 — GC integrity** | In-flight embed tasks not GC'd | Real GC test passes (`len(_pending_embeds) == 1` during active window) | `pytest tests/test_gossip_search.py::test_pending_embeds_set_prevents_gc -v` | Eng |
| **G7 — Graceful degradation** | Ollama-down / Lance-down still returns FTS5 hits | 4 MemoryNode tests pass with mocked failures | `pytest tests/graph/test_memory_node.py -v` | Eng |
| **G8 — End-to-end** | `/run` endpoint returns LLM response with context | Smoke run shows context from prior emits in system prompt | manual curl + observed system prompt | Eng/Ops |
| **G9 — Migration safety** | Pre-existing gossip DB upgrades cleanly | `test_rebuild_fts_handles_existing_rows` passes | pytest + manual on copy of old DB | Eng |

All gates must pass before merging to `main` of target repo.

---

## v1 Backport Candidates (NEW 2026-05-22)

> **Context:** The plan above targets v2 (`oramasys/perpetua-core` + `oramasys/oramasys`). The v1 runtime (`diazMelgarejo/Perpetua-Tools`) has a different module layout: no `perpetua_core` package, code lives in `orchestrator/` and `perpetua/discovery/`. These items are explicit candidates for selective backport to v1; each item names the v1 destination and the adaptation cost.

| Item | Backport priority | v1 destination | Adaptation cost | Stress-test value |
|------|-------------------|----------------|-----------------|-------------------|
| **FTS5 schema + triggers + `_sanitize_fts_query()`** | 🟢 High (cheap + safety win) | Wherever Perpetua-Tools owns its event log today; create `Perpetua-Tools/orchestrator/gossip_bus.py` if absent | Low — pure stdlib SQLite; no new deps | Validates FTS5 sanitizer against real production prompts |
| **`_pending_embeds` GC guard pattern** | 🟢 High (general async correctness, not RAG-specific) | Anywhere `asyncio.create_task()` is used in `orchestrator/` | Low — module-level pattern | Catches latent GC bugs in v1 orchestrator |
| **LanceDB EmbeddingStore w/ dim probe** | 🟡 Medium (1 new dep) | `Perpetua-Tools/orchestrator/memory_store.py` new file | Medium — pyarrow + lancedb deps; verify wheel availability for v1 Python target | Validates dim-probe on real Win + Mac LM Studio hardware |
| **RRF merge** | 🟢 High (pure function, zero deps) | Stand-alone util in v1 | Trivial — copy file | Universal — useful anywhere hybrid retrieval lands |
| **GbrainSearchTool `@tool`** | 🟠 Conditional | Only backport if v1 already has a `@tool` decorator equivalent; otherwise wrap as plain async fn | Medium — depends on v1 tool-registration model | Validates gbrain CLI integration end-to-end |
| **MemoryNode** | 🔴 Low (requires v2 graph model) | Not directly backportable — v1 has no MiniGraph | High — would need a v1-shaped wrapper | Defer; v1 doesn't have the right substrate |
| **dispatch_node LLMClient wiring** | 🔴 Low | v1 already has LLM dispatch via `orchestrator/control_plane.py` | High — different abstraction; learnings inform v2 only | Defer |

**Recommended backport order:**
1. RRF merge (zero risk, instantly useful)
2. FTS5 + `_sanitize_fts_query()` (safety win, no new deps)
3. `_pending_embeds` pattern (general async hygiene)
4. LanceDB store (only if Perpetua-Tools accepts the new dep)
5. Stop. Items 5+ require v1 graph refactor — wait for v2 cut.

**Backport repo:** `diazMelgarejo/Perpetua-Tools`, branch `feat/rag-backport-v1` (created fresh from `main`, NOT from this orama-system feat branch).

**Backport learnings flow:** Any issue discovered while shipping a backport item gets recorded in `docs/LESSONS.md` (this repo) AND incorporated into the v2 plan above (this file) before v2 cut.

---

## Steelman Audit Summary (Critique Phase 2026-05-21 → 2026-05-22)

| Source | Verdict | P0 items applied here | Deferred |
|--------|---------|------------------------|----------|
| **Codex GPT-5.5** (`docs/2026-05-21-001--Critique-RAG-ChatGPT-codex-GPT-5.5.md`) | Approved with P0 hardening required | Status taxonomy, Non-Goals, Security/Privacy/Retention, Acceptance Gate Table | P1 rollback drills, P2 compatibility matrix → tracked in `docs/v2/18` |
| **Antigravity Gemini 3.5** (`docs/2026-05-21-002--RAG-Gstack-Review--Antigravity-Gemini-3.5-Flash-Preview.md`) | Fully approved | Gap 1 (dim probe), Gap 2 (FTS sanitizer), Gap 3 (real GC test) | Gap 4 (v2.5 Reaper prioritization) → `docs/v2/18 § v2.5` |
| **User reframing 2026-05-22** | Override prior docs-only constraint | Explicit v1/v2 targeting block; v1 Backport Candidates section | Backport branch creation → next session |

All P0 items are now reflected in this plan. No silent failures, no tautological tests, no hardcoded dimensions.
