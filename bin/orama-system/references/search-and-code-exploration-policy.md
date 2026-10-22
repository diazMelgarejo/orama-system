<!-- lint-ignore LINT-013 -->
# Search Policy and Code Exploration Order

> The frugal search chain (cheapest source first, never guess) and the code-exploration
> order (code-review-graph before Grep/Read) that every orama agent follows. Moved verbatim
> out of `SKILL.md`; the `## Search Policy` anchor in `SKILL.md` stays as a pointer so
> existing links keep resolving. Paths in code spans are relative to `bin/orama-system/`;
> link targets were rebased for this folder.

## Code Exploration Order

Use code-review-graph MCP tools BEFORE Grep/Read for any multi-file question. Chain: code-review-graph (blast-radius) → gbrain code-def (symbols) → gbrain search (decisions) → Read (confirmed files only). Never default to Grep for code questions.

**RAG wiring (CLI + Desktop) — single enforcer:** the semantic lane needs the gbrain + CRG MCP servers registered in both surfaces. Do NOT re-check this per skill — run the canonical `python3 scripts/ensure-rag-mcp.py [--apply]` (also run by `start.sh`). If CRG's MCP is down, its semantic search has no CLI fallback → degrade to `gbrain search`/`code-def` (same bge-m3 vector space). Reconnect recipe: `code-review` skill § "Fix: MCP disconnected".

## Search Policy

**RULE: Never guess when information is scarce.**
Search in this order — stop at the first satisfying result:

1. `/sync-gbrain` + `gbrain query "<question>"` — local semantic memory, zero cost
2. `code-review-graph: semantic_search_nodes` — structural code context
3. Brave Search API — web facts, current state
4. Perplexity API (inline) — deep web synthesis
5. Grok API — last resort only

**NEVER:** parallel-fire all search tools. Use the cheapest first.
**ALWAYS:** `AskUserQuestion` for decisions — never auto-select between ambiguous options.

**Extraction, not discovery:** once this chain finds a URL, use
[`skills/firecrawl/SKILL.md`](../skills/firecrawl/SKILL.md) to scrape,
interact with, parse, or monitor it — Firecrawl sits downstream of this
policy, it doesn't replace it.
