# Re-Anchor Branches After a Rewrite

When `main` is rewritten, every pre-rewrite commit keeps its content but gets a
new SHA. Branches built on the old SHAs may look 600 commits behind even though
their content is fine or already in `main`.

Large ahead/behind numbers after a scrub or metadata rewrite are graph symptoms,
not semantic-diff proof. A branch that appears hundreds of commits ahead may
only need to be attached to the matching tree in rewritten `main`, then have the
small set of commits above that anchor replayed.

## Wrong fixes

- Flattening every branch to `origin/main` destroys branch identity.
- `git replace --graft` works only locally and never fixes GitHub's branch view.
- `merge-base != root` is not proof that a rewritten branch is healthy.
- Blindly merging rewritten `main` into the stale branch can resurrect the old
  graph as synthetic conflicts and merge-artifact commits.

## Correct fix

Find the byte-identical tree twin in rewritten `main` and re-anchor the branch to
that real in-main commit. If the branch tip has no exact twin, walk first-parent
history to the deepest twin ancestor and replay only the commits above it. Skip
branch-side merge-artifact commits unless inspection proves they contain unique
semantic content.

Invariant: `merge-base(branch, origin/main)` must be a real recent commit in
`origin/main`, ideally the branch's twin.

## ALWAYS check your own main before syncing it — safe-behind vs needs-reanchor

This applies to `main` itself, not just feature branches — including your own
local `main`, a peer's `main` in a mirrored repo, or any "default branch" you
are about to fast-forward, merge, or reset after a rewrite happened upstream.
Never sync blindly just because `main` shows large ahead/behind numbers or
"N commits behind." Classify first:

- **SAFE-BEHIND** — every commit unique to local `main` already exists
  somewhere in `origin/main`'s rewritten history, either as an exact tree
  twin or under a different SHA carrying the same content. Fast-forward or
  reset is safe: nothing local is lost.
- **NEEDS-REANCHOR** — at least one commit's content does not appear
  anywhere in `origin/main`, by tree twin or by content cross-check. Treat
  it like any other stale branch in this document: find the twin ancestor,
  replay only the genuinely unique commits above it. Do not fast-forward or
  reset past it — that would silently discard real local work.

`git cherry -v origin/main main` alone is not proof of either outcome. Its
`-`/`+` split is patch-ID based:

```bash
git fetch origin
git cherry -v origin/main main > /tmp/cherry.txt
awk '/^\+/{print $2}' /tmp/cherry.txt   # candidates that still need verification
```

A `+` result is **not** proof of unique work — only proof that patch-ID
comparison didn't find an exact match. A rewrite (squash, `filter-repo`,
metadata scrub) changes exact diff bytes without changing the underlying
change, so a commit that already landed upstream under a different SHA still
shows as `+`. Before concluding a `+` candidate is genuinely unique, cross-check
by commit message against the rewritten history:

```bash
git log -1 --format=%s <candidate-sha>
git log origin/main --grep="<that message>" --format='%H %s'
```

A message match under a different SHA means the content is already upstream
— SAFE-BEHIND for that commit. This is the same rewrite-artifact SHA mismatch
described in "Detection: use tree twins, not graph merge-base" below, reached
by message search instead of tree-hash search — useful when a rewrite also
touched blobs, so no exact tree twin exists even though the change is present.

Only commits with no tree twin AND no message match anywhere in `origin/main`
are genuinely unique local work. Those, and only those, justify the re-anchor
procedure in this document. A large ahead/behind count or a bare `+` count is
never sufficient grounds by itself to run `git merge origin/main` or
`git reset --hard origin/main` on `main`.

