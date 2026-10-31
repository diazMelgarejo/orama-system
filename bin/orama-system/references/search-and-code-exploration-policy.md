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
3. Known local code / docs — Grep for exact strings or regex, and Read of the files tiers 1-2 surfaced,
   repo docs (`docs/v2/`, ADRs) and PT `.agent` memory; local and zero cost
4. Brave Search API — web facts, current state
5. Perplexity API (inline) — deep web synthesis
6. EXA + Firecrawl playbook — [`skills/deep-research/SKILL.md`](../skills/deep-research/SKILL.md):
   EXA discovery, then Firecrawl scrape of primary sources; paid credits and many calls, so a capped pass
7. Grok API — most expensive; last resort, and only when available

**NEVER:** parallel-fire all search tools. Use the cheapest first.
**ALWAYS:** `AskUserQuestion` for decisions — never auto-select between ambiguous options.

**Extraction, not discovery:** Firecrawl is the second half of tier 6. Once any tier finds a URL, use
[`skills/firecrawl/SKILL.md`](../skills/firecrawl/SKILL.md) to scrape,
interact with, parse, or monitor it — Firecrawl sits downstream of this
policy, it doesn't replace it.

## Older mentions of the five-tier chain

Before 2026-10-30 the chain was written as gbrain, CRG, Brave, Perplexity, Grok. The seven-tier
order above is canonical. These documents still quote the older chain; they are kept as written
(historical or lint-blocked), and this table is the pointer to the current order.

| Document | Where it quotes the older chain | State |
| --- | --- | --- |
| [tiered-model navigator](../../../docs/reference/tiered-model-implementation-navigator.md) | frugality chain bullets (two places) | kept as written |
| [v2/18 migration plan](../../../docs/v2/18-master-alignment-v2-migration-plan.md) | CrewAI and AutoGen bullet | kept as written |
| [v2/29 mastery plan](../../../docs/v2/29-oramasys-mastery-implementation-plan.md) | frugality chain bullet | kept as written |
| [v2/41 stack blend](../../../docs/v2/41-agentic-stack-gstack-gbrain-memory-blend.md) | Search frugality paragraph | dated note added beside it |
| [ORAMASYS-MASTERY-v3](../../../docs/v2/references/ORAMASYS-MASTERY-v3.md) | six-tier variant with Grep | kept as written |
| [2026-05-20 plan](../../../docs/superpowers/plans/2026-05-20-cc-openclaw-master-alignment.md) | Sub-C bullet | dated note added beside it |
| [2026-05-20 spec](../../../docs/superpowers/specs/2026-05-20-cc-openclaw-master-alignment-design.md) | search frugality bullet | kept as written |
