# Fresh-Main Integrity Diff (CLAYGO) — Git Reference Card

> **Thin pointer:** canonical copy lives in
> [`using-git-worktrees/references/fresh-main-integrity-diff-claygo.md`](../../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md).
> Read that file before running the protocol.

**Invoke from this skill when:** stale branch salvage, post-merge integrity audit,
"what is truly unique on this branch vs current `main`?", clean replacement PR
extraction after merge-noise branches, or **path-scoped replay onto a fresh
integration base** (see
[`path-scoped-pr-replay-reference-card.md`](path-scoped-pr-replay-reference-card.md)).

**CLAYGO:** clean last run's ephemeral clone/worktree **before** starting and **after**
finishing every integrity pass.

**Pair with:** [`local-runtime-overlay-reference-card.md`](../../using-git-worktrees/references/local-runtime-overlay-reference-card.md)
when the repo is Perpetua-Tools — never treat `config/devices.yml` / `config/models.yml`
working-tree drift as corruption.
