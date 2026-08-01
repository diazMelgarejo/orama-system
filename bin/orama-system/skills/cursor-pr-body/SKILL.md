---
name: cursor-pr-body
description: >-
  Layer 0 comment-only PR updates for Cursor agents — post_comment/gh pr comment
  only, never auto-change PR descriptions. After operator grant via
  grant-pr-body-human-override.sh, append-pr-body.sh is the only allowed write path.
  Triggers on: update PR body, ManagePullRequest update_pr, gh pr edit, append-pr-body,
  PR summary, post_comment, PR harmonization notes.
version: 1.2.0
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
> **Layers 1–6:** `.cursor/rules/append-only-pr-body.mdc` (operator grant only)  
> **Grant:** `scripts/cursor/grant-pr-body-human-override.sh` (operator interactive)  
> **Write:** `scripts/cursor/append-pr-body.sh` (only authorized body-write path)

## Layer 0 — Default for Cursor agents

**Do not change PR descriptions automatically.** Use comments only:

| Tool | Action |
| ---- | ------ |
| `ManagePullRequest` | `post_comment` only — never `update_pr` with `body=` |
| `gh` | `gh pr comment` only — never `gh pr edit` or direct body API calls |

Hooks enforce this at `preToolUse`, `beforeMCPExecution`, `beforeShellExecution`, and
`beforeSubmitPrompt`. You cannot bypass by choosing a different tool.

## Operator grant (explicit authorization)

The **operator** runs `scripts/cursor/grant-pr-body-human-override.sh` in an
interactive terminal. Agents must not run the grant script or forge the ack file.

After grant, agents may run **only**:

```bash
bash scripts/cursor/append-pr-body.sh <owner/repo> <pr-number> \
  --title "Follow-up: <short title>" \
  --file follow-up.md
```

Direct `update_pr`, `gh pr edit --body-file`, and `gh api` body mutations remain
**denied** even with a grant.

## Append-only workflow (Layers 1–6, grant + append-pr-body only)

```text
READ  →  BACKUP  →  MERGE (append-only)  →  WRITE (full merged body)
```

## Forbidden (always)

| Bad | Why |
| --- | --- |
| Turn-end `update_pr` with latest delta | Clobbered 5+ PRs — comment instead |
| Any automatic body edit without operator grant | Layer 0 violation |
| `gh pr edit` / `gh api` after grant | Grant permits append-pr-body.sh only |
| Delta-only body even with grant | Layers 1–6 violation |

## References

- [`references/append-only-workflow-reference-card.md`](references/append-only-workflow-reference-card.md)
- [`../../references/pr-body-anti-clobber-incident-ledger.md`](../../references/pr-body-anti-clobber-incident-ledger.md)
