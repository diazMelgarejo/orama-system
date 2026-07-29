## Cursor Cloud: git commits

Run on cloud VM boot:

```bash
bash scripts/git/apply-attribution-guard-all-repos.sh
```

### Mandatory commit sequence (never skip or reorder)

`commit-clean.sh` writes **only the staged index**. It never runs `git add`.
Unstaged edits stay in the working tree and are **not** included in the commit.
If you have unstaged changes and an empty index, the old script created an
empty commit (message-only, zero file delta). The guards below block that.

```bash
# 1. Stage every path that belongs in this commit (REQUIRED)
git add <paths>   # or git add -A when the whole tree is intentional

# 2. Verify the index has a real delta vs HEAD (REQUIRED)
bash scripts/git/verify-staged-for-commit.sh
# Must print "OK — staged changes" and a non-empty git diff --cached --stat

# 3. Hook-free commit (REQUIRED last step)
bash scripts/git/commit-clean.sh -m "type(scope): summary"

# Optional: preview without updating the branch
bash scripts/git/commit-clean.sh --dry-run -m "type(scope): summary"
```

Before pushing, confirm the commit actually contains your files:

```bash
git show --stat --oneline HEAD
```

See orama-system `docs/wiki/12-cursor-cloud-commit-attribution.md` (canonical).
