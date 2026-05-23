# crg-embed-mode — Reference

> **Script:** `../scripts/crg-embed-mode`
> **Skill that owns it:** code-review (this skill)
> **Last updated:** 2026-05-19

## Purpose

Toggle the code-review-graph (CRG) MCP server's embedding provider between two modes:

| Mode | Backend | Model | Dimensions | When to use |
|---|---|---|---|---|
| `gbrain` | Ollama @ `localhost:11434/v1` | `bge-m3` | 1024 | Default — unified vector space with gbrain. Required for semantic_search_nodes to share embeddings with gbrain search. |
| `local` | sentence-transformers (in-process) | `all-MiniLM-L6-v2` | 384 | Offline-safe fallback. No Ollama dependency. |
| `status` | — | — | — | Print current mode (default if no arg). |

## Usage

```bash
# From OpenClaw root or anywhere — script discovers .mcp.json via $OPENCLAW_MCP_JSON
bash bin/orama-system/skills/code-review/scripts/crg-embed-mode gbrain
bash bin/orama-system/skills/code-review/scripts/crg-embed-mode local
bash bin/orama-system/skills/code-review/scripts/crg-embed-mode status
```

## How it works

1. Edits `OpenClaw/.mcp.json` in place via `jq`
2. Sets/unsets `CRG_OPENAI_*` env vars for the code-review-graph MCP server entry
3. Idempotent — safe to re-run
4. After switching: **restart Claude Code** to reload the MCP server, then call `embed_graph_tool` via MCP to re-embed the graph with the new model

## Requirements

- `jq` (install: `brew install jq`)
- For `gbrain` mode: Ollama running at `localhost:11434` with `bge-m3` pulled (`ollama pull bge-m3`)

## Idempotency / Disaster Recovery

- Safe to run on a fresh clone — checks `$OPENCLAW_MCP_JSON` and overrides only the env block
- If `bge-m3` is missing, mode still switches but emits a warning; CRG falls back to FTS-only until Ollama is up
- Switching modes **invalidates existing embeddings** — always re-embed after switch

## Called by

- `mcp-install/scripts/setup-embeddings` — invokes `crg-embed-mode gbrain` as part of the disaster-recovery boot chain
- Operator (manually) — for mode toggles and status checks

## See also

- [`../../references/first-run-install.md`](../../references/first-run-install.md) § 0.4 — code-review-graph install
- `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` — full integration plan
- `mcp-install/references/setup-embeddings.md` — the wrapper that invokes this script
