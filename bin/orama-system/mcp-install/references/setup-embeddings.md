# setup-embeddings — Reference

> **Script:** `../scripts/setup-embeddings`
> **Skill that owns it:** mcp-install (this skill)
> **Last updated:** 2026-05-19

## Purpose

Idempotent wire-up of the **unified gbrain + code-review-graph embedding stack** on a fresh machine, fresh checkout, or after switching Ollama models. Run as part of the disaster-recovery boot chain.

## What it does (in order)

| Step | Action | Idempotent? |
|---|---|---|
| 1 | Verify `gbrain`, `uvx`, `jq` on PATH — fail fast if missing | Yes — read-only probe |
| 2 | Verify Ollama is reachable + `bge-m3` pulled — warn if not | Yes — read-only probe |
| 3 | Check `.mcp.json` current CRG embedding model. If already `bge-m3`, skip. Else invoke `crg-embed-mode gbrain` to wire it. | Yes — checks state first |
| 4 | For each of 3 worktrees (AlphaClaw, orama-system, Perpetua-Tools), verify `.gbrain-source` file is pinned — warn if missing | Yes — read-only probe |
| 5 | Smoke test: POST to `localhost:11434/v1/embeddings` with `bge-m3` and assert 1024-dim response | Yes — pure side-effect-free probe |

## Usage

```bash
# Top-level entry — safe to run on a fresh clone, safe to re-run anytime
bash bin/orama-system/mcp-install/scripts/setup-embeddings

# Or via the install chain (preferred):
bash install.sh             # calls setup-embeddings as one step
```

## Disaster recovery flow

On a freshly-cloned machine:

```bash
git clone https://github.com/diazMelgarejo/orama-system
cd orama-system
./install.sh                # runs check-stack.sh, network_autoconfig.py,
                            # then bin/orama-system/mcp-install/scripts/setup-embeddings,
                            # then bin/orama-system/skills/code-review/scripts/crg-embed-mode gbrain
```

Result: unified bge-m3 embeddings across gbrain (PostgreSQL+pgvector) and code-review-graph (SQLite), both at 1024-dim.

## Requirements

- Ollama running with `bge-m3` model — script will warn but continue if absent
- `gbrain` CLI installed and configured (`~/.gbrain/config.json` exists)
- `uvx` (uv tool launcher) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `jq` — `brew install jq`

## Idempotency guarantees

- Step 3 reads existing `.mcp.json` and skips if already `bge-m3` — no double-write
- Steps 1, 2, 4, 5 are pure probes — zero state mutation
- Safe to run 100 times — only step 3 ever writes, and only when needed

## Next steps after running

1. Restart Claude Code to reload the MCP server with new `.mcp.json`
2. In Claude Code: call `embed_graph_tool` via MCP to re-embed the CRG graph with bge-m3
3. Run `gbrain sources list` to verify all worktrees are indexed

## Called by

- `orama-system/install.sh` — disaster-recovery boot chain
- Operator (manually) — after pulling new Ollama model or wiping `.mcp.json`

## See also

- `../../skills/code-review/references/crg-embed-mode.md` — underlying CRG embedding toggle
- [`../../references/first-run-install.md`](../../references/first-run-install.md) § 0.5 — gbrain install
- `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` — full integration plan
