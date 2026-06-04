---
name: git-reanchor
description: >
  Recover branches that look "orphaned" or "600 commits behind" after a force-pushed /
  rewritten main, by re-anchoring each onto the byte-identical twin commit that already
  exists in the rewritten history. Invoke when: "branches are 600 behind", "orphaned
  branch after rewrite", "re-anchor branch to main", "branches lost common ancestor",
  "reconcile branches after force-push", "recover deleted branch", "byte-identical
  common ancestor", "git history rewrite recovery", "branches all became the same".
---

# Git Re-Anchor — Recover Orphaned Branches After a History Rewrite

> Companion to [`expunge-git`](../expunge-git/SKILL.md) (the rewrite) and the AlphaClaw
> fork invariant in [`docs/wiki/13-alphaclaw-fork-contrib-branches.md`](../../../../docs/wiki/13-alphaclaw-fork-contrib-branches.md)
> (`merge-base(branch, origin/main) == origin/main`). Git-hygiene context:
> [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../docs/wiki/08-git-hygiene-and-branching.md).
> First applied end-to-end on orama-system 2026-06-04 (the PR #70 rewrite incident).

## Section 1 — The problem this solves

When `main` is **rewritten** (squash-rebundle, `filter-repo`, expunge, force-push), every
pre-rewrite commit keeps its content but gets a **new SHA**. Branches built on the old
SHAs now share only the *root* with new main, so they show as **"600 commits behind"**
or "orphaned" — even though their work is fine and often already in main.

**Two wrong fixes (do NOT do these):**
- **Flatten** — resetting every branch to `origin/main`. Makes all branches *identical*
  to HEAD; destroys their distinct identity. (This was the first mistaken attempt.)
- **`git replace --graft`** — surgically re-parents locally, but replace-refs are
  **local-only** and never show on GitHub, so the remote branch view stays broken.

**The right fix:** every pre-rewrite commit has a **byte-identical twin** (same tree, new
SHA) somewhere in the rewritten `main`. Re-anchor each branch onto its twin, which is a
real ancestor of `main`. Result: the branch shares a recent common ancestor with main,
stays distinct, and shows only its true delta — never orphaned, never flattened.

**Invariant to satisfy (from wiki/13):** `merge-base(branch, origin/main)` is a real,
recent commit in `origin/main` — ideally the branch's twin, else the deepest twin ancestor.

## Section 2 — Pre-flight (fail-closed; preserve before you push)

```bash
cd <repo>
# 1. Recover EVERY tip first (PR heads survive branch deletion):
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'
git for-each-ref refs/remotes/origin/pr/        # the vault — your backup
# 2. Record current remote SHAs of the branches you will move (lease + rollback):
git ls-remote --heads origin
# 3. Tag local main before any local reset:
git tag backup/pre-reanchor-$(date +%Y%m%d-%H%M%S) main
```

Never force-push a branch whose tip is not preserved in the vault, a tag, or a closed PR.

## Section 3 — Build the twin index (once)

```bash
git log origin/main --format='%H %T' > /tmp/main_trees.txt   # SHA + tree per commit
```

`%T` is the commit's tree id. Two commits with the same `%T` are **byte-identical** in
content (the whole tree matches), regardless of SHA, author, or message.

## Section 4 — Re-anchor each branch

### Case A — branch tip has an exact twin (most common)

```bash
tip=$(git rev-parse <branch-or-vault-ref>)
t=$(git rev-parse "${tip}^{tree}")
twin=$(awk -v t="$t" '$2==t{print $1; exit}' /tmp/main_trees.txt)
# twin is a commit in origin/main with identical content → that IS the branch's home.
git push --force-with-lease="<branch>:<recorded-old-sha>" origin "${twin}:refs/heads/<branch>"
# Verify: branch is now a real ancestor of main.
git merge-base --is-ancestor "$twin" origin/main && echo "ancestor-of-main ✓"
```

The branch shows `+0/-N` against main (contained, distinct tip per branch).

### Case B — no exact tip-twin (recent commits the rewrite rebundled)

Walk first-parent history to the **deepest ancestor that has a twin**, then graft the
commits above it onto that twin. The base trees are byte-identical, so the replay is
**conflict-free**:

```bash
# find the deepest twin ancestor (base) and its twin in main:
for c in $(git rev-list --first-parent "$tip"); do
  t=$(git rev-parse "${c}^{tree}")
  twin=$(awk -v t="$t" '$2==t{print $1; exit}' /tmp/main_trees.txt)
  [ -n "$twin" ] && { echo "base=$c twin=$twin"; break; }
done

git checkout -B __reanchor "$tip"
git clean -fdq                       # untracked/generated files can block the replay
git rebase --onto "$twin" "$base"    # replays branch commits onto the in-main twin
# Verify merge-base, then push:
test "$(git merge-base HEAD origin/main)" = "$(git rev-parse "$twin")" && \
  git push --force-with-lease="<branch>:<recorded-old-sha>" origin HEAD:refs/heads/<branch>
git checkout - && git branch -D __reanchor
```

The branch shows `+K/-M` against main: its `K` real commits above the shared ancestor.

> **Gotcha (2026-06-04):** a mid-rebase `"Your local changes would be overwritten by
> merge"` is almost always an **untracked/generated file** (`__pycache__`, `.pyc`,
> build output) colliding with a replayed add — `git clean -fdq` first, then retry.

## Section 5 — Detection & verification (use TREE-twins, NOT graph merge-base)

⚠️ **CRITICAL — the trap that caused handwaving (2026-06-04):** `git merge-base` is a
**graph** proxy. After a rewrite/rebundle, a branch can show `merge-base != root` and
"+472 ahead" yet its **content converges with main 1–2 commits back** (byte-identical
tree-twin on a divergent SHA line). Concluding "not orphaned, nothing to do" from
`merge-base != root` is WRONG — it hides exactly the branches that need re-anchoring.
**The real test is the tree-twin search (Sections 3–4), per branch, always.**

```bash
MAIN=$(git rev-parse origin/main); git log "$MAIN" --format='%H %T' > /tmp/main_trees.txt
for b in <branches>; do
  tip=$(git rev-parse origin/$b)
  # PRIMARY: deepest first-parent commit whose TREE has a twin in main + how far up:
  C=""; DT=""; above=0
  # Walk the FULL first-parent history (no head cap): a deeper-than-N twin is
  # exactly the case a truncated scan would falsely report as NO-TWIN — that
  # truncation IS the handwaving this section guards against.
  for c in $(git rev-list --first-parent "$tip"); do
    m=$(awk -v t="$(git rev-parse ${c}^{tree})" '$2==t{print $1;exit}' /tmp/main_trees.txt)
    [ -n "$m" ] && { C="$c"; DT="$m"; break; }; above=$((above+1))
  done
  if [ -z "$DT" ]; then echo "$b NO-TWIN (truly disjoint — investigate)";
  elif [ "$C" = "$(git rev-parse origin/$b)" ] && git merge-base --is-ancestor "$DT" "$MAIN"; then
    echo "$b already-anchored (tip is in-main commit ${DT:0:9})"
  else echo "$b NEEDS-REANCHOR: graft $above commit(s) onto twin ${DT:0:9}"; fi
done
```

Pass = every branch either is already an in-main ancestor OR has been grafted onto its
twin (Section 4). A branch reporting `NEEDS-REANCHOR` is the work — even if its naive
`merge-base` is not the root. Never report "no orphans" without having run this per-branch.

## Section 6 — Do NOT confuse re-anchor with content-merge

Re-anchoring moves the **branch ref** so the *graph* is clean. It does **not** merge the
branch's content into `main`. If `main` is the canonical/most-evolved tree (it usually is
after the rewrite — verify with `git diff origin/main <branch> = +small/-large`), merging
old branch content back would **regress** it. Re-anchor for a clean graph; merge only
genuinely-unique, forward work via a reviewed PR. See [[project_orama_main_rewrite_pr70]].

## Section 7 — Related

- [`expunge-git/SKILL.md`](../expunge-git/SKILL.md) — the rewrite that creates the orphans.
- [`docs/wiki/13-alphaclaw-fork-contrib-branches.md`](../../../../docs/wiki/13-alphaclaw-fork-contrib-branches.md)
  — fork invariant + `scripts/git/alphaclaw-align-all.sh` (the cherry-pick-onto-integration
  variant, for forks that track an upstream mirror).
- `scripts/periscope/recreate-ordered-prs-onto-merged.sh` — ordered-PR rebuild onto a
  curated base (the periscope `merged`-branch variant).
- [`docs/LESSONS.md`](../../../../docs/LESSONS.md) — the 2026-06-04 re-anchor journey.

## Scope

Applies to any repo on the orama-system stack whose `main` was rewritten/force-pushed.
For forks tracking an upstream (AlphaClaw, periscope), prefer the repo-specific
align scripts which encode the same `merge-base == mirror` invariant.
