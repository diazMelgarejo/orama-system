# Code exploration tool chain

> **Owner:** code-review skill
> **Last updated:** 2026-05-23

## Order (non-negotiable)

```
1. code-review-graph  →  blast-radius, detect_changes_tool, review context
2. gbrain             →  code-def, code-refs, search (decisions / LESSONS)
3. Read               →  only graph-confirmed files
```

Never skip step 1 on multi-file tasks. Never whole-repo `Read` before the graph.

## code-review-graph (MCP)

| Tool | When |
|------|------|
| `detect_changes_tool` | Start of any diff review |
| `get_review_context_tool` | Snippets before full file read |
| `get_impact_radius_tool` | Refactor / merge risk |
| `get_affected_flows_tool` | Broken execution paths |
| `query_graph_tool` | callers, callees, imports, tests |
| `semantic_search_nodes_tool` | Unknown symbol or keyword |
| `get_architecture_overview_tool` | Unfamiliar subsystem |

Full matrix: [`mcp-tools-crg.md`](mcp-tools-crg.md)

## gbrain (CLI)

| Command | When |
|---------|------|
| `gbrain search "<terms>"` | Semantic question, no exact string |
| `gbrain query "<question>"` | Natural language codebase question |
| `gbrain code-def <symbol>` | Symbol definition |
| `gbrain code-refs <symbol>` | References |
| `gbrain code-callers <symbol>` | Callers |
| `gbrain code-callees <symbol>` | Callees |
| `gbrain search "<terms>" --source gstack-brain-<user>` | Past decisions, learnings |

## First-run prerequisites

Install and wire tools via [`../../../references/first-run-install.md`](../../../references/first-run-install.md) and the E2E guide [`../../../../docs/how-to/first-run-and-code-review.md`](../../../../docs/how-to/first-run-and-code-review.md). Bootstrap:

```bash
bash bin/orama-system/scripts/first-run-install.sh run
```
