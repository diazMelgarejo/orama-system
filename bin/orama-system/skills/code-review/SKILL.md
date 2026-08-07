---
name: code-review
description: |
  Use when reviewing code across multiple files, PRs, or unfamiliar areas; before refactors;
  when the user asks for blast-radius, detect_changes_tool, get_review_context_tool, semantic_search_nodes_tool,
  code-reviewer subagents, or multi-lens PR review. Applies to all coding agents in the stack.
  (Claude, Codex, Gemini, OpenClaw, Hermes, etc.).
  Triggers on: before touching unfamiliar code, code analysis,
  "review this code", "what does this function touch".
---

# Code Review

> **Canonical:** [`references/tool-chain.md`](references/tool-chain.md) (graph → gbrain → Read)
> **Persona:** [`agents/code-reviewer.md`](agents/code-reviewer.md)
> **Motivation:** Reading files inline costs 8–49× more tokens than blast-radius
> mapping. This skill enforces graph-first review for every host.

**Purpose:** token-efficient, high-signal review — map impact with
**code-review-graph**, resolve symbols with **gbrain**, read only confirmed
files, then judge with a **confidence-gated** persona (≥ 80 only).

## Non-negotiable chain

```text
1. code-review-graph  →  blast-radius / detect_changes_tool / review context
2. gbrain             →  code-def, code-refs, search (LESSONS / decisions)
3. Read               →  only graph-confirmed files
```

Never skip step 1 on multi-file tasks. Never whole-repo `Read` before graph.

## Mode router

| Choose | When |
| ------ | ---- |
| **Delta** | Uncommitted changes, small diff, pre-commit, &lt; ~10 files, no PR context |
| **PR** | `gh pr`, branch vs main, explicit PR review, large diff, or thorough/multi-lens ask |

- **Delta:** one reviewer pass after Phases A–C ([`output-format.md`](references/output-format.md)).
- **PR:** Phases A–C, then fan-out per [`review-lenses-pr.md`](references/review-lenses-pr.md) + [`orchestration-dispatch.md`](references/orchestration-dispatch.md).

## Phase A — Graph (code-review-graph MCP)

> SKIP this if CRG works normally.
> 
> READ THIS FULL CONTEXT **only** when CRG is **not** working.

Server: `OpenClaw/.mcp.json` — `uvx code-review-graph==2.3.7 serve`. Full tool
matrix: [`references/mcp-tools-crg.md`](references/mcp-tools-crg.md).
Fresh-clone / 0-node / disk-error setup and repair, MCP-disconnected
fallback to gbrain: [`references/graph-init-and-repair.md`](references/graph-init-and-repair.md).
Embed platform endpoint rule:
[`references/crg-platform-endpoints.md`](references/crg-platform-endpoints.md) ·
toggle: [`references/crg-embed-mode.md`](references/crg-embed-mode.md).

## Phase B — Gbrain

After blast-radius identifies symbols: `gbrain code-def/code-refs/code-callers/code-callees <symbol>`,
`gbrain search "<intent>"` (worktree-pinned via `.gbrain-source`, no `--source` needed in-repo).
Architecture → `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`. HITL → `docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md`.

## Phase C — Context before Read

Call `get_review_context_tool` for changed + impacted files from Phase A,
build the assigned file list (delta: diff + impact; PR: diff ∪ blast radius),
then `Read` only those files.

## Phase D — Review

**Delta:** load [`agents/code-reviewer.md`](agents/code-reviewer.md) +
[`profiles/CLAUDE.coding.md`](profiles/CLAUDE.coding.md), score against
`git diff`/`detect_changes_tool`, drop &lt; 80.

**PR:** complete A–C, build the file list, probe orchestration
([`orchestration-dispatch.md`](references/orchestration-dispatch.md)), run
the five lenses ([`review-lenses-pr.md`](references/review-lenses-pr.md)),
merge/dedupe/filter ≥ 80. Workers use the same persona + lens prompt and
never commit; they must not execute `gstack` `SKILL.md` files as procedures.