**Do not stop at the message-match check either.** A message match proves a
same-titled commit exists somewhere upstream; it does not prove that commit's
*content* is what actually landed. Always confirm against the real merged
head, not an assumed one — `gh pr view <N> --json headRefOid` for a merged PR,
not the local branch tip you happen to have checked out. A prior
conflict-resolution or reanchor pass reporting "safe" or "aligned" is a claim
about intent, not proof about the resulting tree. Diff the local tip against
the actual `headRefOid` (`git diff --stat <local-tip> <real-merged-head>`)
before trusting either verdict — see `docs/LESSONS.md` § 2026-08-08 for a case
where this exact gap silently dropped ~660 lines (a pre-commit gate script,
its wiring, a 439-line reference card, and three skills' pilot content) that
a `cherry -v` + message-match pass alone had already marked resolved.

## Pre-flight

```bash
cd <repo>
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'
git for-each-ref refs/remotes/origin/pr/
git ls-remote --heads origin
git tag backup/pre-reanchor-$(date +%Y%m%d-%H%M%S) main
```

Never force-push a branch whose tip is not preserved in the PR vault, a tag, or
a closed PR.

## Build the twin index

```bash
git log origin/main --format='%H %T' > /tmp/main_trees.txt
```

`%T` is the commit tree id. Two commits with the same `%T` are byte-identical in
content, regardless of SHA, author, or message.

## Case A: branch tip has an exact twin

```bash
tip=$(git rev-parse <branch-or-vault-ref>)
t=$(git rev-parse "${tip}^{tree}")
twin=$(awk -v t="$t" '$2==t{print $1; exit}' /tmp/main_trees.txt)
git push --force-with-lease="<branch>:<recorded-old-sha>" origin "${twin}:refs/heads/<branch>"
git merge-base --is-ancestor "$twin" origin/main && echo "ancestor-of-main ok"
```

The branch shows `+0/-N` against main: contained, distinct tip per branch.

## Case B: no exact tip twin

Walk first-parent history to the deepest ancestor that has a twin, then graft the
commits above it onto that twin:

```bash
for c in $(git rev-list --first-parent "$tip"); do
  t=$(git rev-parse "${c}^{tree}")
  twin=$(awk -v t="$t" '$2==t{print $1; exit}' /tmp/main_trees.txt)
  [ -n "$twin" ] && { echo "base=$c twin=$twin"; break; }
done

git checkout -B __reanchor "$tip"
git clean -fdq
git rebase --onto "$twin" "$base"
test "$(git merge-base HEAD origin/main)" = "$(git rev-parse "$twin")" && \
  git push --force-with-lease="<branch>:<recorded-old-sha>" origin HEAD:refs/heads/<branch>
git checkout -
git branch -D __reanchor
```

Untracked/generated files can block replay. If rebase says local changes would
be overwritten, run `git clean -fdq` after confirming no useful untracked files.

### Case C: scrub changed blobs, so no exact twin exists

If a scrub rewrote file contents, line endings, file modes, or generated memory
artifacts, a pre-scrub commit may have no byte-identical tree twin. That is not
the same as "safe to merge normally." It means tree-twin re-anchor can only
prove ancestry up to the nearest unchanged tree.

When no twin is found:

1. Preserve the old remote SHA, PR head, or a local backup tag.
2. Diff the stale branch against the closest reviewed base and classify each
   changed path as semantic work, scrub-only rewrite, generated artifact, or
   stale merge artifact.
3. Replay semantic work onto current `origin/main` in a clean worktree.
4. Regenerate derived files from sources of truth, especially rendered memory
   markdown from structured JSONL.
5. Verify both graph health and scrub scope before force-with-lease.

Do not call this a tree-twin proof. Call it a reviewed replay after a blob-level
rewrite.

## Detection: use tree twins, not graph merge-base

```bash
MAIN=$(git rev-parse origin/main)
git log "$MAIN" --format='%H %T' > /tmp/main_trees.txt

for b in <branches>; do
  tip=$(git rev-parse origin/$b)
  C=""; DT=""; above=0
  for c in $(git rev-list --first-parent "$tip"); do
    m=$(awk -v t="$(git rev-parse ${c}^{tree})" '$2==t{print $1;exit}' /tmp/main_trees.txt)
    [ -n "$m" ] && { C="$c"; DT="$m"; break; }
    above=$((above+1))
  done
  if [ -z "$DT" ]; then
    echo "$b NO-TWIN (truly disjoint; investigate)"
  elif [ "$C" = "$(git rev-parse origin/$b)" ] && git merge-base --is-ancestor "$DT" "$MAIN"; then
    echo "$b already-anchored (tip is in-main commit ${DT:0:9})"
  else
    echo "$b NEEDS-REANCHOR: graft $above commit(s) onto twin ${DT:0:9}"
  fi
done
```

Pass means every branch is either already an in-main ancestor or has been grafted
onto its twin.

## PR branch replay checklist

Use this when an active PR branch shows huge ahead/behind after scrub work:

1. `git ls-remote` the PR branch and record the exact lease SHA.
2. Build the `origin/main` tree index.
3. Find the deepest first-parent tree twin.
4. Create a disposable worktree from current `origin/main`.
5. Cherry-pick or replay only non-merge commits above the twin, oldest first.
6. Resolve append-only memory by union and dedup (`id` / `run_id`); rerender
   derived markdown instead of hand-merging it.
7. Run repo hygiene, targeted tests, exact conflict-marker scans, and
   forbidden-token current-tree/metadata scans.
8. Confirm `merge-base HEAD origin/main` equals current `origin/main` and the
   branch is only the intended semantic commits ahead.
9. Force-with-lease from the recorded SHA. If the lease moved, stop and restart
   from the new remote tip.

## Clean replacement instead of re-anchor

Sometimes re-anchoring is the wrong objective. If the PR's final tree is the
valuable artifact and the branch history itself contains contaminated blobs,
failed replay attempts, or repeated conflict churn, prefer a clean replacement
PR over preserving the old PR branch.

Use this option when all of these are true:

- the old PR tip is preserved by a tag, remote ref, PR vault, or closed PR;
- the desired final tree can be checked out onto current `origin/main`;
- reviewers care about the resulting content more than the old commit-by-commit
  story;
- PR-unique blob scans are expected to pass only after the intervening commits
  are removed from the replacement branch.

Proof checklist:

1. Save `origin/main...origin/<old-pr-branch>` patch/stat/name-status before
   changing anything.
2. Create `<replacement-branch>` from current `origin/main`.
3. `git checkout <preserved-old-tip> -- .` to replay the final tree.
4. Scrub current tracked files using local-only forbidden-pattern sources.
5. Commit the clean replay once.
6. Verify `git diff --quiet <preserved-old-tip> HEAD` when exact final-tree
   preservation is intended.
7. Verify `origin/main..HEAD` has zero forbidden-label blob hits; inherited
   `origin/main` hits are reported separately.
8. Push the replacement branch, open a new PR, then close the old PR with a
   sanitized audit note.

Do not call this a re-anchor. It is a reviewed clean-lineage content replay.
Its purpose is to remove the intervening commits that created the mess while
keeping the final content available for review.

## Do not confuse re-anchor with content merge

Re-anchoring moves the branch ref so the graph is clean. It does not merge branch
content into `main`. If `main` is the canonical/evolved tree, merging old branch
content back may regress it. Re-anchor for graph recovery; merge only reviewed,
forward-moving work.

## Do not confuse re-anchor with scrub completion

Re-anchor proves the branch graph is attached to rewritten `main`. It does not
prove contaminated file blobs disappeared from every reachable ref.

Use precise status language:

- Metadata/message scrub complete: author, committer, and commit-message surfaces
  passed their scans.
- Current-tree sanitization complete: tracked files at the new tip passed the
  local forbidden-pattern scan.
- PR re-anchor complete: merge-base is current `origin/main` and the PR is only
  the intended semantic commits ahead.
- All-ref blob scrub complete: every reachable blob across all refs was scanned
  with local-only forbidden patterns and produced zero hits.

If the all-ref scan timed out, was skipped, or found hits, keep the gap explicit.
Never summarize that state as history-wide removal.
