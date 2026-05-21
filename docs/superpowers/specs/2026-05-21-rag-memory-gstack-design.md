# Design: Minimal RAG Memory Pipeline + gstack Optional Submodule

**Date:** 2026-05-21
**Status:** Approved for planning — implementation pending manual review
**Branch:** `feat/rag-gstack-optional-v1`
**Repos in scope (v1):** `diazMelgarejo/orama-system`, `diazMelgarejo/Perpetua-Tools`
**Canonical v2 repos (plan only):** `oramasys/perpetua-core`, `oramasys/oramasys`

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

**v1 (this week):** Zero new Python dependencies.
- FTS5: bundled in Python's `sqlite3` module (available since Python 3.4)
- gbrain @tool: subprocess call to existing `gbrain` CLI (already on PATH for dev machines)
- LLMClient: already implemented in `perpetua_core/llm.py`
- gstack submodule: `git submodule` only — no pip installs

**v2.1 (future):** LanceDB replaces FTS5 for vector semantic recall.
**v2.5 (future):** DuckDB for fleet analytics over GossipBus history.

---

## Architecture Overview

```
perpetua-core (kernel changes)           oramasys (graph changes)
─────────────────────────────           ──────────────────────────
GossipBus                                ContextNode  (NEW, node 0)
  + FTS5 virtual table (NEW)              ├── gossip.search(prompt, k=5)
  + search(query, limit) (NEW)            └── scratchpad["context"] = top-k hits
  + _rebuild_fts() migration helper             ↓
                                         route_node  (existing, node 1)
perpetua_core/graph/tools/               dispatch_node  (WIRED, node 2)
  gbrain_search.py (NEW)                  ├── LLMClient.chat(messages=[
    @tool GbrainSearch                    │     system: context + policy,
    subprocess: gbrain query              │     user: state.prompt
    graceful: empty list if CLI absent    │   ])
                                          └── scratchpad["response"] = LLM output
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
      → ContextNode
          gossip.search(state.prompt, limit=5)
          → FTS5 BM25 query on payload_json
          → top-k past events injected into scratchpad["context"]
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

## Sub-Project 1: GossipBus FTS5 Search

**File:** `perpetua_core/gossip.py` (modify)
**Tests:** `tests/test_gossip_search.py` (create)

### Schema changes to `init_db()`

```python
CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS gossip_fts
USING fts5(event_type, payload_json, content='gossip', content_rowid='id')
"""

CREATE_FTS_AI = """
CREATE TRIGGER IF NOT EXISTS gossip_fts_ai
AFTER INSERT ON gossip BEGIN
  INSERT INTO gossip_fts(rowid, event_type, payload_json)
  VALUES (new.id, new.event_type, new.payload_json);
END
"""

CREATE_FTS_AD = """
CREATE TRIGGER IF NOT EXISTS gossip_fts_ad
AFTER DELETE ON gossip BEGIN
  INSERT INTO gossip_fts(gossip_fts, rowid, event_type, payload_json)
  VALUES ('delete', old.id, old.event_type, old.payload_json);
