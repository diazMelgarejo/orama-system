# Plan: gbrain Embeddings as Optional Feature of code-review-graph

**Date:** 2026-05-19  
**Status:** Phase 0 ✅ shipped · Phase 1 ✅ shipped (see `bin/orama-system/skills/code-review/scripts/crg-embed-mode`) · Phase 2 pending upstream PR · Phase 3 pending Phase 2  
**Scope:** OpenClaw toolchain (local Mac only; no upstream commitment required for Phases 0–1)

---

## Background

Two semantic-search systems coexist in OpenClaw:

| System | Storage | Model | Dimension | What it indexes |
|--------|---------|-------|-----------|-----------------|
| **code-review-graph** (CRG) v2.3.3 | SQLite `graph.db` | all-MiniLM-L6-v2 (default) | 384 | Structural AST nodes (functions, classes, imports) |
| **gbrain** v0.33.3 | pgvector (Supabase) | bge-m3 (Ollama local) | 1024 | Code pages + gstack memory + docs |

Problem: they run different models, so their vector spaces are incompatible. A `semantic_search_nodes` result and a `gbrain search` result on the same query produce vectors that can't be compared or ranked together. Using the same model on both would put them in the same vector space, enabling future unified recall.

**Key finding (confirmed via source inspection):** CRG v2.3.3 already ships an `openai` provider (`embeddings.py:268`) that accepts any OpenAI-compat endpoint, including Ollama in its `/v1/embeddings` compat mode. gbrain uses `bge-m3` via Ollama at `http://localhost:11434`. **Phase 0 = zero new code; just configuration.**

---

## Architecture Overview

```
code-review-graph MCP server
  │
  ├─ embed_graph_tool ──── EmbeddingStore (SQLite, graph.db)
  │                                │
  │                          EmbeddingProvider
  │                         ┌──────────────────────────────┐
  │                         │ local (sentence-transformers) │ ← default today
  │                         │ openai (any /v1/embeddings)   │ ← Phase 0: point at Ollama
  │                         │ google (Gemini)               │
  │                         │ minimax (embo-01)             │
  │                         │ [gbrain] (planned Phase 2)    │ ← queries pgvector directly
  │                         └──────────────────────────────┘
  │
  └─ semantic_search_nodes ── hybrid FTS5 + vector RRF

gbrain MCP server  
  │
  └─ gbrain search / code-def / code-refs ── pgvector (bge-m3, 1024-dim)
```

---

## Phases

### Phase 0 — Unified model via env config (TODAY, ~5 min)

**What:** Configure CRG's `openai` provider to call Ollama bge-m3 — the same model gbrain uses. Both tools now embed in the same 1024-dim vector space.

**How:** Update `OpenClaw/.mcp.json` env section for code-review-graph:

```json
{
  "mcpServers": {
    "code-review-graph": {
      "command": "uvx",
      "args": ["code-review-graph", "serve"],
      "env": {
        "PYTHON": "/opt/homebrew/bin/python3.13",
        "CRG_OPENAI_API_KEY": "ollama",
        "CRG_OPENAI_BASE_URL": "http://localhost:11434/v1",
        "CRG_OPENAI_MODEL": "bge-m3",
        "CRG_OPENAI_DIMENSION": "1024",
        "CRG_ACCEPT_CLOUD_EGRESS": "1"
      }
    }
  }
}
```

Note: `CRG_ACCEPT_CLOUD_EGRESS=1` suppresses the localhost-egress warning since Ollama is local (CRG already skips the warning for localhost URLs via `_is_localhost_url` check — this is belt-and-suspenders).

**After applying:** run `embed_graph_tool` (MCP) to re-embed all CRG nodes with bge-m3. This replaces the existing all-MiniLM-L6-v2 vectors (CRG detects model change and auto-re-embeds). ~2-5 min for the AlphaClaw graph (31k nodes).

**Risk:** Ollama must be running when Claude Code starts the MCP server. If Ollama is down, `embed_graph_tool` and `semantic_search_nodes` (vector leg) gracefully degrade — CRG falls back to FTS5-only hybrid search. No hard failure.

