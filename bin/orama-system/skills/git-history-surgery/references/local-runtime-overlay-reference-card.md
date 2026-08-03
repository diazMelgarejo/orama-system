# Local Runtime Overlay — Git Reference Card

> **Thin pointer:** canonical copy lives in
> [`using-git-worktrees/references/local-runtime-overlay-reference-card.md`](../../using-git-worktrees/references/local-runtime-overlay-reference-card.md).
> Read that file before stash/pull/integrity work on Perpetua-Tools.

**Quick rules:** never `git checkout` overlay paths; never commit LAN values; stash
`config/devices.yml` and `config/models.yml` before pull/rebase when needed; optional
`git update-index --skip-worktree` per clone.

**Package policy:** [`config/LOCAL-RUNTIME-OVERLAY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/LOCAL-RUNTIME-OVERLAY.md)