END
"""
```

### New method: `search()`

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

### Migration helper: `_rebuild_fts()`

For databases created before FTS5 was added (existing deployments):

```python
async def _rebuild_fts(self) -> int:
    """Populate gossip_fts from existing gossip rows. Returns rows rebuilt."""
    async with aiosqlite.connect(self._db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM gossip")
        (total,) = await cursor.fetchone()
        if total == 0:
            return 0
        await db.execute(
            "INSERT INTO gossip_fts(rowid, event_type, payload_json) "
            "SELECT id, event_type, payload_json FROM gossip"
        )
        await db.commit()
    return total
```

Called once at `init_db()` if the fts table was just created with existing rows.

### Test cases

1. `test_search_returns_empty_for_no_match` — FTS5 miss returns `[]`
2. `test_search_finds_exact_payload_keyword` — emit an event, search for a word in its payload
3. `test_search_filters_by_event_type` — emit dispatch + error events, filter to error only
4. `test_search_ranking_by_relevance` — multiple emits, most-relevant appears first
5. `test_search_empty_query_returns_empty` — guard against FTS5 empty-query exception

---

## Sub-Project 2: ContextNode + gbrain @tool

### ContextNode (`orama/graph/nodes/context_node.py`, create)

```python
from perpetua_core.state import PerpetuaState
from perpetua_core.gossip import GossipBus
import os

_GOSSIP_DB = os.environ.get("GOSSIP_DB_PATH", "perpetua_core.db")

async def context_node(state: PerpetuaState) -> dict:
    """Retrieve relevant past GossipBus events and inject into scratchpad."""
    bus = GossipBus(_GOSSIP_DB)
    prompt = state.scratchpad.get("prompt", "") or state.prompt if hasattr(state, "prompt") else ""
    if not prompt:
        return {}
    hits = await bus.search(prompt, limit=5)
    return {"scratchpad": {**state.scratchpad, "context": hits}}
```

### GbrainSearchTool (`perpetua_core/graph/tools/gbrain_search.py`, create)

```python
import subprocess
import json
from perpetua_core.graph.plugins.tool import tool

@tool
def gbrain_search(query: str, limit: int = 5) -> list[dict]:
    """Search gbrain semantic memory for relevant past knowledge.

    Returns empty list if gbrain CLI is not installed (graceful degradation).
    Never raises — failure is treated as no results.
    """
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
```

### Wire ContextNode into graph (`orama/graph/perpetua_graph.py`, modify)

Add `context_node` as node 0 before `route_node`:

```python
from orama.graph.nodes.context_node import context_node

graph = (
    MiniGraph()
    .add_node("context",  context_node)
    .add_node("route",    route_node)
    .add_node("dispatch", dispatch_node)
    .add_node("respond",  respond_node)
    .add_edge(START,       "context")
    .add_edge("context",  "route")
    .add_edge("route",    "dispatch")
    .add_edge("dispatch", "respond")
    .add_edge("respond",  END)
)
```

### Test cases

1. `test_context_node_empty_db_returns_empty_scratchpad`
2. `test_context_node_injects_relevant_hits_into_scratchpad`
3. `test_gbrain_search_returns_empty_when_cli_absent`
4. `test_gbrain_search_returns_empty_on_timeout`

---

## Sub-Project 3: LLMClient Wiring in dispatch_node

**File:** `orama/graph/nodes/dispatch_node.py` (modify — currently echo stub)
**Tests:** `tests/graph/test_dispatch_node.py` (create)

### Implementation

```python
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
    context_hits = state.scratchpad.get("context", [])
    context_str = "\n".join(
        f"[{h['event_type']}] {json.dumps(h['payload'])}"
        for h in context_hits[:5]
    ) if context_hits else "No prior context available."

    system = _SYSTEM_TEMPLATE.format(
        context=context_str,
        tier=getattr(state, "target_tier", "unknown"),
        task_type=getattr(state, "task_type", ""),
    )
    prompt = state.scratchpad.get("prompt", "")

    client = LLMClient(base_url=_LLM_BASE_URL, model=_LLM_MODEL)
    response = await client.chat([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ])

    return {"scratchpad": {**state.scratchpad, "response": response}}
```

### Fallback behavior

If `LLMClient` raises (model unreachable, timeout), fall back to returning a structured
error in `scratchpad["response"]` rather than propagating — preserving the graph
completion contract. The error is also emitted to GossipBus as an `"error"` event.

### Test cases

1. `test_dispatch_node_calls_llm_with_context` — mock LLMClient, verify system prompt includes context
2. `test_dispatch_node_falls_back_on_llm_error` — raise in LLMClient, verify no exception propagates
3. `test_dispatch_node_empty_context_uses_default_string`

---

## Sub-Project 4: gstack Optional Git Submodule

**Scope:** `diazMelgarejo/orama-system` only (not oramasys/*)
**Files to create/modify:**

| File | Action | Purpose |
|------|--------|---------|
| `.gitmodules` | Create/append | Register `tools/gstack` submodule |
| `install-gstack.sh` | Create | Manual opt-in install script |
| `install.sh` | Modify | Add idempotent gstack detection (skip if found) |
| `portal_server.py` | Modify | Add `GET /api/tools/status` endpoint |
| `scripts/tool_status.py` | Create | Detection logic (shared by install.sh + portal) |
| `docs/v2/19-gstack-optional-integration.md` | Create | v2 plan |

### Detection order (idempotent, fail-safe)

```python
def detect_gstack() -> dict:
    """Returns gstack/gbrain detection state. Never raises."""
    import shutil, subprocess, pathlib

    results = {
        "skill_installed": pathlib.Path("~/.claude/skills/gstack").expanduser().exists(),
        "gbrain_on_path":  shutil.which("gbrain") is not None,
        "submodule_present": pathlib.Path("tools/gstack").exists(),
        "version": None,
        "source": None,
    }

    if results["gbrain_on_path"]:
        try:
            v = subprocess.run(["gbrain", "--version"], capture_output=True, text=True, timeout=5)
            results["version"] = v.stdout.strip() if v.returncode == 0 else None
            results["source"] = "path"
        except Exception:
            pass
    elif results["skill_installed"]:
        results["source"] = "skill"
    elif results["submodule_present"]:
        results["source"] = "submodule"

    results["available"] = any([
        results["gbrain_on_path"],
        results["skill_installed"],
        results["submodule_present"],
    ])
    return results
```

### `install-gstack.sh` (user-invokable, idempotent)

```bash
#!/usr/bin/env bash
set -e

# Idempotent gstack install. Safe to run multiple times.
# Skips gracefully if gbrain is already on PATH.

if command -v gbrain &>/dev/null; then
  echo "✓ gbrain already available at $(which gbrain). Nothing to install."
  exit 0
fi

echo "Installing gstack submodule..."
git submodule add https://github.com/garrytan/gstack tools/gstack 2>/dev/null || true
git submodule update --init --recursive tools/gstack

echo "Running gstack setup..."
bash tools/gstack/setup --team

echo "✓ gstack installed. Run 'gbrain --version' to verify."
```

### Portal endpoint `GET /api/tools/status`

```python
@app.get("/api/tools/status", tags=["tools"])
async def tools_status():
    from scripts.tool_status import detect_gstack
    return {"gstack": detect_gstack()}
```

Future portal UI can poll this endpoint and offer an install button.

### `install.sh` modification (idempotent guard)

Add to the start of `install.sh`, before any gstack-dependent step:

```bash
# gstack / gbrain detection (optional — skip if already installed or not wanted)
if command -v gbrain &>/dev/null; then
  echo "✓ gbrain detected at $(which gbrain). Skipping gstack setup."
elif [ -f "tools/gstack/setup" ]; then
  echo "→ gstack submodule found. Running setup..."
  bash tools/gstack/setup --team
else
  echo "⚠ gstack not detected. RAG semantic search will use keyword-only mode."
  echo "  To install: bash install-gstack.sh"
fi
```

### What gstack brings (why it's valuable)

gstack ships:
- `gbrain` CLI — hybrid pgvector + FTS semantic search over indexed knowledge
- gstack skills — `/investigate`, `/qa`, `/context-save`, `/context-restore`, etc.
- Continuous checkpoint auto-commit for Claude Code sessions

On machines where gstack is installed, the `GbrainSearchTool` @tool automatically
provides semantic (1024-dim bge-m3) recall in addition to FTS5 keyword recall.
On machines without it, FTS5 keyword recall is the only mode — the system works
identically, just without semantic search.

---

## Commit Plan (v1 feature branch)

**Commit 1 — Retrieval layer (perpetua-core + oramasys context node)**

```bash
git add perpetua_core/gossip.py \
        tests/test_gossip_search.py \
        perpetua_core/graph/tools/gbrain_search.py \
        orama/graph/nodes/context_node.py \
        orama/graph/perpetua_graph.py \
        tests/graph/test_context_node.py
git commit -m "feat(rag): FTS5 GossipBus.search() + ContextNode + GbrainSearchTool"
```

**Commit 2 — Generation layer (LLMClient wiring)**

```bash
git add orama/graph/nodes/dispatch_node.py \
        tests/graph/test_dispatch_node.py
git commit -m "feat(dispatch): wire LLMClient into dispatch_node with context injection"
```

---

## v2 Upgrade Path (planning only — implement in oramasys/* later)

| v1 (this week) | v2.1 (LanceDB) | v2.5 (DuckDB) |
|---|---|---|
| FTS5 keyword on GossipBus | LanceDB + bge-m3 vector search | DuckDB analytical queries over fleet |
| gbrain @tool (subprocess) | gbrain as first-class ToolNode | gbrain as MCP server tool |
| LLMClient direct call | perpetua_core LLMClient with hardware policy | Full streaming + HITL context injection |
| gstack optional submodule | gstack optional sidecar (OCI image) | gstack fleet coordinator |

See `docs/v2/18-rag-and-memory-design.md` and `docs/v2/19-gstack-optional-integration.md`
for full v2 forward-plan.

---

## Agent Dispatch Plan for Implementation

Each task maps to a specialized agent:

| Task | Recommended model | Rationale |
|------|------------------|-----------|
| GossipBus FTS5 (perpetua-core) | Claude Sonnet | Python async + SQLite schema, needs reasoning |
| ContextNode (oramasys) | Claude Haiku | Mechanical wiring, small file |
| GbrainSearchTool | Claude Haiku | Mechanical subprocess wrapper |
| dispatch_node LLMClient | Claude Sonnet | Async client + fallback logic |
| gstack submodule + install.sh | Claude Sonnet | Multi-file, shell scripts |
| portal /api/tools/status | Claude Haiku | Simple FastAPI endpoint |
| Tests (all) | Claude Sonnet | TDD spec compliance |

Use `superpowers:dispatching-parallel-agents` for Tasks 1+3 (independent) and
Tasks 4+5 (independent). Tasks 2 is blocked by Task 1.

---

## Open Questions (resolved)

| Question | Answer |
|----------|--------|
| LanceDB this week? | No — deferred to v2.1. FTS5 is sufficient and has zero deps. |
| DuckDB this week? | No — deferred to v2.5. |
| Which repo for plans? | diazMelgarejo/orama-system for v1; oramasys/* later for v2. |
| gstack mandatory? | Never — always optional, always idempotent. |
| gbrain at runtime? | Via @tool subprocess wrapper, graceful fallback to empty list. |
