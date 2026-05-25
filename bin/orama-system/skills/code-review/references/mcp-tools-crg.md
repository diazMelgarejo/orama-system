# code-review-graph MCP tools

> **Server:** `code-review-graph` in `OpenClaw/.mcp.json` (`uvx code-review-graph serve`)
> **Canonical chain:** [`tool-chain.md`](tool-chain.md)
> **Embeddings:** [`crg-embed-mode.md`](crg-embed-mode.md) — unified bge-m3 with gbrain

Use MCP tools **before** `Grep`, `Glob`, or bulk `Read` on multi-file tasks.

**Naming:** Invoke the `*_tool` names below (what Cursor/Claude MCP exposes). The Python package also documents shortened aliases without `_tool` (e.g. `list_graph_stats` = `list_graph_stats_tool`).

## Tool matrix

| Tool | When to use |
|------|-------------|
| `list_graph_stats_tool` | Graph empty, stale, or first run of session; confirm index health |
| `detect_changes_tool` | **Start** any diff review; risk-scored changed nodes and files |
| `semantic_search_nodes_tool` | Unknown symbol, entry point, or keyword; no exact string yet |
| `query_graph_tool` | Structural traces: `callers_of`, `callees_of`, `imports_of`, `tests_for`, `file_summary` |
| `get_impact_radius_tool` | Blast radius before approving refactor or large change |
| `get_affected_flows_tool` | Which execution paths / flows are touched |
| `get_review_context_tool` | Token-efficient snippets **before** full file `Read` |
| `get_architecture_overview_tool` | Unfamiliar subsystem; onboarding to a module |
| `refactor_tool` | Rename planning, dead-code hints — **not** for line-by-line review |

Slash commands (Claude Code) mirror some flows: `/code-review-graph:review-delta`, `review-pr`, `build-graph`. In **Cursor**, prefer MCP tools directly.

## Typical sequences

### Delta (local / uncommitted)

```
list_graph_stats_tool (if unsure)
  → detect_changes_tool
  → query_graph_tool / get_impact_radius_tool on hot symbols
  → get_review_context_tool for changed + impacted files
  → gbrain code-def / search
  → Read (scoped list only)
```

### PR / branch review

```
detect_changes_tool (or PR file list + graph refresh)
  → get_impact_radius_tool + get_affected_flows_tool
  → get_review_context_tool
  → gbrain + CLAUDE.md path discovery (see review-lenses-pr.md)
  → multi-lens fan-out (see orchestration-dispatch.md)
```

### Explore unknown area (no diff yet)

```
get_architecture_overview_tool
  → semantic_search_nodes_tool
  → query_graph_tool (callers_of / callees_of)
  → gbrain search
  → Read (minimal)
```

## Pairing with gbrain

Both use **Ollama bge-m3** (1024-dim) when [`crg-embed-mode`](crg-embed-mode.md) is in `gbrain` mode. Semantic rankings from CRG and gbrain are comparable.

| Need | Tool |
|------|------|
| Structure, callers, tests in graph | CRG `query_graph_tool` |
| Symbol definition / refs | `gbrain code-def` / `code-refs` |
| Past decisions, LESSONS | `gbrain search` |
| Snippets for review | CRG `get_review_context_tool` |

## Embedding fallback

If Ollama is down: `semantic_search_nodes` may fall back to FTS5 (see [`crg-embed-mode.md`](crg-embed-mode.md)). Toggle: `bash bin/orama-system/skills/code-review/scripts/crg-embed-mode [gbrain|local|status]`.

## Red flags

- Skipping `detect_changes_tool` on a diff review
- `Read` on >3 files without `get_review_context_tool` or blast-radius list
- `refactor_tool` used as a substitute for review
- Re-embedding without checking Ollama + `bge-m3`