**Benefit:** `semantic_search_nodes` and `gbrain search` now return results from the same embedding space. Manually combining their ranked lists (by score) is now semantically valid.

---

### Phase 1 — Operational wrapper + fallback toggle (1–2 hours)

**What:** Add a shell helper and a `.mcp.json` toggle so you can switch between `bge-m3` mode and the default `local` mode without editing JSON manually.

**Files:**
- `bin/orama-system/skills/code-review/scripts/crg-embed-mode` — bash script (lives inside the `code-review` skill, not at the bin root)

```bash
#!/bin/bash
# Usage: crg-embed-mode [gbrain|local]
# Toggles CRG embedding provider in OpenClaw/.mcp.json
set -euo pipefail
MODE="${1:-status}"
MCP_JSON="/Users/lawrencecyremelgarejo/Documents/Terminal xCode/claude/OpenClaw/.mcp.json"

case "$MODE" in
  gbrain)
    # Set openai provider pointing to Ollama bge-m3
    jq '.mcpServers["code-review-graph"].env |= . + {
      "CRG_OPENAI_API_KEY": "ollama",
      "CRG_OPENAI_BASE_URL": "http://localhost:11434/v1",
      "CRG_OPENAI_MODEL": "bge-m3",
      "CRG_OPENAI_DIMENSION": "1024",
      "CRG_ACCEPT_CLOUD_EGRESS": "1"
    } | del(.CRG_EMBEDDING_PROVIDER)' "$MCP_JSON" > "$MCP_JSON.tmp" && mv "$MCP_JSON.tmp" "$MCP_JSON"
    echo "CRG embedding: gbrain (Ollama bge-m3 @ localhost:11434)"
    ;;
  local)
    # Remove openai keys, fall back to local sentence-transformers
    jq '.mcpServers["code-review-graph"].env |= del(
      .CRG_OPENAI_API_KEY, .CRG_OPENAI_BASE_URL,
      .CRG_OPENAI_MODEL, .CRG_OPENAI_DIMENSION, .CRG_ACCEPT_CLOUD_EGRESS
    )' "$MCP_JSON" > "$MCP_JSON.tmp" && mv "$MCP_JSON.tmp" "$MCP_JSON"
    echo "CRG embedding: local (all-MiniLM-L6-v2, offline)"
    ;;
  status)
    CRG_MODEL=$(jq -r '.mcpServers["code-review-graph"].env.CRG_OPENAI_MODEL // "local"' "$MCP_JSON" 2>/dev/null)
    echo "CRG embedding mode: $CRG_MODEL"
    ;;
  *)
    echo "Usage: crg-embed-mode [gbrain|local|status]" >&2; exit 1
    ;;
esac
```

**Routing rule:** `gbrain` mode = Ollama must be running (it always is during active dev). `local` mode = offline-safe fallback (e.g., when demoing without network).

---

### Phase 2 — Native `gbrain` provider in code-review-graph (upstream PR, ~1 day)

**What:** Add `provider="gbrain"` to `get_provider()` in CRG's `embeddings.py`. Instead of storing vectors in `EmbeddingStore` (SQLite), this provider delegates embedding calls to gbrain's Ollama endpoint AND optionally reads results back from pgvector (bypassing EmbeddingStore entirely).

**Why bother vs Phase 0?** Phase 0 still stores vectors in two separate places (CRG's SQLite + gbrain's pgvector). Phase 2 eliminates the duplicate store — CRG uses gbrain's pgvector as its vector backend. `semantic_search_nodes` queries pgvector instead of SQLite.

**Implementation sketch (new `GBrainEmbeddingProvider` in `embeddings.py`):**

```python
class GBrainEmbeddingProvider(EmbeddingProvider):
    """
    Delegates to gbrain's local Ollama (bge-m3) for embedding.
    Reads ~/.gbrain/config.json for DATABASE_URL (pgvector backend).
    """
    _MODEL = "bge-m3"
    _DIMENSION = 1024
    _OLLAMA_URL = "http://localhost:11434/api/embed"

    def embed(self, texts: list[str]) -> list[list[float]]:
        import json, urllib.request
        payload = json.dumps({"model": self._MODEL, "input": texts}).encode()
        with urllib.request.urlopen(
            urllib.request.Request(self._OLLAMA_URL, data=payload,
                                   headers={"Content-Type": "application/json"})
        ) as resp:
            body = json.loads(resp.read())
        return body["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._DIMENSION

    @property
    def name(self) -> str:
        return f"gbrain:{self._MODEL}"
```

