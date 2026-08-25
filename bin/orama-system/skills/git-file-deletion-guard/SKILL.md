---
name: git-file-deletion-guard
description: >-
  Prevent accidental whole-file deletion at commit and pre-push time. Triggers:
  deleted files, mass deletion, git diff-filter=D, staged deletion, git add -u,
  API tree publication, tree SHA verification, and pre-push deletion audit.
version: 1.0.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, gemini, openclaw, hermes-harness, orama-system
parent_skill: git-history-surgery
triggers:
  - accidental deleted files
  - mass deletion
  - git diff-filter=D
  - staged deletion
  - git add -u
  - API tree publication
  - pre-push deletion audit
allowed-tools: Bash(scripts/git/check_file_deletion_guard.sh *), file-operations
---

# Git File Deletion Guard

> **Thin entrypoint.** Full invariant, proof bundle, override policy, and
> remote-tree publication rule: [`../git-history-surgery/references/file-deletion-preflight-reference-card.md`](../git-history-surgery/references/file-deletion-preflight-reference-card.md)

## When to load

- Before staging, committing, or pushing a change that may remove a tracked file
- When `git status` or a PR shows unexpected deletions
- Before updating a Git ref through a Git data/tree API
- When the guard reports `GIT_SCOPE_E_FILE_DELETION`

## Fast path

```bash
bash scripts/git/check_file_deletion_guard.sh --staged
bash scripts/git/check_file_deletion_guard.sh --range origin/main..HEAD
```

The local hooks run both checks automatically. The command only blocks Git
`D`-status paths; normal line removals and file modifications remain allowed.

## Deliberate deletion

Do not bypass with `--no-verify`. State the reason explicitly for the one
commit or push, and preserve that rationale in the commit/PR:

```bash
GIT_ALLOW_FILE_DELETIONS=1 \
GIT_FILE_DELETION_JUSTIFICATION='retire obsolete generated fixture' \
git commit -m 'chore: remove obsolete fixture'
```

## Parent skill

[`../git-history-surgery/SKILL.md`](../git-history-surgery/SKILL.md) — decision item 16.
