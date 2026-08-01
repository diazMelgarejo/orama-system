---
name: cursor-pr-body
description: >-
  Layer 0 comment-only PR updates for Cursor agents — post_comment/gh pr comment
  only, never auto-change PR descriptions. When human sets
  CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1, append-only body workflow applies. Triggers
  on: update PR body, ManagePullRequest update_pr, gh pr edit, append-pr-body,
  PR summary, post_comment, PR harmonization notes.
version: 1.1.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, openclaw, hermes-harness, orama-system
parent_skill: orama-system
triggers:
  - update pr body
  - append pr body
  - post_comment
  - pr comment only
  - ManagePullRequest update_pr
  - gh pr edit
  - harmonize pr
  - append-pr-body
allowed-tools: Bash(gh pr comment *), Bash(gh pr view *)
---

# Cursor PR Body — Comment-Only + Append-Only

> **Layer 0 rule:** `.cursor/rules/pr-body-comment-only.mdc` (alwaysApply)  
> **Layers 1–6:** `.cursor/rules/append-only-pr-body.mdc` (human override only)  
> **Script:** `scripts/cursor/append-pr-body.sh` (human override only)

## Layer 0 — Default for Cursor agents

**Do not change PR descriptions automatically.** Use comments only:

| Tool | Action |
| ---- | ------ |
| `ManagePullRequest` | `post_comment` only — never `update_pr` with `body=` |
| `gh` | `gh pr comment` only — never `gh pr edit` or `append-pr-body.sh` |

Hooks enforce this at `preToolUse`, `beforeMCPExecution`, `beforeShellExecution`, and
`beforeSubmitPrompt`. You cannot bypass by choosing a different tool.

## Human override (explicit authorization required)

Operator must create an ack file **and** export the env var in the shell that runs
the write (hooks verify both; env alone is insufficient):

```bash
touch ~/.cursor/pr-body-human-override-ack
export CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1
```

Then follow append-only workflow below. Delta-only writes remain forbidden.

## Append-only workflow (Layers 1–6, override only)

```text
READ  →  BACKUP  →  MERGE (append-only)  →  WRITE (full merged body)
```

```bash
bash scripts/cursor/append-pr-body.sh <owner/repo> <pr-number> \
  --title "Follow-up: <short title>" \
  --file follow-up.md
```

## Forbidden (always)

| Bad | Why |
| --- | --- |
| Turn-end `update_pr` with latest delta | Clobbered 5+ PRs — comment instead |
| Any automatic body edit without human override | Layer 0 violation |
| Delta-only body even with override | Layers 1–6 violation |

## References

- [`references/append-only-workflow-reference-card.md`](references/append-only-workflow-reference-card.md)
- [`../../references/pr-body-anti-clobber-incident-ledger.md`](../../references/pr-body-anti-clobber-incident-ledger.md)
