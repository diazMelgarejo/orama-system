# Expunge Contaminated History

A naive scrub leaves the bad string discoverable in reflog, packed objects, and
stale remote-tracking refs. Use this only when prevention failed and the
contaminated object already landed.

## When to invoke

Invoke when:
- A forbidden identity, secret, token, or workstation path landed in commit
  messages, authored-by lines, or file contents.
- A coordinated force-push window is acceptable.
- All collaborators can be notified to re-clone within about 24 hours.

Do not invoke when:
- A shared long-lived branch has many collaborators or release consumers.
- Rotation plus a forward fix is sufficient.
- You cannot coordinate a force-push window.

Warning: rewriting history does not un-leak a secret. Rotate any secret that ever
touched a public remote.

## Pre-flight

0. On Windows, run the runtime bootstrap in
   `../using-git-worktrees/SKILL.md#windows-powershell-runtime-bootstrap`.

1. Disable live Cursor co-author injection before writing new commits:

   ```bash
   bash scripts/git/apply-attribution-guard-all-repos.sh
   # or hook-free commits:
   bash scripts/git/commit-clean.sh -m "type(scope): summary"
   ```

2. Identify every contaminated commit and SHA:

   ```bash
   git log --all --format="%H %s%n%b" | grep -i "<token>"
   git log --all --format="%H %an <%ae>" | grep -i "<token>"
   git rev-list --all --objects | git cat-file --batch-check --batch-all-objects \
     | awk '$2=="blob"{print $1}' \
     | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -q "<token>" && echo {}'
   ```

3. Choose a strategy:

   | Scenario | Strategy |
   |---|---|
   | Short contiguous range, about 10 commits or fewer | Anchor + cherry-pick |
   | Many commits, scattered, or all-history scrub | `git filter-repo` |
   | Secret in a single blob, message clean | `git filter-repo --replace-text` |

4. Ensure no in-flight work and tag the pre-scrub tip:

   ```bash
   git fetch --all --prune
   git tag pre-expunge-backup-$(date +%Y%m%d-%H%M%S) <current-tip-sha>
   ```

## Scrub sequence

Use placeholders throughout. Never paste the real forbidden string into PR
titles, bodies, commit messages, or shell history.

1. Re-confirm contaminated commits:

   ```bash
   git log --all --format="%H %s%n%b" | grep -i "<token>"
   ```

2. Create a clean branch and replay safe commits:

   ```bash
   git checkout -b <clean-branch> <last-known-good-sha>
   git cherry-pick <good-sha-1> <good-sha-2>
   # Or, for broad scrubs:
   # git filter-repo --message-callback 'return message.replace(b"<token>", b"")'
   ```

3. Push with a lease:

   ```bash
   git push --force-with-lease origin <clean-branch>
   ```

4. Open the PR with sanitized language only.

5. After merge, move `main` to the clean tip:

   ```bash
   git checkout main
   git reset --hard <merged-clean-tip-sha>
   git push --force-with-lease origin main
   ```

6. Delete contaminated remote branches:

   ```bash
   gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>
   ```

7. Prune local remote-tracking refs:

   ```bash
   git remote prune origin
   ```

8. Delete local refs still pointing at contaminated objects:

   ```bash
   git for-each-ref --format='%(refname) %(objectname)' | grep "<bad-sha>"
   git update-ref -d <ref>
   ```

9. Expire all reflogs:

   ```bash
   git reflog expire --expire=now --all
   ```

10. Remove unreachable objects:

   ```bash
   git repack -Ad --unpack-unreachable=now
   git prune --expire=now
   ```

11. Verify commit messages:

   ```bash
   git log --all --format="%B" | grep -i "<token>"
   ```

12. Verify blobs:

   ```bash
   git rev-list --all --objects \
     | git cat-file --batch-check --batch-all-objects \
     | awk '$2=="blob"{print $1}' \
     | xargs -I{} sh -c 'git cat-file -p {} 2>/dev/null | grep -l "<token>"'
   ```

13. Verify reflog is drained:

   ```bash
   git reflog --all | wc -l
   ```

14. Notify collaborators: force-push complete, fresh clone required, do not
    `git pull`.

15. Confirm secret rotation, if applicable.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Forgot `git reflog expire --expire=now --all` | Reachable commits are clean but `git log -g` still shows bad SHAs | Expire reflogs, then prune |
| Forgot `git remote prune origin` | `git branch -ra` still lists contaminated refs | Prune remotes, then delete local refs |
| Used `git pull` after rewrite | Bad objects resurrect locally | Fresh clone |
| Skipped secret rotation | Secret remains valid outside git | Rotate immediately |
