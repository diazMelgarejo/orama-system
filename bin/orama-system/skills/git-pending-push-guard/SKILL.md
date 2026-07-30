---
name: git-pending-push-guard
description: >-
  Block git push while MERGE_HEAD, CHERRY_PICK_HEAD, or REVERT_HEAD is set after a
  --no-commit merge/cherry-pick/revert. KB exit codes 1–4, conflict vs clean merge
  detection, periscope PR #39 remediation. Triggers on: MERGE_HEAD, pre-push blocked,
  empty PR after merge, no-commit merge, CHERRY_PICK_HEAD, REVERT_HEAD, pending git
  operation before push, GIT_PUSH_E_PENDING.
version: 1.0.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, openclaw, hermes-harness, orama-system
parent_skill: git-history-surgery
triggers:
  - MERGE_HEAD
  - CHERRY_PICK_HEAD
  - REVERT_HEAD
  - pre-push blocked
  - empty PR after merge
  - no-commit merge
  - pending git operation
  - GIT_PUSH_E_PENDING
allowed-tools: Bash(scripts/git/check_no_pending_merge.sh *), file-operations
---

# Git Pending Push Guard

> **Thin entrypoint.** Full invariant, diagrams, KB table, and decision log:
> [`../git-history-surgery/references/pending-operation-push-guard-reference-card.md`](../git-history-surgery/references/pending-operation-push-guard-reference-card.md)

## When to load

- Before `git push` after any `--no-commit` merge, cherry-pick, or revert
- When pre-push prints `GIT_PUSH_E_PENDING_*`
- When a PR describes a merge but `git diff base...head` is near-empty

## Quick check

```text
scripts/git/check_no_pending_merge.sh
# exit 0 = OK; 1–4 = see reference card KB table
```

Pre-push hook runs this automatically (`.githooks/pre-push`).

## KB exits (summary)

| Exit | Symbol |
|------|--------|
| 0 | `GIT_PUSH_OK` |
| 1 | `GIT_PUSH_E_PENDING_MERGE_CLEAN` |
| 2 | `GIT_PUSH_E_PENDING_MERGE_CONFLICT` |
| 3 | `GIT_PUSH_E_PENDING_CHERRY_PICK` |
| 4 | `GIT_PUSH_E_PENDING_REVERT` |

## Parent skill

[`../git-history-surgery/SKILL.md`](../git-history-surgery/SKILL.md) — decision item 11.
