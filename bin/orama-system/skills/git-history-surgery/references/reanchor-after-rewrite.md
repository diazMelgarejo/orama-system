# Re-Anchor Branches After a Rewrite

When `main` is rewritten, every pre-rewrite commit keeps its content but gets a
new SHA. Branches built on the old SHAs may look 600 commits behind even though
their content is fine or already in `main`.

## Wrong fixes

- Flattening every branch to `origin/main` destroys branch identity.
- `git replace --graft` works only locally and never fixes GitHub's branch view.
- `merge-base != root` is not proof that a rewritten branch is healthy.

## Correct fix

Find the byte-identical tree twin in rewritten `main` and re-anchor the branch to
that real in-main commit. If the branch tip has no exact twin, walk first-parent
history to the deepest twin ancestor and replay only the commits above it.

Invariant: `merge-base(branch, origin/main)` must be a real recent commit in
`origin/main`, ideally the branch's twin.

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

## Do not confuse re-anchor with content merge

Re-anchoring moves the branch ref so the graph is clean. It does not merge branch
content into `main`. If `main` is the canonical/evolved tree, merging old branch
content back may regress it. Re-anchor for graph recovery; merge only reviewed,
forward-moving work.
