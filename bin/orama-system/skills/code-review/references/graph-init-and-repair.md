# Graph Initialization & Repair (fresh clone / 0-node / disk error)

`setup-embeddings` wires the env config but **cannot** call MCP tools — the graph must be seeded interactively inside Claude Code.

## Check first

```text
list_graph_stats_tool(repo_root=<path>)
```

| Result | Action |
| -------- | -------- |
| `nodes > 0`, `embeddings_count > 0` | Graph is healthy — skip to Phase A |
| `nodes > 0`, `embeddings_count = 0` | Embeddings missing → run Step 2 only |
| `nodes = 0` | Never built or wiped → run Steps 1 + 2 |
| `disk I/O error` | Corrupted `graph.db` → delete it, then run Steps 1 + 2 |

## Step 1 — Build graph (all 3 repos independently)

```text
build_or_update_graph_tool(
  repo_root = "<repo_path>",   # orama-system / AlphaClaw / Perpetua-Tools
  full_rebuild = True,
  postprocess = "full"
)
```

Expected output per repo (ballpark):

- **orama-system**: ~160 files, ~1 461 nodes, ~10 151 edges, 12 communities
- **AlphaClaw**: ~464 files, ~3 730 nodes, ~43 638 edges, 14 communities
- **Perpetua-Tools**: ~103 files, ~1 151 nodes, ~8 099 edges, 12 communities

## Step 2 — Embed with bge-m3 (must match gbrain's model)

```text
embed_graph_tool(
  repo_root = "<repo_path>",
  provider = "openai",   # OpenAI-compat shim → Ollama
  model = "bge-m3"
)
```

**Prerequisite:** Embed backend running with `bge-m3` loaded — **macOS/Linux:** Ollama at `localhost:11434`; **Windows:** LM Studio at `localhost:1234` (see [`crg-platform-endpoints.md`](crg-platform-endpoints.md)).
If the backend is down, omit the call — CRG falls back to FTS-only keyword search.

## Fix: corrupted graph.db

```bash
rm "<repo_path>/.code-review-graph/graph.db"
# then run Steps 1 + 2 above
```

## Fix: gbrain sync blocked

```bash
# Acknowledge YAML / embedding failures and continue
gbrain sync --source <source-id> --skip-failed
```

Check `~/.gbrain/sync-failures.jsonl` to see which files failed and why.
Old failures with `"acknowledged": true` are harmless.

## Red flag: 0 nodes after install

`setup-embeddings` ran but no one called `build_or_update_graph_tool`. Add a
reminder to your first-session checklist: **after** `setup-embeddings`, call the
build + embed tools once per repo before starting any review work.

## Fix: MCP disconnected, or refreshing from the CLI (two live gotchas)

The graph tools above run *inside* Claude Code via MCP. When the `code-review-graph`
MCP shows **disconnected**, drive the `uvx` CLI directly — but mind two traps that
bit us live (2026-06-13):

1. **Cold-start timeout = the usual disconnect cause.** The first
   `uvx code-review-graph serve` of a session downloads tree-sitter-language-pack
   (~74 packages, ~31 MiB) and can blow past the MCP handshake window, so the harness
   marks it disconnected. Pre-warm the cache once, then reconnect:

   ```bash
   uvx code-review-graph --help    # one-time download; warms the uvx cache
   # then in Claude Code:  /mcp  → reconnect code-review-graph  (warm = connects fast)
   ```

2. **CLI `embed` defaults to `local` (NOT the unified provider).**
   `uvx code-review-graph embed` defaults to `--provider local` (sentence-transformers,
   not installed → hard error). You MUST pass the provider for the bge-m3 vector space.
   Full CLI refresh after a big change (mirrors the MCP build+embed path):

   ```bash
   # macOS/Linux — Ollama @ :11434
   export CRG_OPENAI_API_KEY=ollama CRG_OPENAI_BASE_URL=http://localhost:11434/v1 \
          CRG_OPENAI_MODEL=bge-m3 CRG_OPENAI_DIMENSION=1024 CRG_ACCEPT_CLOUD_EGRESS=1
   # Windows — LM Studio @ :1234 (use this instead of :11434)
   # export CRG_OPENAI_BASE_URL=http://localhost:1234/v1
   uvx code-review-graph update                                  # incremental re-parse
   uvx code-review-graph embed --provider openai --model bge-m3  # NEVER omit --provider
   uvx code-review-graph postprocess                             # flows / communities / FTS
   uvx code-review-graph status                                  # confirm nodes + embeddings
   ```

   `embed_graph_tool(provider="openai")` already does this over MCP — the `--provider`
   flag is only needed on the CLI path, where `local` is the unfortunate default.

3. **Semantic search is MCP-only — fall back to gbrain.** `semantic_search_nodes_tool`,
   `query_graph_tool`, `get_impact_radius_tool`, `get_review_context_tool` exist **only**
   over MCP — there is **no `uvx` CLI equivalent** (the CLI does build/update/embed/status,
   not search). So any skill that calls them **fails outright when the MCP is disconnected**.
   When you can't reconnect immediately, use **gbrain** for the semantic lane — it shares the
   **same bge-m3 vector space**, so results are directly comparable:
   - "where is X handled / find by meaning" → `gbrain search "<terms>"` · `gbrain query "<q>"`
   - "where is symbol Y" · "what calls Y" → `gbrain code-def Y` · `gbrain code-callers Y`
   Reconnect CRG (`/mcp`) when you specifically need graph-native blast-radius
   (`get_impact_radius`, flows, communities) that gbrain doesn't model. Never block a review
   on a dead MCP — degrade to gbrain + FTS and say so in the report.
