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

<!-- THIN-WRAPPER: canonical skill lives in orama-system/bin/orama-system -->

# code-review (thin wrapper)

Canonical, permanent implementation: `../../../bin/orama-system/skills/code-review/`.
**Read it before proceeding** — this wrapper only carries discovery metadata.

Pre-wrapper body preserved at `SKILL.md.premerge-20260722.bak`.
