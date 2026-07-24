---
name: fable5-git-rebase-safety
description: >
  Tree-twin safety doctrine for post-rewrite branch validation. NEVER use rev-list --count,
  merge-base, or ahead/behind after rewrites. Use git cherry + tree-twins to prove branch
  safety across rewritten histories. Invoke when: "validate branches after rewrite",
  "prove branch is safe", "check if branch is orphaned", "rebase safety check",
  "parallel agent branch collision", "post-rewrite branch validation", "tree-twin scan",
  or "branch safety audit".
---

# Fable-5 Git Rebase Safety: Tree-Twin Doctrine

Operationalizes the tree-twin safety pattern for validating branches after git history
rewrites. This skill implements consensus from the Fable-5 LLM Council (7/7 agents,
highest agreement level).

**Key invariant:** After main is rewritten (squash-merge, filter-repo, force-push),
every branch's SHA becomes meaningless. The ONLY correct test is the TREE-TWIN:
whether a branch's tree (%T) matches a commit already in main. Two commits with
the same tree are byte-identical regardless of SHA/author/date/message.

Use this skill to:
- Validate branches post-rewrite without false orphan positives
- Prove branch safety before merging
- Detect true orphans (no tree-twin in main)
- Avoid the "600 behind" incident (orama PR#70, 2026-06-05 PT repeat)
- Resolve parallel agent branch collisions safely

## When to Invoke

| Situation | Action |
|-----------|--------|
| Main was rewritten; branches look "600 behind" | Run tree-twin scan; validate before acting |
| Two parallel agents produced independent branches | Scan both for tree-twins; resolve conflicts |
| Merging after a rebase or squash-merge | Verify branch is not orphaned (has tree-twin) |
| Auditing branch safety across the workspace | Scan all remotes/heads; validate reachability |
| Deciding to force-push or rebase | Always run scan first; record lease target |

## The Tree-Twin Principle

**What happens when main rewrites:**
```text
Before rewrite:
  commit abc123: tree=t1, parent=p1, message="Feature X"
  main → abc123

After rewrite (e.g., squash-merge):
  commit xyz789: tree=t1, parent=p2, message="Feature X"  ← SAME TREE, NEW SHA
  main → xyz789

Old SHA-based tools (rev-list --count, merge-base):
  ❌ See "abc123 is 47 commits behind xyz789" — WRONG, tree is identical

Tree-twin scan:
  ✓ Detects tree=t1 in main
  ✓ Proves branch is fully merged (tip is tree-twin)
```

**Why tree-twins are correct:**
- Git's tree object (%T) is the CONTENT hash, independent of history
- Two commits with %T=t1 have identical diffs, messages, and final code
- SHA changes when parent/author/date change; tree never changes unless content changes
- After rewrite, SHAs lie; trees never lie

## Procedure

### Step 1: Scan Branch Tree-Twin Status

```bash
bash scripts/git/reanchor_scan.sh <repo_path> [origin/main] [scope]
```

**Parameters:**
- `repo_path`: absolute path to repository root
- `origin/main`: reference branch (default: origin/main)
- `scope`: which branches to scan
  - `remotes` (default): scan origin/* (exclude origin/HEAD, origin/main)
  - `heads`: scan local refs/heads/* (exclude main)
  - `all`: scan both remotes and heads

**Example:**
```bash
# Scan all remote branches in current repo
bash scripts/git/reanchor_scan.sh . origin/main remotes

# Scan all local branches + remotes (full audit)
bash scripts/git/reanchor_scan.sh . origin/main all

# Scan a parallel worktree
bash scripts/git/reanchor_scan.sh ~/code/oramasys/worktrees/agent-work origin/main heads
```

### Step 2: Interpret Scan Output

The scan categorizes every branch into one of four states:

```text
MERGED/in-main (tip=tree-twin)
  ✓ Branch is fully included in main
  ✓ All commits are present (possibly reordered or squashed)
  → Action: safe to delete branch

NEEDS-REANCHOR: graft N unique commit(s) onto tree-twin
  ⚠ Branch has unique work not yet in main
  ⚠ Work lives above a commit that IS in main (tree-twin)
  → Action: run suggested cherry-pick command to graft onto new parent
  → Command: git cherry -v origin/main <branch-tip> <first-unique>

NO-TWIN but shares merge-base
  ⚠ Branch and main share common ancestor
  ⚠ No tree-twin found in main (branch diverged)
  → Action: likely fine; merge normally or use git cherry to compare
  → Investigate: git diff origin/main...<branch>

ORPHAN (no tree-twin, merge-base==root)
  ❌ Branch has zero connection to main's history
  ❌ No common ancestor besides repo root
  → Action: investigate deletion or archive branch; ask: was this meant to be created?
```

### Step 3: Validate Safety Before Merge

After scan, before merging:

```bash
# Show commits unique to branch
git cherry -v origin/main <branch-name>

# Preview merge (no changes)
git merge --no-commit --no-ff <branch-name>
git diff --name-only --diff-filter=U   # show conflicts

# Abort preview
git merge --abort

# If all looks good: merge normally
git merge <branch-name>
git push origin main
```

### Step 4: Parallel Agent Branch Merge Protocol

When two agents independently produce branches for the same feature:

1. **Scan both branches:**
   ```bash
   bash scripts/git/reanchor_scan.sh . origin/main all
   ```

2. **Identify tree-twins:**
   - If both have same tree-twin: they are byte-identical; delete one, fast-forward the other
   - If different tree-twins: they diverged; requires manual merge

3. **Simulate both merges (do NOT commit yet):**
   ```bash
   git merge --no-commit --no-ff branch-A
   git diff --name-only --diff-filter=U   # enumerate conflicts
   git merge --abort
   # repeat for branch-B
   ```

4. **Present conflicts to user; wait for direction**

5. **Resolve all in one pass (choose strategy: union/superset/additive/correct)**

6. **Verify before commit:**
   ```bash
   pytest
   python scripts/review/repo_hygiene.py .
   bash scripts/git/reanchor_scan.sh . origin/main heads
   ```

7. **Push → CI → GitHub API merge**

8. **Wait 10 minutes; confirm `mergeable_state: clean` on GitHub API**

## Non-Negotiables

1. **NEVER use these after a rewrite:**
   - `git rev-list --count origin/main..branch` (lies after rewrite)
   - `git merge-base origin/main branch` (meaningless across rewrites)
   - GitHub's "600 commits behind" (UI proxy; breaks on rewrite)
   - Any adjacency-based reasoning (assumes SHAs are stable)

2. **ALWAYS use tree-twin scan:**
   - Before deciding a branch is orphaned
   - Before force-pushing to main
   - Before deleting "stale" branches post-rewrite
   - Before merging parallel agent work

3. **Record lease targets before force-push:**
   ```bash
   CURRENT=$(git rev-parse origin/main)
   git push --force-with-lease=main:$CURRENT origin main
   ```

4. **Prove reachability:**
   - All commits in a NEEDS-REANCHOR branch must be reachable from main eventually
   - Scan output shows how many commits above tree-twin; verify all are intentional

5. **Never flatten distinct branches:**
   - Don't force a branch to be "identical to origin/main" unless user explicitly asks
   - Tree-twins prove content match; distinct SHAs are fine (and expected)

## Granular Refinement: Per-File / Per-Commit Triage

`reanchor_scan.sh` classifies a branch by its **tip**. Real audits often need
finer granularity: the tip isn't a tree-twin (main moved on differently), yet
specific commits or files inside the branch were still individually
cherry-picked/rebased into main, or specific pieces are genuinely stale while
others aren't. Live example (2026-07-24, a three-worktree audit across
Perpetua-Tools + orama-system) surfaced four techniques worth using together.

### A. Patch-ID — confirm "same work, different SHA" for one commit pair

When a branch and main both have a commit with a matching message (a
rebase/cherry-pick candidate):

```bash
git log origin/main --oneline --all -1 --grep="<distinctive phrase>"
pid_a=$(git show <branch-sha> | git patch-id --stable | awk '{print $1}')
pid_b=$(git show <main-sha>   | git patch-id --stable | awk '{print $1}')
[ "$pid_a" = "$pid_b" ] && echo "IDENTICAL -- same patch, rebased" || echo "DIVERGED -- investigate diff"
```

`patch-id` ignores parent/author/date; it fingerprints the diff content
itself. A match proves the two commits are the same change — there is no
"more elegant version to pick," they're the same code under a different SHA.

### B. Scope against a specific PR's merge commit, not main's moving tip

Diffing a stale branch against main's *current* tip conflates "what this
branch is missing" with "everything main did unrelated since." Scope to the
actual PR that superseded the work:

```bash
PR_SHA=$(gh pr view <N> --json mergeCommit --jq .mergeCommit.oid)
git diff --stat <branch> "$PR_SHA"     # isolates the real remaining delta
```

In the live example, a branch that looked "52 ahead / 90 behind" origin/main
shrank to a genuine 19-file / ~1,260-line delta once scoped against the one
PR that actually superseded most of it.

### C. Structural supersession — a big diff doesn't always mean missing work

Before concluding a large per-file diff represents unlanded work, check
whether main's file became a thin delegator to a new location:

```bash
git show origin/main:<path> | wc -l                        # suspiciously small?
git show origin/main:<path> | grep -n "^from \|^import "   # delegates elsewhere?
```

Live example: a branch's 1,663-line `agent_coordination_core.py` diff against
main looked like a huge gap. Main's actual file was 23 lines — a thin wrapper
delegating to a new `orchestrator/coordination/` module from an unrelated,
larger refactor PR. The branch's *capability* wasn't missing from main; the
whole file had been restructured. Replaying the old diff would fight the new
architecture — any real bug fix inside it needs re-deriving against the new
module, not a mechanical replay.

### D. GitHub PR titles/bodies as provenance breadcrumbs

`gh pr list --state all --search "<keyword>"` and reading merged-PR bodies
often reveals that "missing" work landed under a *differently-named*
branch/PR. Search by keyword or issue/PR number reference before assuming
work was silently dropped.

### Triage classification (apply per file/commit, not just per branch)

| Class | Test | Action |
|-------|------|--------|
| DONE (ancestor) | `merge-base --is-ancestor` | Nothing to do |
| IDENTICAL-REBASED | patch-id match | Nothing to do — same content |
| OBSOLETE-SUPERSEDED | main's file delegates to a newer module/location | Re-derive substance against new structure; don't replay |
| NEEDS UNION MERGE | append-only shared file, diverged both ways | Merge unique entries from both sides, never delete |
| GENUINELY UNIQUE | none of the above | Real gap — surface for a landing decision |

## Real-World Evidence: orama-system Validation

**Repository:** orama-system (canonical)
**Validation date:** 2026-07-04
**Evidence:** Live tree-twin scan on canonical orama-system repo

Ran: `bash scripts/git/reanchor_scan.sh "$(git rev-parse --show-toplevel)" origin/main all`

**Results:**
- **Total branches scanned:** 34
  - Remote branches (origin/*): 20
  - Local branches: 14
- **MERGED/in-main:** 20 branches (all work already integrated in main, safe to delete)
- **NEEDS-REANCHOR:** 14 branches (contain unique commits to graft onto tree-twin parents)
- **ORPHAN:** 0 branches (zero orphaned, all have tree-twins in main history)
