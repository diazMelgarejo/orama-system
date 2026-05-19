---
name: code-review
description: |
  Code-review cycle for ALL coding agents (Claude, Codex, Gemini, OpenClaw, Hermes, etc.).
  Triggers on: multi-file review, PR review, before touching unfamiliar code, blast-radius
  analysis before refactoring, "review this code", "what does this function touch".
---

# Code-Review Cycle

> **Canonical doc:** `CLAUDE-instru.md § 1` (code-review-graph + gbrain chaining)
> **Motivation:** Reading all files inline inflates context 8–49x vs. blast-radius mapping.
> This skill enforces the correct tool chain for all coding agents in the stack.

---

## The Chain (use in this order, always)

```
1. code-review-graph  →  blast-radius map
2. gbrain code-def    →  symbol resolution
3. gbrain search      →  past decisions / LESSONS.md
4. Read               →  only confirmed-relevant files
```

Never skip to `Read` without completing step 1 first on multi-file tasks.

---

## Step 1 — Blast-radius map (`code-review-graph` MCP)

**When:** Start of any multi-file review or before touching code in an unfamiliar area.

MCP tool: `code-review-graph` (registered in `OpenClaw/.mcp.json`)
- `uvx code-review-graph serve` starts the MCP server
- Python 3.13 required; uvx handles the env

Available slash commands (Claude Code):
| Command | When to use |
|---------|-------------|
| `/code-review-graph:build-graph` | Rebuild after major changes |
| `/code-review-graph:review-delta` | Blast-radius of uncommitted changes |
| `/code-review-graph:review-pr` | Full PR review with impact analysis |

**Output:** File list (callers, dependents, affected tests) for the changed function/file.
Feed this list to steps 2–4 instead of reading the full repo.

---

## Step 2 — Symbol resolution (`gbrain`)

**When:** After blast-radius identifies a symbol/function you need to understand.

```bash
gbrain code-def <symbol>         # where is X defined?
gbrain code-refs <symbol>        # what uses X?
gbrain code-callers <symbol>     # what calls X?
gbrain code-callees <symbol>     # what does X call?
```

Each worktree is auto-pinned to its own indexed corpus via `.gbrain-source`.
No `--source` flag needed when calling from within the repo directory.

---

## Step 3 — Past decisions & LESSONS.md

**When:** Before making architectural or behavioral changes; or when reasoning about why code is structured a certain way.

```bash
gbrain search "<intent>"                                # this repo's history
gbrain search "<terms>" --source gstack-brain-lawrencecyremelgarejo  # cross-session memory
```

**Architecture?** → Check `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` first.
Briefly summarize (2-3 lines) + link section. Expand only if user asks.

**HITL gates?** → `docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md`

**Hardware affinity?** → `docs/v2/17-hardware-policy-enforcement.md`

---

## Step 4 — Targeted file reads

Only read files confirmed relevant by steps 1–3.

```
Read the file. Don't re-read if already in context.
```

---

## Agent compatibility matrix

This skill is designed for all agents in the stack. Each agent uses the same
chain; only the tool invocation differs:

| Agent | How to trigger step 1 | How to trigger step 2 |
|-------|----------------------|----------------------|
| **Claude Code** | `/code-review-graph:review-delta` | `gbrain code-def <symbol>` |
| **Codex** | `codex mcp call code-review-graph review_delta` | `gbrain code-def <symbol>` |
| **Gemini** | `gemini-mcp-tool` → `ask-gemini` to run codebase query | `gbrain search` |
| **OpenClaw** | Route through `orchestrator/orama_bridge.py` → PT MCP adapter | Same |
| **Hermes / ai-cli** | `ai-cli run` with prompt that invokes the MCP | Same |

---

## Contract reference

- Shared types: `Perpetua-Tools/orchestrator/contracts.py`
- Hardware policy: `Perpetua-Tools/config/model_hardware_policy.yml`
- Mirror exclusion: `_MIRROR_BACKENDS = frozenset({"lmstudio-mac"})` in `selector.py`

---

## Embedding Configuration (unified bge-m3 vector space)

Both `code-review-graph` and `gbrain` use **Ollama bge-m3** (1024-dim). This puts
`semantic_search_nodes` and `gbrain search` in the same vector space — their ranked
results can be compared and merged directly.

**Config in `OpenClaw/.mcp.json` (already set):**
```
CRG_OPENAI_API_KEY=ollama
CRG_OPENAI_BASE_URL=http://localhost:11434/v1
CRG_OPENAI_MODEL=bge-m3
CRG_OPENAI_DIMENSION=1024
```

**If Ollama is down:** `semantic_search_nodes` falls back to FTS5-only (no vectors, still works).
**To toggle:** `crg-embed-mode [gbrain|local|status]`
**To re-embed after restart:** call `embed_graph_tool` via MCP.
**Full plan:** `orama-system/docs/plans/2026-05-19-gbrain-crg-embedding-integration.md`

---

## Red flags — when this skill is being violated

- Reading `*.py` or `*.ts` files before running code-review-graph blast-radius
- `gbrain search` skipped in favor of reading `LESSONS.md` directly
- Architecture described from memory without a doc reference
- "Let me look at the full repo structure" (→ use code-review-graph instead)
- `Read` on more than 3 files without a prior blast-radius scan
- Running `embed_graph_tool` without confirming Ollama + bge-m3 is running

## MCP Tool Sequence

| Step | Tool | When |
|---|---|---|
| 1 | `list_graph_stats_tool` | Confirm graph is fresh |
| 2 | `semantic_search_nodes_tool` | Find entry points by symbol or keyword |
| 3 | `query_graph_tool` (callers_of / callees_of / file_summary) | Trace flow |
| 4 | `get_impact_radius_tool` | Blast radius of changes |
| 5 | `get_affected_flows_tool` | Which execution paths break |

Embedding setup: see `scripts/crg-embed-mode` and `references/crg-embed-mode.md`.
