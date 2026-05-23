# code-review-graph MCP tools

> **Server:** `code-review-graph` in `OpenClaw/.mcp.json` (`uvx code-review-graph serve`)
> **Canonical chain:** [`tool-chain.md`](tool-chain.md)
> **Embeddings:** [`crg-embed-mode.md`](crg-embed-mode.md) — unified bge-m3 with gbrain

Use MCP tools **before** `Grep`, `Glob`, or bulk `Read` on multi-file tasks.

## Tool matrix

| Tool | When to use |
|------|-------------|
| `list_graph_stats` | Graph empty, stale, or first run of session; confirm index health |
| `detect_changes` | **Start** any diff review; risk-scored changed nodes and files |
| `semantic_search_nodes` | Unknown symbol, entry point, or keyword; no exact string yet |
| `query_graph` | Structural traces: `callers_of`, `callees_of`, `imports_of`, `tests_for`, `file_summary` |
| `get_impact_radius` | Blast radius before approving refactor or large change |
| `get_affected_flows` | Which execution paths / flows are touched |
| `get_review_context` | Token-efficient snippets **before** full file `Read` |
| `get_architecture_overview` | Unfamiliar subsystem; onboarding to a module |
| `refactor_tool` | Rename planning, dead-code hints — **not** for line-by-line review |

Slash commands (Claude Code) mirror some flows: `/code-review-graph:review-delta`, `review-pr`, `build-graph`. In **Cursor**, prefer MCP tools directly.

## Typical sequences

### Delta (local / uncommitted)

```
list_graph_stats (if unsure)
  → detect_changes
  → query_graph / get_impact_radius on hot symbols
  → get_review_context for changed + impacted files
  → gbrain code-def / search
  → Read (scoped list only)
```

### PR / branch review

```
detect_changes (or PR file list + graph refresh)
  → get_impact_radius + get_affected_flows
  → get_review_context
  → gbrain + CLAUDE.md path discovery (see review-lenses-pr.md)
  → multi-lens fan-out (see orchestration-dispatch.md)
```

### Explore unknown area (no diff yet)

```
get_architecture_overview
  → semantic_search_nodes
  → query_graph (callers_of / callees_of)
  → gbrain search
  → Read (minimal)
```

## Pairing with gbrain

Both use **Ollama bge-m3** (1024-dim) when [`crg-embed-mode`](crg-embed-mode.md) is in `gbrain` mode. Semantic rankings from CRG and gbrain are comparable.

| Need | Tool |
|------|------|
| Structure, callers, tests in graph | CRG `query_graph` |
| Symbol definition / refs | `gbrain code-def` / `code-refs` |
| Past decisions, LESSONS | `gbrain search` |
| Snippets for review | CRG `get_review_context` |

## Embedding fallback

If Ollama is down: `semantic_search_nodes` may fall back to FTS5 (see [`crg-embed-mode.md`](crg-embed-mode.md)). Toggle: `bash bin/orama-system/skills/code-review/scripts/crg-embed-mode [gbrain|local|status]`.

## Red flags

- Skipping `detect_changes` on a diff review
- `Read` on >3 files without `get_review_context` or blast-radius list
- `refactor_tool` used as a substitute for review
- Re-embedding without checking Ollama + `bge-m3`
