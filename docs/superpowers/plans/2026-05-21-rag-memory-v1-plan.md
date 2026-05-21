# RAG Memory Pipeline v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add FTS5 keyword recall to GossipBus, inject context into oramasys graph via ContextNode, wire LLMClient into dispatch_node. Zero new Python dependencies.

**Architecture:** Two commits on `feat/rag-gstack-optional-v1`. Commit 1 = retrieval layer (perpetua-core + ContextNode). Commit 2 = generation layer (dispatch_node LLMClient wiring).

**Tech Stack:** Python 3.11+, aiosqlite, SQLite FTS5 (stdlib), perpetua-core kernel, oramasys FastAPI graph, existing `perpetua_core.llm.LLMClient`

**Repos:** `/Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core` and `/Users/lawrencecyremelgarejo/Documents/oramasys/oramasys`

**Run tests with:** `python -m pytest tests/ -v` (in each repo root)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `perpetua_core/gossip.py` | Modify | Add FTS5 schema + triggers + `search()` + `_rebuild_fts()` |
| `tests/test_gossip_search.py` | Create | 5 FTS5 tests |
| `perpetua_core/graph/tools/gbrain_search.py` | Create | `@tool GbrainSearch` subprocess wrapper |
| `tests/graph/tools/test_gbrain_search.py` | Create | 2 tests (graceful degradation) |
| `orama/graph/nodes/context_node.py` | Create | ContextNode: search + scratchpad injection |
| `orama/graph/nodes/__init__.py` | Create/modify | Export context_node |
| `orama/graph/perpetua_graph.py` | Modify | Wire ContextNode as node 0 |
| `tests/graph/test_context_node.py` | Create | 2 tests |
| `orama/graph/nodes/dispatch_node.py` | Modify | Wire LLMClient with context system prompt |
| `tests/graph/test_dispatch_node.py` | Create | 3 tests |

---

## COMMIT 1: Retrieval Layer

