---
name: cursor-pr-body
description: >-
  Append-only GitHub PR body updates for Cursor Cloud agents and any coding agent
  using ManagePullRequest or gh. Prevents clobbering existing PR summaries when
  adding harmonization notes, CodeRabbit fix follow-ups, or CI verification blocks.
  Triggers on: update PR body, append to PR, follow-up section, ManagePullRequest
  update_pr, gh pr edit, PR harmonization notes, stack integration summary.
version: 1.0.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, openclaw, hermes-harness, orama-system
parent_skill: orama-system
triggers:
  - update pr body
  - append pr body
  - follow-up section
  - ManagePullRequest update_pr
  - gh pr edit
  - harmonize pr
  - stack integration
  - append-pr-body
allowed-tools: bash, file-operations
---

# Cursor PR Body — Append-Only Workflow

> **Cursor rule:** `.cursor/rules/append-only-pr-body.mdc` (always applied)  
> **Script:** `scripts/cursor/append-pr-body.sh`  
> **Curriculum:** [`../../cidf/references/integrative-editing-examples.md`](../../cidf/references/integrative-editing-examples.md) §1  
> **Wiki:** [`docs/wiki/12-cursor-cloud-commit-attribution.md`](../../../../docs/wiki/12-cursor-cloud-commit-attribution.md) § PR body updates

## Purpose

GitHub PR descriptions are **append-only historical records** during multi-turn agent work. Replacing the body with only the latest delta erases the original Summary, misleads reviewers, and breaks CodeRabbit release-note continuity.

This skill governs **updates to existing PRs**. For **creating** new PRs, see `.cursor/commands/pr.md`.

## Mandatory workflow (never skip)

```text
READ  →  BACKUP  →  MERGE (append-only)  →  WRITE (full merged body)
```

| Step | Command / action |
|------|------------------|
| **READ** | `gh pr view <N> --repo <owner/repo> --json body --jq .body` |
| **BACKUP** | `.git/pr-body-backups/<repo-slug>-pr<N>-<UTC-ts>.md` |
| **MERGE** | Add `## Follow-up: <title>` below original summary; preserve CodeRabbit tail |
| **WRITE** | `append-pr-body.sh` or `gh pr edit --body-file` with **full** merged markdown |

## Canonical script

```bash
bash scripts/cursor/append-pr-body.sh <owner/repo> <pr-number> \
  --title "Follow-up: harmonized onto #244" \
  --file follow-up.md
```

The script:

- Inserts before `<!-- CURSOR_AGENT_PR_BODY_END -->` when present
- Else inserts before `<!-- This is an auto-generated comment: release notes by coderabbit.ai -->`
- Else appends at end
- Aborts if the remote body changed between read and write (race guard)
- Rejects append content containing reserved delimiters

See [`references/append-only-workflow-reference-card.md`](references/append-only-workflow-reference-card.md) for tool matrix, failure modes, and examples.

## Tool matrix

| Tool | Use when | Constraints |
|------|----------|-------------|
| `append-pr-body.sh` | Default for any agent with `gh` + repo checkout | Full merge logic built in |
| `gh pr edit --body-file` | Non-agent-managed PRs; human-owned descriptions | Token needs `updatePullRequest`; pass merged file, not delta |
| `ManagePullRequest update_pr` | Cursor Cloud agent-managed PRs only | Raw markdown only — no `CURSOR_AGENT_PR_BODY_*` markers, no Cursor footer images. Fails on non-agent-managed PRs |

## What to put in a Follow-up block

- Stack harmonization: base branch, rebase tip SHA, commits skipped/kept
- Review fixes: CodeRabbit review id, commit SHA, what changed
- CI: failing job URL, root cause, local verification command + result
- Explicit **non-goals** when a side quest was deferred to another PR

## Forbidden

| Bad | Why |
|-----|-----|
| `update_pr` with only CI delta | Wipes original Summary |
| Retitle PR to match side quest | Misrepresents branch purpose |
| Skip backup on "small" edits | No rollback if merge logic wrong |
| Reorder or delete prior follow-ups | Breaks audit trail |

## Related skills

- [`../git-history-surgery/SKILL.md`](../git-history-surgery/SKILL.md) — branch harmonization before PR body notes
- [`../oramasys-method/references/integrative-merge.md`](../oramasys-method/references/integrative-merge.md) — synthesize, never amputate (applies to PR prose too)
- [`../cursor-agent/SKILL.md`](../cursor-agent/SKILL.md) — Cursor Cloud agent operations
