---
name: deep-research
description: Multi-source deep research with EXA for discovery and Firecrawl for primary-source extraction, then cited synthesis and independent verification. Delivers gap-aware reports with source attribution. Use when the user wants thorough research on any topic with evidence and citations. Activates when the user says "research", "deep dive", "investigate", or "what's the current state of".
version: 1.1.0
compatibility: Claude Code, Cursor, Codex CLI; needs the firecrawl and/or exa MCP server
allowed-tools: Read, Write, Grep, Bash, firecrawl_search, firecrawl_scrape, web_search_exa, web_fetch_exa
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
Run tiers 1 to 3 first. Search never fires in parallel across tiers.

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

Both together give the best coverage. The two use different transports, and the
difference matters:

- **EXA (local stdio MCP).** Reach it through the shared wrapper
  `scripts/exa/exa-mcp-wrapper.sh`, which runs one `exa-mcp-daemon` behind a Unix
  socket so every concurrent agent shares a single authenticated process instead
  of each spawning its own `npx` child. Setup and key lookup order:
  [`docs/exa-integration.md`](../../../../docs/exa-integration.md).
- **Firecrawl (remote `type: http` MCP).** Connect directly. There is no local
  process to daemonize, so the shared-daemon pattern does not apply.
- **Do not switch EXA from the local stdio server to a hosted endpoint without
  explicit authorization.** If a hosted connector is already attached to the
  session, using it changes no config, but say so in the methodology note.
- **Secrets.** Never put an API key in a tracked file (`.mcp.json`, provider or
  agent configs). Use a checked-in template with `${VAR}` placeholders, resolve
  from a `0600` secrets file or the Keychain at runtime, and keep any backup of
  the resolved config outside git. Never print a token value.

## Workflow

### Step 0: Frame the pass and set a cap

Write down four inputs before searching: the **question**, the **authority
filter** (which sources count), the **output shape**, and the **cap** (how many
queries and scrapes, or how much time). When the user has already supplied them,
run the pass immediately and do not re-ask. The cap is a budget you choose and
state; it is not derived from anything, so record it in the methodology and
report what it cut off.

### Step 1: Understand the Goal

Ask 1-2 quick clarifying questions if the inputs above are not already clear:

- "What's your goal: learning, making a decision, or writing something?"
- "Any specific angle or depth you want?"

If the user says "just research it", skip ahead with reasonable defaults.

### Step 2: Plan the Research

Break the topic into 3-5 research sub-questions, each an orthogonal search
vector. Example:

- Topic: "Impact of AI on healthcare"
  - What are the main AI applications in healthcare today?
  - What clinical outcomes have been measured?
  - What are the regulatory challenges?
  - What companies are leading this space?
  - What's the market size and growth trajectory?

### Step 3: Discover (EXA first, Firecrawl as the second voice)

For EACH sub-question, search with the available tools:

```text
web_search_exa(query: "<description of the ideal page>", numResults: 8)
web_search_advanced_exa(query: "<keywords>", numResults: 5, startPublishedDate: "<12 months back>")
firecrawl_search(query: "<sub-question keywords>", limit: 8)
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

Structure the report:

```markdown
# [Topic]: Research Report
*Generated: [date] | Sources: [N] | Confidence: [High/Medium/Low]*

## Executive Summary
[3-5 sentence overview of key findings]

## 1. [First Major Theme]
[Findings with inline citations]
- Key point ([Source Name](url))
- Supporting data ([Source Name](url))

## 2. [Second Major Theme]
...

## Key Takeaways
- [Actionable insight 1]
- [Actionable insight 2]

## Open questions and gaps
[What was not found, and what the cap cut off]

## Sources
1. [Title](url): [one-line summary, publication date, excerpt-level or full read]

