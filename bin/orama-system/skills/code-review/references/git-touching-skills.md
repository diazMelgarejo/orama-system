# Git-touching skills this one composes with

> **Owner:** code-review skill
> **Last updated:** 2026-08-07

Fixes found during review often need one of these to land safely.

- [`../../git-history-surgery/SKILL.md`](../../git-history-surgery/SKILL.md) — dangerous git ops:
  history scrub, tree-twin re-anchor, patch-equivalence rebase recovery
  (§ Decision 13), multi-agent branch merge protocol
- [`../../using-git-worktrees/SKILL.md`](../../using-git-worktrees/SKILL.md) — parallel-agent
  worktree lifecycle; the clean-branch-per-contribution pattern in
  [`upstream-contribution-discipline.md`](upstream-contribution-discipline.md) uses this directly
- [`../../cursor-agent/SKILL.md`](../../cursor-agent/SKILL.md) — fan-out dispatch + § Fan-out
  Safety (file-disjoint clustering, verify self-reports, concurrent-job races)
- [`../../fable5-git-rebase-safety/SKILL.md`](../../fable5-git-rebase-safety/SKILL.md) — per-file/
  per-commit triage (patch-id matching, structural supersession) before
  deciding what to reanchor, discard, or replay
- [`../../git-pending-push-guard/SKILL.md`](../../git-pending-push-guard/SKILL.md) — guard against
  pushing with an unresolved merge/cherry-pick/revert in progress
- [`../../cursor-pr-body/SKILL.md`](../../cursor-pr-body/SKILL.md) — PR body append discipline
  (comment-only by default; operator-grant-gated body edits)
