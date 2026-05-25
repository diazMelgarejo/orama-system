# Agent compatibility matrix

> Same review chain for every host; only invocation differs.
> Chain: **code-review-graph → gbrain → Read** (see [`SKILL.md`](../SKILL.md)).

| Agent | Step 1 (graph) | Step 2 (gbrain) | PR fan-out |
|-------|----------------|-----------------|------------|
| **Claude Code** | MCP `detect_changes`, `get_review_context`; or `/code-review-graph:review-delta` | `gbrain code-def <symbol>` | Plugin-style lenses or Task |
| **Cursor** | MCP tools (preferred) | `gbrain` CLI / MCP | `Task` + [`agents/code-reviewer.md`](../agents/code-reviewer.md) |
| **Codex** | `codex mcp call code-review-graph …` | `gbrain code-def` | ai-cli workers; **do not** run gstack SKILL.md as procedure |
| **Gemini** | Via MCP client if registered | `gbrain search` | Optional read-only doc lens via `gemini-mcp-tool` |
| **OpenClaw** | PT MCP adapter / orchestrator bridge | Same CLI | Route through OmniRoute or ai-cli per mother skill |
| **Hermes / ai-cli** | Prompt worker to call MCP first | Same | `ai-cli run` per lens — [`orchestration-dispatch.md`](orchestration-dispatch.md) |

## Contract references (orama stack)

| Topic | Location |
|-------|----------|
| Shared types | `Perpetua-Tools/orchestrator/contracts.py` |
| Hardware policy | `Perpetua-Tools/config/model_hardware_policy.yml` |
| Mirror exclusion | `_MIRROR_BACKENDS` in `selector.py` |
| Unified embeddings plan | `orama-system/docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` |

## Embedding env (OpenClaw `.mcp.json`)

```
CRG_OPENAI_API_KEY=ollama
CRG_OPENAI_BASE_URL=http://localhost:11434/v1
CRG_OPENAI_MODEL=bge-m3
CRG_OPENAI_DIMENSION=1024
```

Toggle: `bash bin/orama-system/skills/code-review/scripts/crg-embed-mode [gbrain|local|status]`

---

## MCP invoke names (footer)

Cursor and Claude Code register **code-review-graph** handlers with a `*_tool` suffix. Prose in this skill may shorten names; they map 1:1:

| Short name in docs | MCP tool name |
|--------------------|---------------|
| `detect_changes` | `detect_changes_tool` |
| `get_review_context` | `get_review_context_tool` |
| `get_impact_radius` | `get_impact_radius_tool` |
| `query_graph` | `query_graph_tool` |
| `semantic_search_nodes` | `semantic_search_nodes_tool` |
| `list_graph_stats` | `list_graph_stats_tool` |
| `build_or_update_graph` | `build_or_update_graph_tool` |

Full parameter reference: [`mcp-tools-crg.md`](mcp-tools-crg.md).

## Open TODOs

- [x] **Naming:** footer mapping added (2026-05-25)
- [ ] Host surface map: [`docs/reference/agent-first-open-visibility.md`](../../../../docs/reference/agent-first-open-visibility.md)
