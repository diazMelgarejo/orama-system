# Deep research: depth levels, parallel reading and example requests

Supporting detail for the [deep-research skill](../SKILL.md).

## Depth levels

| Level | What you do | Label in the report |
| --- | --- | --- |
| Initial | Step 3 only: searches, no scrapes | every finding "excerpt-level" |
| Standard | Steps 3 and 4: 15-30 sources found, 3-5 read in full | read-in-full vs excerpt per source |
| Thorough | The worked example below: 6 EXA queries (about 54 sources) then 15 Firecrawl scrapes, roughly 10-15 minutes of collection | full method and cap |

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

## Examples

```text
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research the best strategies for bootstrapping a SaaS business"
"What's happening with the US housing market right now?"
"Investigate the competitive landscape for AI code editors"
```

## Planning examples

Clarifying questions for Step 1:

- "What's your goal: learning, making a decision, or writing something?"
- "Any specific angle or depth you want?"

Sub-questions for Step 2:

- Topic: "Impact of AI on healthcare"
  - What are the main AI applications in healthcare today?
  - What clinical outcomes have been measured?
  - What are the regulatory challenges?
  - What companies are leading this space?
  - What's the market size and growth trajectory?