## Phase E — Report

Template and rubric: [`references/output-format.md`](references/output-format.md).
Minimum fields: scope, strengths (short), Critical / Important lists with `file:line`, verdict.

## Red flags (skill violation)

- `Read`/`Grep` on many files before `detect_changes_tool` or blast-radius
- Skipping `get_review_context_tool` then reading full files
- `gbrain search` skipped in favor of reading `LESSONS.md` inline
- Architecture from memory without a doc link
- "Let me scan the whole repo" without graph
- Nitpicks reported as Critical; PR fan-out for a two-file local delta
- Workers committing or following gstack `SKILL.md`

## Profiles

| Profile | Use |
| ------- | --- |
| [`profiles/CLAUDE.coding.md`](profiles/CLAUDE.coding.md) | Review, debug, refactor tone |
| [`profiles/CLAUDE.agents.md`](profiles/CLAUDE.agents.md) | Multi-agent pipelines |
| [`profiles/J-drona23-v5/`](profiles/J-drona23-v5/) | Default agentic coding |

## Post-review

- Micro-remediation (cluster findings by root cause,
  one commit per failure class, no revert chains):
  [`../../references/post-review-micro-remediation.md`](../../references/post-review-micro-remediation.md)
- Upstream contribution discipline (porting a fix to a vendored repo):
  [`references/upstream-contribution-discipline.md`](references/upstream-contribution-discipline.md)
- Optional provider onboarding (Claude/Codex/Antigravity/Cline/BigModel/Perplexity):
  [`../../references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md)

## References

| Doc | Content |
| --- | ------- |
| [`references/mcp-tools-crg.md`](references/mcp-tools-crg.md) | Full CRG MCP matrix + sequences |
| [`references/graph-init-and-repair.md`](references/graph-init-and-repair.md) | Fresh-clone setup, repair, MCP-disconnected fallback |
| [`references/output-format.md`](references/output-format.md) | Confidence rubric + report template |
| [`references/review-lenses-pr.md`](references/review-lenses-pr.md) | Five PR lenses + prompts |
| [`references/orchestration-dispatch.md`](references/orchestration-dispatch.md) | OmniRoute / ai-cli / Task probe |
| [`references/agent-matrix.md`](references/agent-matrix.md) | Per-host invocation |
| [`references/crg-embed-mode.md`](references/crg-embed-mode.md) | Embedding toggle |
| [`references/crg-platform-endpoints.md`](references/crg-platform-endpoints.md) | Windows vs macOS CRG URL SSoT |
| [`references/pressure-test-notes.md`](references/pressure-test-notes.md) | Expected graph-first behavior |
| [`references/upstream-contribution-discipline.md`](references/upstream-contribution-discipline.md) | Porting a fix to a vendored upstream repo |
| [`references/git-touching-skills.md`](references/git-touching-skills.md) | Git-touching skills this one composes with |
| [`agents/code-reviewer.md`](agents/code-reviewer.md) | Subagent / worker persona |

## Related skills

- Mother: [`bin/orama-system/SKILL.md`](../../SKILL.md) (OmniRoute probe, search policy)
- E2E bootstrap: [`docs/how-to/first-run-and-code-review.md`](../../../docs/how-to/first-run-and-code-review.md)
- First-run: [`skills/first-run-setup/SKILL.md`](../first-run-setup/SKILL.md) · [`references/first-run-install.md`](../../references/first-run-install.md)
- MCP stack: [`bin/orama-system/mcp-install/SKILL.md`](../../mcp-install/SKILL.md)
- Orchestration: [`~/.claude/skills/mcp-orchestration/SKILL.md`](~/.claude/skills/mcp-orchestration/SKILL.md)
- Git-touching skills this composes with: [`references/git-touching-skills.md`](references/git-touching-skills.md)
