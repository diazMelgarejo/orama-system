# Stash Hooks Safeguard — Git Reference Card

> **Thin pointer:** canonical copy lives in
> [`git-history-surgery/references/stash-hooks-safeguard-reference-card.md`](../../git-history-surgery/references/stash-hooks-safeguard-reference-card.md).
> Read that file before any `git stash pop` or `git stash apply`.

**Rule:** `git -c core.hooksPath=/dev/null stash pop` → `bash scripts/git/install-local-hooks.sh`. Never bare `git stash pop`.
