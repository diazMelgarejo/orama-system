---
name: deep-research
description: Multi-source deep research with EXA for discovery and Firecrawl for primary-source extraction, then cited synthesis and independent verification. Delivers gap-aware reports with source attribution. Use when the user wants thorough research on any topic with evidence and citations. Activates when the user says "research", "deep dive", "investigate", or "what's the current state of".
version: 1.2.0
compatibility: Claude Code, Cursor, Codex CLI; needs the firecrawl and/or exa MCP server
allowed-tools: Read, Write, Grep, Bash, firecrawl_search, firecrawl_scrape, firecrawl_crawl, web_search_exa, web_search_advanced_exa, web_fetch_exa, crawling_exa
---

# Deep Research

Produce thorough, cited research reports from multiple web sources using the
EXA and Firecrawl MCP tools: EXA finds the sources, Firecrawl reads the primary
ones, and a second reviewer checks the result before it is trusted.

## Purpose

Turn a research question into a cited, gap-aware report with a recorded method.
This is the canonical card, at `bin/orama-system/skills/deep-research/`. The
Cursor copy under `.cursor/.agents/skills/` is only a pointer to it.

It is tier 6 of the cheapest-first search order, so it is not the first thing to
reach for:

```text
1 gbrain  2 code-review-graph  3 known local code/docs  4 Brave  5 Perplexity
6 EXA + Firecrawl playbook (this skill)  7 Grok (most expensive, last, when available)
```

The full order and its rules live in
[`search-and-code-exploration-policy.md`](../../references/search-and-code-exploration-policy.md).
Run tiers 1 to 5 first, in order, and stop at the first that answers. Asking for
this skill does not skip them unless the operator says so. If a tier is not
available in this harness, name it in the methodology and move on. Search never
fires in parallel across tiers.

## When to Activate

- User asks to research any topic in depth
- Competitive analysis, technology evaluation, or market sizing
- Due diligence on companies, investors, or technologies
- Any question requiring synthesis from multiple sources
- User says "research", "deep dive", "investigate", or "what's the current state of"

## Tool contract

At least one of:

- **firecrawl**: `firecrawl_search`, `firecrawl_scrape`, `firecrawl_crawl`
- **exa**: `web_search_exa` and `web_fetch_exa`; the stdio server may also expose
  `web_search_advanced_exa` and `crawling_exa`

Both together give the best coverage.
**Never call a tool the session does not have.**
Check what is connected, then use the matching row:

| Connected | Discover with | Read with | Say in the methodology |
| --- | --- | --- | --- |
| EXA and Firecrawl | EXA | `firecrawl_scrape`, `web_fetch_exa` as a second voice | Nothing extra |
| EXA only | EXA | `web_fetch_exa`; skip every Firecrawl call | Firecrawl was unavailable |
| Firecrawl only | `firecrawl_search`, the one degraded fallback; skip every EXA call | `firecrawl_scrape` | EXA was unavailable, so discovery is degraded |
| Neither | Stop this tier | Nothing | Neither server was connected; move to tier 7 or ask |

`web_search_advanced_exa` and `crawling_exa` exist only on the stdio server. Skip
them on a hosted connector that does not list them.

How each harness connects, the shared EXA wrapper, the hosted exceptions and the
secrets rules: [`references/transports.md`](references/transports.md).

## Workflow

### Step 0: Frame the pass and set a cap

Write down four inputs before searching: the **question**, the **authority
filter** (which sources count), the **output shape**, and the **cap** (how many
queries and scrapes, or how much time). When the user has already supplied them,
run the pass immediately and do not re-ask. The cap is a budget you choose and
state; it is not derived from anything, so record it in the methodology and
report what it cut off.

### Step 1: Understand the Goal

Ask 1-2 quick clarifying questions if the inputs above are not already clear.
If the user says "just research it", skip ahead with reasonable defaults.

### Step 2: Plan the Research

Break the topic into 3-5 research sub-questions, each an orthogonal search
vector. A worked set is in the references.

### Step 3: Discover with EXA

For EACH sub-question, find candidate URLs with EXA. Firecrawl reads them in Step 4:

```text
web_search_exa(query: "<description of the ideal page>", numResults: 8)
web_search_advanced_exa(query: "<keywords>", numResults: 5, startPublishedDate: "<12 months back>")
```

Search strategy:

- Describe the page you want ("official docs comparing X and Y") rather than
  listing keywords; EXA ranks on meaning.
