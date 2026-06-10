---
name: git-history-surgery
description: >
  End-to-end git history surgery for the orama-system stack: scrub contaminated
  history, force-push safely, and recover/re-anchor branches after a rewrite using
  byte-identical tree twins. Invoke when: "expunge git history", "remove secret
  from history", "rewrite author", "scrub commits", "branches are 600 behind",
  "orphaned branch after rewrite", "re-anchor branch to main", "branches lost
  common ancestor", "recover deleted branch", "git history rewrite recovery",
  "byte-identical common ancestor", or "branches all became the same".
---

# Git History Surgery

One source of truth for dangerous git history operations. This skill replaces the
former split between separate rewrite-scrub and branch-recovery skills.

Use it for two related jobs:

| Situation | Procedure |
|---|---|
| A secret, forbidden identity, token, or workstation path landed in history | [`references/expunge-contaminated-history.md`](references/expunge-contaminated-history.md) |
| `main` was rewritten and branches look 600 commits behind/orphaned | [`references/reanchor-after-rewrite.md`](references/reanchor-after-rewrite.md) |

Fail closed: preserve refs, prove the operation is necessary, and use
`--force-with-lease` only after recording the expected remote SHA.

## Windows PowerShell Bootstrap

Before any `fetch`, `rebase`, `push`, scrub, or local verification on the Windows
LM Studio host, run
[`references/windows-powershell-runtime-bootstrap.md`](references/windows-powershell-runtime-bootstrap.md).

## Decision Flow

1. Is there a leaked secret/identity/path in committed history?
   Use the expunge reference, rotate any secret, and require fresh clones.
2. Did a rewrite already happen and branches now look impossible to reason about?
   Use the re-anchor reference and tree-twin scan. Do not trust ahead/behind counts.
3. Is this only a normal bad commit?
   Do not perform history surgery. Use a normal PR or revert.

## Non-Negotiables

- Never paste the real forbidden token into PR titles, commit messages, issue
  comments, shell history, or docs. Use placeholders.
- Never force-push without a recorded lease target.
- Never judge rewritten branches by `merge-base`, `rev-list --count`, or GitHub
  ahead/behind alone.
- Never flatten branches to `origin/main` unless the user explicitly asks to
  destroy their distinct branch identity.
- Never treat a clean git rewrite as secret remediation. Rotation is separate.

## Verification

After any history surgery:

```bash
python scripts/review/repo_hygiene.py .
bash scripts/git/reanchor_scan.sh <repo> origin/main [heads|remotes|all]
git log --all --format="%B" | grep -i "<token>"   # must print nothing
git reflog --all | wc -l                          # should be near-zero after scrub
```

For PR branch cleanup without contamination, rebase or merge normally; do not use
this skill unless history was rewritten or contaminated.

## References

- [`references/expunge-contaminated-history.md`](references/expunge-contaminated-history.md)
- [`references/reanchor-after-rewrite.md`](references/reanchor-after-rewrite.md)
- [`references/windows-powershell-runtime-bootstrap.md`](references/windows-powershell-runtime-bootstrap.md)
- [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../docs/wiki/08-git-hygiene-and-branching.md)
- [`docs/wiki/13-alphaclaw-fork-contrib-branches.md`](../../../../docs/wiki/13-alphaclaw-fork-contrib-branches.md)
- [`scripts/git/reanchor_scan.sh`](../../../../scripts/git/reanchor_scan.sh)
