---
name: stacked-pr-naming
description: >-
  Canonical stacked-PR branch and title format so PR(N+1) is based on PR(N)
  and merge order is obvious in the PR name. Activates for stacked PRs,
  stack/NN branches, [NN/TT → merged] titles, security PR stacking, periscope
  onto-merged branches, PR(N+1) rebase, and conflict-minimizing merge order.
version: 1.0.0
license: Apache 2.0
compatibility: cursor, claude-code, codex, openclaw, hermes-harness, orama-system
parent_skill: git-history-surgery
triggers:
  - stacked PR
  - stack/NN
  - PR(N+1)
  - merge order
  - onto-merged
  - security PR stacking
  - [0/4 → merged]
  - branch naming convention
allowed-tools: file-operations
---

# Stacked PR Naming

> **Thin OSSF-1 entry.** Full formats, repo integration bases, and worked
> periscope stack:
> [`../git-history-surgery/references/stacked-pr-naming-reference-card.md`](../git-history-surgery/references/stacked-pr-naming-reference-card.md)

## Purpose

Keep stacked work mergeable: one logical fix per PR, `PR(N+1)` rebased on
`PR(N)`, titles that show `[NN/TT → <integration-base>]`.

## When to Use

- Opening more than one dependent PR against the same integration base
- Security remediation stacks (`SECURITY.md`)
- Periscope fork work (base is `merged`, never `main`)
- Closing wrong-base PRs and replaying them onto a stack

## Load Order

1. This `SKILL.md`.
2. The reference card (formats + chain).
3. [`../oramasys-method/references/integrative-merge.md`](../oramasys-method/references/integrative-merge.md)
   when resolving conflicts inside the stack.

## Workflow

1. Pick the **integration base** for the repo (card table).
2. Order work to **minimize conflicts** (lineage/sync first, then isolated
   deps, then docs).
3. Create `stack/00-…` from `origin/<integration-base>`.
4. Create `stack/(N+1)-…` from `stack/NN-…` after `NN` is pushed.
5. Title `[NN/TT → <integration-base>] <type>: <summary>`.
6. Put `Stack` / `GitHub base` / `Depends on` on the first lines of the PR
   body (Cursor agents: **comment** later updates — `cursor-pr-body`).

## Boundaries

### Always Do

- Use `stack/NN-short-topic` and `[NN/TT → <base>]` for stacked work.
- Rebase `PR(N+1)` on `PR(N)` before opening.
- Merge `00` first, then each successor.

### Ask First

- Force-updating or rebasing an **existing** remote branch.
- Changing stack width `TT` after PRs are already open.

### Never Do

- Open stack PRs against the wrong integration base (periscope `main`).
- Use dated `yyyy-mm-dd-NNN-…` names **instead of** `stack/NN-…` for a stack.
- Duplicate a finding already on an earlier stack step.

## References

- [`../git-history-surgery/references/stacked-pr-naming-reference-card.md`](../git-history-surgery/references/stacked-pr-naming-reference-card.md)
- [`eval/stacked-pr-naming-checklist.md`](eval/stacked-pr-naming-checklist.md)