- Use 2-3 keyword variations per sub-question; mix general and news-focused.
- Aim for 15-30 unique sources in a standard pass.
- Prioritize academic, official and primary sources over reputable news, then
  blogs, then forums. Treat vendor pages as biased and say so.
- Filter to the last 12 months where recency matters; keep older sources only if
  they are foundational, and mark their date.
- Never scrape blind. Discovery decides which URLs are worth a scrape.

### Step 4: Deep-Read Key Sources

For the most promising URLs, fetch full content:

```text
firecrawl_scrape(url: "<url>", formats: ["markdown"], onlyMainContent: true)
web_fetch_exa(urls: ["<url>"])
```

Read 3-5 key sources in full for depth. Do not rely only on search snippets.
Findings drawn from a snippet alone are labelled **excerpt-level** in the report.

Keep raw output in a local, untracked `.firecrawl/` cache. Promote it into a
tracked archive only deliberately, after redacting emails, tokens, request IDs and
personal path fragments (repo hygiene blocks them in tracked files).

### Step 5: Synthesize and Write Report

Write the report from
[`references/report-template.md`](references/report-template.md). It has the
sections every report carries, including open questions, the cap and the method.

### Step 6: Verify, Deliver, Crystallize

- **Verify.** Have an independent second reviewer check the claims and any code
  that follows (see Verification below). A claim a second source or reviewer
  cannot re-find is dropped or flagged unverified.
- **Deliver.** Short topics: post the full report in chat. Long reports: post the
  executive summary and key takeaways, save the full report to a file.
- **Crystallize.** Record reusable operational findings through the Perpetua-Tools
  memory tool (`.agent/tools/learn.py`, stage then graduate). Never hand-edit
  `LESSONS.md`; the memory is append-only.

## Depth and parallel reading

Pick a depth and label it in the report: initial, standard or thorough. For broad
topics, parallelize the reading with subagents, never the search tiers. Details
and examples: [`references/depth-and-examples.md`](references/depth-and-examples.md).

## Roles and verification

Discovery finds URLs and does not prove claims. Extraction sits downstream of it.
The lead owns the merge gate, and two reviewers with no shared context give the
strongest signal. The role table, a worked example and what memory records about
earlier runs: [`references/evidence-and-roles.md`](references/evidence-and-roles.md).

## Quality Rules

1. **Every claim needs a source.** No unsourced assertions.
2. **Cross-reference.** If only one source says it, flag it as unverified.
3. **Recency matters.** Prefer sources from the last 12 months, and show dates.
4. **Acknowledge gaps.** If you couldn't find good info on a sub-question, say so.
5. **No hallucination.** If you don't know, say "insufficient data found."
6. **Separate fact from inference.** Label estimates, projections, and opinions clearly.
7. **No silent caps.** State the cap and what it excluded.
8. **Mark depth.** Excerpt-level and read-in-full findings are labelled differently.
9. **Bias check.** Vendor and marketing pages are flagged as such.

## References

- [`search-and-code-exploration-policy.md`](../../references/search-and-code-exploration-policy.md): the 7-tier order
- [`references/transports.md`](references/transports.md): EXA and Firecrawl transports and the hosted exceptions
- [`references/report-template.md`](references/report-template.md): the report shape
- [`references/evidence-and-roles.md`](references/evidence-and-roles.md): worked example, past runs and roles
- [`references/depth-and-examples.md`](references/depth-and-examples.md): depth levels, parallel reading, example requests
- [`firecrawl` skill](../firecrawl/SKILL.md): extraction commands and auth
- [`docs/exa-integration.md`](../../../../docs/exa-integration.md): EXA setup and key lookup
- [`pr-body-human-grant-security-gap-research.md`](../../references/pr-body-human-grant-security-gap-research.md): the thorough-depth worked example

## Boundaries

### Always Do

- Cite every claim with a source link; flag single-source claims as unverified.
- State the gaps and the cap; say so when a sub-question has no good source.
- Run search tiers 1 to 5 before spending EXA or Firecrawl credits.
- Verify provider auth and read diffs and tests before crediting another agent.

### Ask First

- Before using a paid search tier or a large scrape budget.
- Before switching EXA from the local stdio server to a hosted endpoint.

### Never Do

- Print, log, or commit API keys or tokens.
- Present an inference as a sourced fact.
- Scrape blind: discovery first.
- Commit raw scraped payloads that contain personal data.
