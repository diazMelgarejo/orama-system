# Search Frugality — gbrain + gstack + CRG

The data-context layer. The machine already indexes its own code and curated
knowledge locally and for free. Always exhaust local memory before any paid tool.

## The chain (stop at the first tier that answers)

```
gbrain  →  code-review-graph (CRG)  →  Brave  →  Perplexity  →  Grok
(local)    (local graph)              (free)    (paid)         (last resort)
```

## gbrain — local semantic memory

Two indexed corpora:
- **This worktree's code** — auto-pinned via `.gbrain-source` (kubectl-style context).
  No `--source` flag needed; routes to code on disk in this worktree.
- **Curated memory** — `~/.gstack/` as `gstack-brain-<user>` source.

| Question | Command |
|---|---|
| "Where is X handled?" | `gbrain search "<terms>"` or `gbrain query "<q>"` |
| "Where is Y defined?" | `gbrain code-def <symbol>` |
| "Where is Y referenced?" | `gbrain code-refs <symbol>` |
| "What calls Y?" | `gbrain code-callers <symbol>` |
| "What does Y depend on?" | `gbrain code-callees <symbol>` |
| "What did we decide?" | `gbrain search "<terms>" --source gstack-brain-<user>` |

Run `/sync-gbrain` after meaningful code changes.
Sandbox fallback: if gbrain errors `getaddrinfo ENOTFOUND`, use CRG MCP tools instead.

## code-review-graph (CRG)

For multi-file code questions, use CRG MCP tools BEFORE Grep/Read.
Chain: CRG (blast-radius) → gbrain code-def → gbrain search → Read (confirmed files only).

## When Grep is right

Known exact strings, regex, multiline patterns, file globs.

## Web — always through gstack

ALWAYS `/browse`. NEVER `mcp__claude-in-chrome__*` directly.
gstack v1.37.0.0 at `~/.claude/skills/gstack`.
