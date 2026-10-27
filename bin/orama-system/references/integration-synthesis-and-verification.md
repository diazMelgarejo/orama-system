# Integration, Synthesis and Live-Code Verification

> Three permanent operator rules for resuming, merging and reporting work that more
> than one agent touched, plus the operational corollaries that keep them safe.

## When it applies

Load this card whenever you resume stopped or partial work, integrate parallel work
(agents, branches, PRs), merge or reconcile two solutions to one problem, or act on
any report (subagent, bot, peer or your own) before something is pushed.

## Rule 1 - Leftover reuse

When resuming or integrating after stopped, partial or parallel work, ingest **all**
leftovers: partial patches, stashes, aborted merges, prior verifier notes and other
agents' commits. Reuse what adds value. Always report what was reused or rejected,
and why.

Rationale: leftovers hold paid-for work and hard-won findings. Starting clean
silently discards them; adopting them blindly imports their defects. The report is
what makes either choice auditable.

## Rule 2 - Synthesis

When two sides (agents, branches, PRs) solved the same problem, never pick one side
wholesale. Keep the stronger guarantee from each side, remove duplicate mechanisms,
and choose the simplest combined design. Record each decision as a row of the
decision record in the report template below.

Rationale: each side usually hardens a different failure mode. Picking a winner
drops the other side's guarantee; stacking both leaves two mechanisms doing one job.
The combined design must be at least as strict as the stricter side on every concern
and carry no duplicate mechanism.

## Rule 3 - Live-code verification

Check every report (subagent, bot, peer or your own) against the live code, both
`origin` and local, before anything is pushed. A report is a claim, not evidence:
re-read the files, re-run the check, and compare the origin tip with the local tip.

Rationale: reports go stale the moment another agent commits, and the author of a
report cannot see what changed after it was written.

## Report template

```markdown
### Integration report

**Inputs:** <branches / PRs / agents / SHAs, origin and local tips>

**Leftovers ingested**

| Item (patch, stash tag, merge, note, commit) | Reused / Rejected | Why |
|----------------------------------------------|-------------------|-----|

**Synthesis decisions**

| Concern | Side A | Side B | Combined | Why at least as strict | Where (path:line) |
|---------|--------|--------|----------|------------------------|-------------------|

**Live-code verification:** <each report claim, the file or command that confirmed
or refuted it, origin vs local result>

**Provenance:** <takeover disclosure, original author, current actor>
```

## Corollaries

- **Merge, never rewrite others' work.** Integrate another branch (a base into a
  stacked PR, another agent's branch) by merge commit only. Never rebase other
  agents' commits and never force-push over them. When the same shared branch
  advances under your unpushed delta, follow
  [concurrent-head reapply](concurrent-head-reapply.md) instead of a catch-up merge.
- **Disclose takeover first.** Before acting on another agent's work, state that you
  are taking it over; see the
  [cross-agent provenance invariant](cross-agent-provenance-invariant.md).
- **Stash with a unique tag, never pop shared stashes.** Preserve partial work with
  `git stash push -u -m "<unique-tag>"` instead of discarding it. The stash stack is
  shared across worktrees, so capture your entry's SHA, restore with
  `git stash apply <sha>`, and never `git stash pop`.
- **Short scratch worktree paths on Windows.** Use short paths (for example
  `worktrees/m-d0-x`) and `git -c core.longpaths=true worktree add ...`.

## Links

- [Multi-agent collaboration protocol](multi-agent-collaboration-protocol.md)
- [Cross-agent provenance invariant](cross-agent-provenance-invariant.md)
- [Concurrent-head reapply](concurrent-head-reapply.md)
- [Worktree semantic merge card](worktree-semantic-merge-reference-card.md)
- [Markdown editing rule](markdown-editing-rule.md)
