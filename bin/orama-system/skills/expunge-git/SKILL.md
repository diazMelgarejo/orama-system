---
name: expunge-git
description: >
  Complete git-history scrub procedure for removing forbidden tokens, leaked
  secrets, or contaminated author identities from a repo's commits, branches,
  reflog, and packed objects. Invoke when: "expunge git history", "remove from
  history", "rewrite author", "scrub commits", "delete from reflog", "clean
  leaked secret from git", "remove forbidden token", "rewrite history",
  "purge identity string".
---

# Expunge Git History — End-to-End Scrub

> Real-time guidance. Git-hygiene doctrine: `docs/v2/22-worktree-parallel-agents.md`
> Branching context: `docs/wiki/08-git-hygiene-and-branching.md`
> Canonical skill source: `orama-system/bin/orama-system/skills/expunge-git/SKILL.md`

A naïve scrub leaves the bad string discoverable in **reflog**, **packed
objects**, and **stale remote-tracking refs**. The first attempt of this
procedure missed exactly those three places. The 15-step sequence below is the
one that actually worked end-to-end.

> **Prevention beats scrubbing.** The cheapest expunge is the one you never run.
> The pre-commit hygiene gate ([`docs/wiki/08` § Portable paths](../../../../docs/wiki/08-git-hygiene-and-branching.md#portable-paths-in-tracked-files-no-workstation-leaks))
> runs `repo_hygiene.py` and blocks workstation paths / leaked tokens *before*
> they reach history — so this scrub is the last resort, not the routine. This
> skill is itself **fail-closed**: prove it's safe to rewrite (Section 1) before
> destroying anything. See the [Fail-Closed Trust Boundary](../../../../docs/reference/multi-channel-steelman.md).

---

## Section 1 — When to Invoke / When NOT To

**Invoke when:**
- Solo or small-team repo (< ~5 active committers).
- A forbidden author identity, secret, or token landed in commit messages,
  authored-by lines, or file contents.
- All collaborators can be notified to re-clone within ~24 h.
- Rewriting history is acceptable (no signed-tag release dependencies, no
  external consumers pinned to specific SHAs).

**Do NOT invoke when:**
- Shared long-lived branch with many collaborators / open PRs.
  → Prefer `git revert` + **rotate the leaked secret** + add a redaction note.
- Released tags or downstream consumers depend on the contaminated SHAs.
  → Rotation + forward-fix is the only safe play.
- You cannot coordinate a force-push window.

⚠️ **Rewriting history does NOT un-leak a secret.** Anything that touched a
public remote MUST be rotated regardless of how clean the scrub is.

---

## Section 2 — Pre-flight

0. **Disable live Cursor co-author injection** before writing new commits during a scrub:

   ```bash
   bash scripts/git/apply-attribution-guard-all-repos.sh
   # or hook-free commits:
   bash scripts/git/commit-clean.sh -m "type(scope): summary"
   ```

   See `docs/wiki/12-cursor-cloud-commit-attribution.md`.

1. **Identify every contaminated commit and SHA.**

   ```bash
   git log --all --format="%H %s%n%b" | grep -i "<token>"
   git log --all --format="%H %an <%ae>" | grep -i "<token>"
   git rev-list --all --objects | git cat-file --batch-check --batch-all-objects \
     | awk '$2=="blob"{print $1}' \
     | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -q "<token>" && echo {}'
   ```

   Record the SHAs — you will verify against them in Section 4.

2. **Pick a strategy.**

   | Scenario | Strategy |
   |----------|----------|
   | Short contiguous range (≤ ~10 commits) | Anchor + cherry-pick — best traceability |
   | Many commits, scattered, or all-history scrub | `git filter-repo` |
   | Secret in a single blob, message clean | `git filter-repo --replace-text` |

3. **Ensure no in-flight work.**
   - All collaborators have pushed or stashed.
   - No open auto-merge PRs targeting the affected branch.
   - You hold a fresh `git fetch --all --prune` snapshot.

4. **Tag the pre-scrub tip** in case rollback is needed:

   ```bash
   git tag pre-expunge-backup-$(date +%Y%m%d-%H%M%S) <current-tip-sha>
   ```

---

## Section 3 — The 15-Step Sequence

Use placeholders throughout — never paste the real forbidden string into shell
history, PR titles, or commit messages.

### 1. Re-confirm all contaminated commits

```bash
git log --all --format="%H %s%n%b" | grep -i "<token>"
```

### 2. Choose rewrite strategy

Anchor + cherry-pick for short ranges (preferred). `git filter-repo` for many
commits or all-history scrubs.

### 3. Create clean branch from the anchor and replay

```bash
git checkout -b <clean-branch> <last-known-good-sha>
git cherry-pick <good-sha-1> <good-sha-2> ...
# Or, for many commits:
# git filter-repo --message-callback 'return message.replace(b"<token>", b"")'
```

### 4. Force-push the clean branch

```bash
git push --force-with-lease origin <clean-branch>
```

### 5. Open the PR with a sanitized title and body

⚠️ **Never reproduce `<token>` verbatim** in the PR title, body, or commit
messages. Refer to it as "the forbidden identity string" or similar.

### 6. After merge: force-push main to the new tip

```bash
git checkout main
git reset --hard <merged-clean-tip-sha>
git push --force-with-lease origin main
```

### 7. Delete contaminated remote branches

```bash
gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>
# Repeat for every contaminated branch.
```

### 8. ⚠️ Prune local remote-tracking refs (CRITICAL — easy to forget)

```bash
git remote prune origin
```

Without this, `origin/<branch>` still points at the bad object on your disk.

### 9. Hunt local refs still pointing at contaminated objects

```bash
git for-each-ref --format='%(refname) %(objectname)' | grep "<bad-sha>"
# For each ref printed:
git update-ref -d <ref>
```

### 10. ⚠️ Expire all reflog entries (CRITICAL — default retention is 90 days)

```bash
git reflog expire --expire=now --all
```

The reflog is the single most common reason a "clean" repo still contains the
bad SHA.

### 11. Physically remove unreachable objects

```bash
git repack -Ad --unpack-unreachable=now
git prune --expire=now
# Equivalent heavyweight alternative:
# git gc --prune=now --aggressive
```

### 12. Verify message scrub

```bash
git log --all --format="%B" | grep -i "<token>"   # must print nothing
```

### 13. Verify blob scrub

```bash
git rev-list --all --objects \
  | git cat-file --batch-check --batch-all-objects \
  | awk '$2=="blob"{print $1}' \
  | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -l "<token>"'
# Must print nothing.
```

### 14. Verify reflog is drained

```bash
git reflog --all | wc -l   # should be ~0 (just the new HEAD entry)
```

### 15. Notify collaborators

- Announce the force-push window has happened.
- Require **fresh clones**, not `git pull` — pull will resurrect bad objects.
- If a secret leaked: confirm rotation already completed, and document the
  rotation in an internal incident note.

---

## Section 4 — Verification Checklist

Run all three. Each must return empty / near-zero.

```bash
# 1. No bad string in any reachable commit message.
git log --all --format="%B" | grep -i "<token>"

# 2. No bad string in any reachable blob.
git rev-list --all --objects \
  | git cat-file --batch-check --batch-all-objects \
  | awk '$2=="blob"{print $1}' \
  | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -l "<token>"'

# 3. Reflog drained.
git reflog --all | wc -l
```

If any of the three is non-empty, **go back to Step 10–11**. The most common
cause is skipping `git remote prune origin` or `git reflog expire --all`.

---

## Section 5 — Coordinating With Collaborators

| Step | Who | Channel |
|------|-----|---------|
| Pre-flight notice ("force-push window opening") | You | Team chat |
| Force-push complete | You | Team chat with new main SHA |
| Fresh-clone instructions | You | Pin in chat |
| Secret rotation status (if applicable) | Secret owner | Incident channel |

**Fresh-clone instructions to send:**

```bash
# Do NOT git pull — it will resurrect contaminated objects from local reflog.
cd ..
rm -rf <repo>     # back up any unpushed work first
git clone git@github.com:<owner>/<repo>.git
```

⚠️ **Rotate any leaked secret** even after a clean scrub. History rewrites do
not retroactively revoke credentials that were ever pushed to a remote.

---

## Section 6 — Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Forgot `git reflog expire --expire=now --all` | `git rev-list --all` is clean, but `git log -g` still shows `<bad-sha>` | Run Step 10, then Step 11 |
| Forgot `git remote prune origin` | `git branch -ra` still lists `origin/<contaminated-branch>` | Run Step 8 |
| Skipped Step 9 (local refs) | A stale tag or PR ref keeps the bad object reachable, so `git prune` does nothing | Run Step 9 then Step 11 |
| Pasted `<token>` verbatim into PR title | Forbidden string returns via GitHub's commit API | Edit PR, force-push again, reopen |
| Used `git pull` after the rewrite | Contaminated objects resurrected from local reflog | Delete clone, re-clone fresh |
| Used `git filter-branch` instead of `git filter-repo` | Slow, error-prone, deprecated | Use `git filter-repo` |
| Skipped secret rotation because "history is clean" | Secret already on someone's laptop / in CI logs / in GitHub's archive | Rotate. Always. |

---

## Section 7 — References

- `docs/v2/22-worktree-parallel-agents.md` — git hygiene context, lock-file
  rules, orphan-ref handling. Parallel-agent setups multiply the risk that a
  stale ref or unpushed worktree resurrects the bad object.
- `docs/wiki/08-git-hygiene-and-branching.md` — branch lifecycle, naming, and
  the broader hygiene story this skill plugs into.
- `scripts/review/repo_hygiene.py` — pre-commit scanner that catches forbidden
  tokens, personal paths, bidi controls, and legacy names. Run before every
  commit during a scrub.

---

## Scope

Applies to: any repo on the orama-system stack.
Does not modify external archives (e.g., GitHub's REST archive, third-party
mirrors, package registries) — those require separate takedown requests.