## Methodology
Searched [N] queries across web and news. Read [M] sources in full.
Cap: [stated cap]. Sub-questions investigated: [list]
```

### Step 6: Verify, Deliver, Crystallize

- **Verify.** Have an independent second reviewer check the claims and any code
  that follows (see Verification below). A claim a second source or reviewer
  cannot re-find is dropped or flagged unverified.
- **Deliver.** Short topics: post the full report in chat. Long reports: post the
  executive summary and key takeaways, save the full report to a file.
- **Crystallize.** Record reusable operational findings through the Perpetua-Tools
  memory tool (`.agent/tools/learn.py`, stage then graduate). Never hand-edit
  `LESSONS.md`; the memory is append-only.

## Depth levels

| Level | What you do | Label in the report |
| --- | --- | --- |
| Initial | Step 3 only: searches, no scrapes | every finding "excerpt-level" |
| Standard | Steps 3 and 4: 15-30 sources found, 3-5 read in full | read-in-full vs excerpt per source |
| Thorough | The worked example below: 6 EXA queries (about 54 sources) then 15 Firecrawl scrapes, roughly 10-15 minutes of collection | full method and cap |

## Worked example: PR-body human-grant security gap (2026-08-02)

A code review showed that a human-override grant could be forged. The research
pass was EXA first, then Firecrawl, then synthesis:

1. **EXA, 6 queries, about 54 candidate sources.** It surfaced that a TTY test
   measures terminal attachment, not human identity, that agent shells get
   pseudo-terminals, and that a plaintext marker file is forgeable.
2. **Firecrawl, 15 primary-source scrapes** of authoritative documentation, with
   the main content only.
3. **Synthesis** into a cited reference, with the raw EXA exports kept local-only
   because the scraped payloads contained email literals that repo hygiene blocks.

Read the result and the verdict table in
[`pr-body-human-grant-security-gap-research.md`](../../references/pr-body-human-grant-security-gap-research.md).
The implementation record is in Perpetua-Tools memory
(`PR_BODY_GRANT_HMAC_MVP_SAGA_2026-08-02.md`).

## Correlation with the Cline, GLM and DeepSeek memory

What Perpetua-Tools memory does and does not record about earlier runs:

- **The 2026-08-02 research above is recorded as EXA plus Firecrawl.** The saga
  does not name a Cline, GLM or DeepSeek model as having run it, so do not claim
  one did.
- **The Cline route shows up in a separate event.** A Cline fan-out run failed on
  provider auth. EXA found the official ClinePass docs and Firecrawl scraped the
  Cline CLI overview, which established that the provider id (`clinepass`) and the
  model id (`cline-pass/deepseek-v4-flash`) are different things (lesson
  `290a2efb284b`; `docs/LESSONS.md`). Rule: verify provider auth, not only the
  model slug, before trusting a Cline fan-out route (lesson `58ec2dc24e62`).
- **GLM.** ClinePass with `cline-pass/glm-5.2` is the default coding route, and
  GLM-5.2 is the last stop of the fallback chain (ClinePass, LM Studio, Ollama,
  OpenAI, then GLM-5.2). See [`glm52-fallback`](../glm52-fallback/SKILL.md).
- **DeepSeek.** The DeepSeek V4 Flash route is its own skill, parallel to the
  GLM one: [`clinepass-deepseek-flash`](../clinepass-deepseek-flash/SKILL.md).
- **Using them for research.** Those skills describe non-interactive fan-out
  workers. Whether to give one a sub-question to read and summarize from an
  already-extracted corpus is an operator choice; the memory has no record of it
  having been done. If you do, route per the skill, check auth first, and treat
  its output like any other claim: verify it against the source.

## Roles and verification

| Role | Who | Invariant |
| --- | --- | --- |
| Lead | Claude Code or the active harness | Decomposes the question, drives Steps 0-5, owns the merge gate |
| Discovery | EXA | Finds URLs; does not prove claims |
| Extraction | Firecrawl | Reads primary sources; sits downstream of discovery |
| Fan-out worker (optional) | Cline route per the skills above | Reads or summarizes extracted text; auth checked first |
| Implementer (if code follows) | Cursor Agent or Cline | Its commit messages are claims, not evidence |
| Verifier | Codex (`codex exec`, read-only, `< /dev/null`) plus a separate Claude subagent with no shared context | Reads the same source independently |

- When two reviewers with no shared context reach the same finding, treat it as
  the strongest signal available and weight it above either one's stated severity
  (lesson `fb76280fc2cd`). It is a strong signal, not proof; still re-find the
  evidence in the source.
- When another agent commits to the same branch mid-review, read the actual diff
  and run the tests before crediting any claimed fix; never trust a claimed test
  count in a commit message (lesson `11baf3e69fcb`).

## Parallel Research with Subagents

For broad topics, use the harness's subagent tool to parallelize reading:

```text
Launch 3 research agents in parallel:
1. Agent 1: Research sub-questions 1-2
2. Agent 2: Research sub-questions 3-4
3. Agent 3: Research sub-question 5 + cross-cutting themes
```

Each agent searches, reads sources, and returns findings. The main session
synthesizes into the final report. On Claude Code, the `Workflow` tool is the
mechanism, under its own explicit opt-in.

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

## Examples

```text
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research the best strategies for bootstrapping a SaaS business"
"What's happening with the US housing market right now?"
"Investigate the competitive landscape for AI code editors"
```

## References

- [`search-and-code-exploration-policy.md`](../../references/search-and-code-exploration-policy.md): the 7-tier order
- [`firecrawl` skill](../firecrawl/SKILL.md): extraction commands and auth
- [`docs/exa-integration.md`](../../../../docs/exa-integration.md): EXA setup and key lookup
- [`pr-body-human-grant-security-gap-research.md`](../../references/pr-body-human-grant-security-gap-research.md): the thorough-depth worked example

## Boundaries

### Always Do

- Cite every claim with a source link; flag single-source claims as unverified.
- State the gaps and the cap; say so when a sub-question has no good source.
- Run search tiers 1 to 3 before spending EXA or Firecrawl credits.
- Verify provider auth and read diffs and tests before crediting another agent.

### Ask First

- Before using a paid search tier or a large scrape budget.
- Before switching EXA from the local stdio server to a hosted endpoint.

### Never Do

- Print, log, or commit API keys or tokens.
- Present an inference as a sourced fact.
- Scrape blind: discovery first.
- Commit raw scraped payloads that contain personal data.