### Task 1 — GossipBus FTS5 schema + triggers

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
    # Manually insert rows without FTS (simulate pre-FTS database)
    import aiosqlite
    async with aiosqlite.connect(db) as conn:
        await conn.execute(
            "CREATE TABLE gossip (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ts REAL NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL)"
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
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/test_gossip_search.py -v
```

Expected: 5 failures (search not implemented yet)

- [ ] **Step 3: Implement FTS5 in gossip.py**

Add after `CREATE_TABLE`:

```python
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

Replace `init_db()`:

```python
async def init_db(self) -> None:
    async with aiosqlite.connect(self._db_path) as db:
        await db.execute(CREATE_TABLE)
        await db.execute(_CREATE_FTS)
        await db.execute(_CREATE_FTS_AI)
        await db.execute(_CREATE_FTS_AD)
        await db.commit()
        # Populate FTS from any existing rows that predate this migration
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

Add `search()` method:

```python
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    event_type: Optional[str] = None,
) -> list[dict]:
    """BM25 full-text search over GossipBus event history."""
    if not query.strip():
        return []
    async with aiosqlite.connect(self._db_path) as db:
        if event_type:
            cursor = await db.execute(
                """SELECT g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ? AND g.event_type = ?
                   ORDER BY rank LIMIT ?""",
                (query, event_type, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT g.ts, g.event_type, g.payload_json
                   FROM gossip_fts f
                   JOIN gossip g ON g.id = f.rowid
                   WHERE gossip_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        rows = await cursor.fetchall()
    return [
        {"ts": r[0], "event_type": r[1], "payload": json.loads(r[2])}
        for r in rows
    ]
```

Add `Optional` to imports: `from typing import Literal, AsyncIterator, Optional`

- [ ] **Step 4: Run tests — verify 5 pass**

```bash
python -m pytest tests/test_gossip_search.py -v
```

Expected: 5 passed

- [ ] **Step 5: Run full perpetua-core suite — verify all 32+ still pass**

```bash
python -m pytest tests/ -v
```

Expected: all prior tests pass + 5 new

---

### Task 2 — GbrainSearchTool @tool (perpetua-core)

**Files:** `perpetua_core/graph/tools/gbrain_search.py` (create), `tests/graph/tools/test_gbrain_search.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/tools/test_gbrain_search.py`:

```python
import pytest
from unittest.mock import patch
from perpetua_core.graph.tools.gbrain_search import gbrain_search


def test_gbrain_search_returns_empty_when_cli_absent():
    """FileNotFoundError (gbrain not on PATH) → empty list, no raise."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_returns_empty_on_timeout():
    """TimeoutExpired → empty list, no raise."""
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gbrain", timeout=10)):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_returns_empty_on_nonzero_exit():
    """returncode != 0 → empty list."""
    import subprocess
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=fake):
        result = gbrain_search(query="anything")
    assert result == []


def test_gbrain_search_parses_json_output():
    """Valid JSON stdout → parsed list."""
    import subprocess, json
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
import json
import subprocess
from perpetua_core.graph.plugins.tool import tool


@tool
def gbrain_search(query: str, limit: int = 5) -> list[dict]:
    """Search gbrain semantic memory for relevant past knowledge.

    Returns an empty list if gbrain CLI is unavailable — never raises.
    """
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
```

- [ ] **Step 5: Run 4 tests — verify they pass**

```bash
python -m pytest tests/graph/tools/test_gbrain_search.py -v
```

- [ ] **Step 6: Run full suite**

```bash
python -m pytest tests/ -v
```

---

### Task 3 — ContextNode in oramasys

**Files:** `orama/graph/nodes/context_node.py` (create), `orama/graph/perpetua_graph.py` (modify)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/test_context_node.py` in the oramasys repo:

```python
import asyncio
import pytest
import tempfile
import os
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_context_node_empty_db_returns_empty_scratchpad(tmp_path):
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()

    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db}):
        from orama.graph.nodes.context_node import context_node
        state = PerpetuaState(session_id="t1", scratchpad={"prompt": "hello"})
        delta = await context_node(state)

    # No events in db → context is empty list
    assert delta.get("scratchpad", {}).get("context") == []


@pytest.mark.asyncio
async def test_context_node_injects_relevant_hits(tmp_path):
    db = str(tmp_path / "test.db")
    bus = GossipBus(db)
    await bus.init_db()
    await bus.emit("dispatch", {"prompt": "summarize the quarterly report"})

    with patch.dict(os.environ, {"GOSSIP_DB_PATH": db}):
        from orama.graph.nodes.context_node import context_node
        state = PerpetuaState(session_id="t2", scratchpad={"prompt": "quarterly report"})
        delta = await context_node(state)

    hits = delta.get("scratchpad", {}).get("context", [])
    assert len(hits) >= 1
    assert any("quarterly" in str(h) for h in hits)
```

- [ ] **Step 2: Run tests — verify 2 fail**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/graph/test_context_node.py -v
```

- [ ] **Step 3: Create `orama/graph/nodes/__init__.py`** (empty or add exports)

- [ ] **Step 4: Create `orama/graph/nodes/context_node.py`**

```python
"""ContextNode — first graph node. Retrieves relevant GossipBus history."""
import os
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus

_GOSSIP_DB = os.environ.get("GOSSIP_DB_PATH", "perpetua_core.db")


async def context_node(state: PerpetuaState) -> dict:
    """Search GossipBus for events relevant to the current prompt.

    Injects top-k hits into scratchpad["context"]. Returns empty list
    if db is absent or query is empty — never raises.
    """
    prompt = state.scratchpad.get("prompt", "")
    if not prompt:
        return {"scratchpad": {**state.scratchpad, "context": []}}
    try:
        bus = GossipBus(_GOSSIP_DB)
        await bus.init_db()
        hits = await bus.search(prompt, limit=5)
    except Exception:
        hits = []
    return {"scratchpad": {**state.scratchpad, "context": hits}}
```

- [ ] **Step 5: Wire ContextNode into `orama/graph/perpetua_graph.py`**

Find the existing graph construction (currently 3 nodes). Add context node:

```python
from orama.graph.nodes.context_node import context_node

graph = (
    MiniGraph()
    .add_node("context",  context_node)
    .add_node("route",    route_node)
    .add_node("dispatch", dispatch_node)
    .add_node("respond",  respond_node)
    .add_edge(START,      "context")
    .add_edge("context",  "route")
    .add_edge("route",    "dispatch")
    .add_edge("dispatch", "respond")
    .add_edge("respond",  END)
)
```

- [ ] **Step 6: Run tests — verify 2 pass, prior 4 still pass**

```bash
python -m pytest tests/ -v
```

---

### Task 4 — Commit 1

- [ ] **Step 1: Verify all tests pass in perpetua-core**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/ -v
```

Expected: 32 prior + 9 new = 41 passing

- [ ] **Step 2: Verify all tests pass in oramasys**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/ -v
```

Expected: 4 prior + 2 new = 6 passing

- [ ] **Step 3: Commit (perpetua-core first)**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
git add perpetua_core/gossip.py \
        perpetua_core/graph/tools/__init__.py \
        perpetua_core/graph/tools/gbrain_search.py \
        tests/test_gossip_search.py \
        tests/graph/tools/test_gbrain_search.py
git commit -m "$(cat <<'EOF'
feat(rag): FTS5 GossipBus.search() + GbrainSearchTool

Add SQLite FTS5 virtual table + BM25 triggers to GossipBus.
Add search(query, limit, event_type) method — zero new deps.
Add GbrainSearchTool @tool — graceful subprocess wrapper for gbrain CLI,
returns [] when CLI absent (never raises).
Add idempotent _rebuild_fts migration for existing deployments.

Tests: 9 new passing (5 gossip FTS5 + 4 gbrain tool).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Commit (oramasys)**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
git add orama/graph/nodes/__init__.py \
        orama/graph/nodes/context_node.py \
        orama/graph/perpetua_graph.py \
        tests/graph/test_context_node.py
git commit -m "$(cat <<'EOF'
feat(graph): ContextNode injects GossipBus recall as scratchpad context

Add ContextNode as node 0 in perpetua_graph. Searches FTS5 GossipBus
for events relevant to current prompt. Injects top-5 hits into
scratchpad["context"] before route + dispatch. Graceful: empty list
if db absent or query empty.

Tests: +2 (6 total, all passing).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## COMMIT 2: Generation Layer

### Task 5 — Wire LLMClient into dispatch_node

**Files:** `orama/graph/nodes/dispatch_node.py` (modify), `tests/graph/test_dispatch_node.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/graph/test_dispatch_node.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
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
    # System prompt must contain "prior task" from context
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
    """Dispatch to LLMClient with GossipBus context in system prompt."""
    context_hits = state.scratchpad.get("context", [])
    if context_hits:
        context_str = "\n".join(
            f"[{h['event_type']}] {json.dumps(h['payload'])}"
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

Expected: 6 prior + 3 new = 9 passing

---

### Task 6 — Commit 2

- [ ] **Step 1: Final test run across both repos**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core && python -m pytest tests/ -v
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys && python -m pytest tests/ -v
```

All must be green before committing.

- [ ] **Step 2: Commit (oramasys)**

```bash
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
git add orama/graph/nodes/dispatch_node.py \
        tests/graph/test_dispatch_node.py
git commit -m "$(cat <<'EOF'
feat(dispatch): wire LLMClient into dispatch_node with context injection

Replace echo stub with real LLMClient.chat() call. System prompt
includes top-5 GossipBus context hits from ContextNode. Graceful
fallback on LLM error — stores error string in scratchpad["response"]
rather than propagating. LLM_BASE_URL and LLM_MODEL via env vars.

Tests: +3 (9 total, all passing).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Verification After Both Commits

```bash
# 1. perpetua-core: all tests green
cd /Users/lawrencecyremelgarejo/Documents/oramasys/perpetua-core
python -m pytest tests/ -v  # expect 41+ passing

# 2. oramasys: all tests green
cd /Users/lawrencecyremelgarejo/Documents/oramasys/oramasys
python -m pytest tests/ -v  # expect 9+ passing

# 3. Manual smoke test (requires LM Studio running at localhost:1234)
curl -s http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What did we work on last time?"}' | jq .

# Expected: output contains LLM response with context from GossipBus history
# (If LM Studio not running, response will be "[dispatch error: ...]" — graceful)
```