Then in `get_provider()`:
```python
if provider == "gbrain":
    return GBrainEmbeddingProvider()
```

**pgvector read path (deeper integration):** `semantic_search_nodes` currently runs cosine similarity in Python over SQLite blobs. A v2 of this tool could hit pgvector directly (`SELECT id, 1 - (embedding <=> $1) AS score FROM ...`) for GPU-accelerated ANN search. This is a separate upstream issue from the embedding provider.

**Effort:** ~4 hours Python + tests. Good upstream PR candidate for tirth8205/code-review-graph.

---

### Phase 3 — Unified recall: single query, both corpora (future, gated only by Phase 2)

**What:** A unified `search` MCP tool that fans out to both CRG's structural graph and gbrain's semantic corpus, then merges via RRF. One call, two corpora, same model.

**Prerequisite:** Phase 2 (same vector space). **No dependency on LanceDB** — gbrain stays on pgvector permanently (it is a separate upstream repo with its own roadmap). orama-system's optional LanceDB migration (v2.1, for job/decision history) is **decoupled** from this plan: even if orama-system moves to LanceDB, gbrain remains the codebase-index source of truth via pgvector, and CRG queries it directly.

**Design:** Add a `/hybrid-search` tool to the OpenClaw MCP composite that:
1. Calls `mcp__code-review-graph__semantic_search_nodes(query)`
2. Calls `mcp__gbrain__search(query, source=<current_worktree_pin>)`
3. Merges by RRF (k=60)
4. Returns unified ranked list with provenance tags (`crg:` vs `gbrain:`)

This is an agent-level composition tool, not a change to either upstream tool.

---

## Decision: What to implement now

| Phase | Effort | Value | When |
|-------|--------|-------|------|
| 0 — env config | 5 min | Unified model, zero risk | **Today** |
| 1 — toggle script | 2 hrs | Ergonomic, offline fallback | This week |
| 2 — native provider | 4 hrs | Eliminate duplicate store, upstream PR | This sprint |
| 3 — unified recall tool | 1 day | Power feature, fan-out search | After Phase 2 |

**Recommendation:** Ship Phase 0 now (5-min `.mcp.json` edit + re-embed). Phase 1 adds operational comfort. Phase 2 is the right upstream contribution. Phase 3 unblocks as soon as Phase 2 lands — no LanceDB dependency (gbrain stays on pgvector).

---

## Phase 0 implementation checklist

- [ ] Edit `OpenClaw/.mcp.json` — add Ollama bge-m3 env vars to code-review-graph entry
- [ ] Restart Claude Code / reload MCP server
- [ ] Call `embed_graph_tool` via MCP to re-embed CRG graph with bge-m3
- [ ] Validate: `semantic_search_nodes("sanitizeOpenclawConfig")` returns relevant results
- [ ] Validate: `gbrain search "sanitizeOpenclawConfig"` returns same top node
- [ ] Commit `.mcp.json` to orama-system or OpenClaw (whichever owns it)

---

## Notes

- The `gstack-code-stem-28787e52-61949f` source (0 pages, never synced) in gbrain `sources list` is an orphan — likely from an aborted registration. Safe to remove with `gbrain sources remove gstack-code-stem-28787e52-61949f` when convenient.
- The gstack-gbrain-sync.ts orchestrator has a `list.find is not a function` bug in v1.40.0.0. Workaround: use `gbrain sync --source <id>` directly. File upstream issue against garrytan/gstack.
- **LanceDB and gbrain are fully decoupled** (clarified 2026-05-20): gbrain is a separate upstream repo and will **always use pgvector** for the codebase index. orama-system **may** migrate parts of its job/decision history to LanceDB in v2.1, but that migration does not touch gbrain. This plan stays on pgvector for the CRG↔gbrain bridge in all phases.
