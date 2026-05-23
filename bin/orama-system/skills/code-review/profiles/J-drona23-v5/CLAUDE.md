# Profile: J-drona23-v5 (default agentic coding)

> This folder is **outside any git repo**. The profile is a behavior bundle, not a project.

## Meta-rule: Progressive Disclosure (Horse Pulls Cart)

Documents own content. This file navigates.
When in doubt: read the doc. Don't restate it here.
Skills operationalize docs — they don't copy them.
Full instructions if folder is not inside a repo → [`../../../references/first-run-install.md`](../../../references/first-run-install.md)

## Profile structure

| File | Purpose |
|------|---------|
| [`rules/workflow.md`](rules/workflow.md) | MUST / NEVER rules — before/while/after coding |
| [`agents/builder.md`](agents/builder.md) | Builder agent contract (50-call budget, chain order) |
| [`reference/patterns.md`](reference/patterns.md) | Good vs anti-patterns, multi-repo conventions |

## Activation

For agentic projects (`perpetua*`, `AlphaClaw`, `OpenClaw`, `periscope`, `agentsview`):
read `rules/workflow.md` first, then `agents/builder.md`. Drop-ins live one level up:

- [`../CLAUDE.coding.md`](../CLAUDE.coding.md) — code review, debugging, refactoring
- [`../CLAUDE.agents.md`](../CLAUDE.agents.md) — multi-agent automation pipelines

## Tool-chain reminder

```
code-review-graph (MCP)  →  gbrain code-def / search  →  Read
```

Never skip to `Read` on a multi-file task. See [`../../references/tool-chain.md`](../../references/tool-chain.md).
