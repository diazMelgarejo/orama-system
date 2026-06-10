# Search Frugality — gbrain + gstack + CRG

The data-context layer. Prefer local code indexes and curated memory before any
paid or external tool. Tool names vary by harness; preserve the ordering even
when the exact integration is unavailable.

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

Run `/sync-gbrain` after meaningful code changes when gbrain/gstack is installed.
Fallback: if gbrain is unavailable or errors, use CRG MCP tools or the current
harness's cheapest local code-search equivalent before broad Grep.

## code-review-graph (CRG)

For multi-file code questions, use CRG MCP tools BEFORE Grep/Read when available.
Chain: CRG (blast-radius) → gbrain code-def → gbrain search → Read (confirmed files only).

## When Grep is right

Known exact strings, regex, multiline patterns, file globs.

## Web — use the approved harness path

Use the current harness's approved browser/search path. In Claude/gstack
environments, prefer `/browse` and avoid raw browser MCP calls.
