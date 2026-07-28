# Path-Scoped PR Replay on Fresh Integration Base — Git Reference Card

> **Use when:** An open PR is `CONFLICTING` / `DIRTY` because its branch still carries
> pre-merge commits that re-add content already landed on the integration base; or when
> two generator runs produced overlapping artifacts and a harmonized delta must ship as
> one clean commit.
> **Goal:** Reset to the **current integration base**, replay **only proven unique paths**,
> single commit, force-with-lease — no cross-merge ping-pong.
> **Pair with:** [`fresh-main-integrity-diff-claygo.md`](../../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md)
> Protocol B/C; [`integrative-merge.md`](../../oramasys-method/references/integrative-merge.md)
> synthesize mode.

Origin: periscope PR #12 ECC fusion (2026-07-28). PR #10 had already merged the ECC
bundle onto `merged`; PR #12 still stacked two commits from pre-#10 `merged`, causing
duplicate bundle adds and GitHub `mergeStateStatus: DIRTY`.

---

## When to use

| Situation | Use this card |
|-----------|----------------|
| Integration PR conflicts because base moved forward with overlapping content | ✅ |
| Harmonized/synthesized delta must replace noisy multi-commit branch history | ✅ |
| Only a **known path list** changed; rest is merge noise or timestamp churn | ✅ |
| History rewrite / expunge recovery | ❌ use [`reanchor-after-rewrite.md`](reanchor-after-rewrite.md) |
| Full branch tree replay after dual-pedigree reanchor | ❌ use tree-twin + `read-tree` protocol in reanchor card |

**Integration base by repo (not always `main`):**

| Repo | Agent PR base |
|------|----------------|
| periscope | `merged` |
| AlphaClaw | `feature/MacOS-post-install` |
| orama-system, Perpetua-Tools | `main` |

Never replay onto periscope `main` — it is the upstream mirror only.

---

## Non-negotiables

| Rule | Why |
|------|-----|
| `git fetch origin <integration-base>` immediately before replay | Stale base reintroduces the conflict |
| Replay **paths only** — never merge the stale branch wholesale | Whole-branch merge re-imports deleted/guard paths |
| `git add` staged paths **before** `commit-clean.sh` | `commit-clean.sh` does not stage; empty commits are silent failures |
| Exclude timestamp-only files unless intentionally harmonized | `ecc-tools.json` / `identity.json` `generatedAt` churn adds review noise |
| `git push --force-with-lease` only after verifying `git diff --stat <base>..HEAD` | Proves the PR delta is exactly the intended paths |
| Preserve synthesis content in a **known-good worktree** before resetting branch | Force-push overwrites remote; do not extract fusion blobs from the branch you are about to rewrite |

---

## Protocol — path-scoped replay

Replace `<BASE>`, `<BRANCH>`, `<PATHS…>`, and `<WORKTREE>` for your repo.

```bash
REPO=/path/to/repo
BASE=merged                    # or main / feature/MacOS-post-install
BRANCH=ecc-tools/periscope-…   # PR head branch
WORKTREE="${TMPDIR:-/tmp}/pr-replay-$$"

cd "$REPO"
git fetch origin "$BASE" "$BRANCH"

# 1) Preserve harmonized content OUTSIDE the branch being rewritten
#    (worktree, stash, or tagged preserve branch)
mkdir -p "$WORKTREE"
git worktree add --detach "$WORKTREE" "origin/$BASE"

# Copy or author only the proven unique paths into $WORKTREE
# Example (periscope ECC fusion):
# cp /path/to/fusion/.agents/skills/periscope/SKILL.md \
#    "$WORKTREE/.agents/skills/periscope/SKILL.md"
# … repeat for each path in the unique set …

# 2) Reset PR branch to fresh integration base
git checkout -B "$BRANCH" "origin/$BASE"

# 3) Apply path-scoped delta from preserve worktree
git checkout "$WORKTREE" -- <PATH1> <PATH2> <PATH3>
git add <PATH1> <PATH2> <PATH3>
git diff --cached --stat   # MUST show non-empty

# 4) Commit (stage first — commit-clean.sh does not git add)
bash scripts/git/commit-clean.sh -m "feat: replay harmonized delta onto fresh $BASE"

# 5) Verify delta scope
git diff --stat "origin/$BASE"..HEAD
git log --oneline "origin/$BASE"..HEAD   # expect exactly 1 commit

# 6) Push
git push --force-with-lease origin "$BRANCH"

# 7) CLAYGO teardown
git worktree remove --force "$WORKTREE" 2>/dev/null || rm -rf "$WORKTREE"
```

---

## Worked example — periscope PR #12 ECC fusion (2026-07-28)

**Before:**

| Item | Value |
|------|-------|
| Base (`merged`) | `f4a43cd6` — PR #10 ECC already merged |
| PR #12 branch | 2 commits from pre-#10 `015cd4ef` |
| GitHub | `mergeable: CONFLICTING`, `mergeStateStatus: DIRTY` |

**Unique path set (harmonized delta only):**

```text
.agents/skills/periscope/SKILL.md
.claude/skills/periscope/SKILL.md
.claude/homunculus/instincts/inherited/periscope-instincts.yaml
```

**Excluded:** `.claude/ecc-tools.json`, `.claude/identity.json` (timestamp-only vs PR #10).

**After replay:**

| Item | Value |
|------|-------|
| Head | `9e465d9c` — single commit |
| Delta | 3 files, +305 / −132 |
| GitHub | `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` |

**Integrative-merge notes preserved in replay:**

- PR #10 contribution/testing workflows + PR #12 dependency evidence synthesized
- Dependency instinct pair kept with `## Related` cross-links
- All 15 stable PR #10 instinct IDs preserved; 2 PR #12 additions added
- Agents ↔ Claude skills byte-identical (verify with `scripts/periscope/verify-ecc-skill-mirror.sh` from orama-system)

---

## Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty commit pushed; PR shows 0 files changed | `commit-clean.sh` without prior `git add` | Re-stage paths; amend with new commit-clean |
| Fusion content lost after force-push | Extracted blobs from branch being rewritten | Preserve in separate worktree **before** reset |
| PR still CONFLICTING | Replayed full bundle instead of delta | Diff against base; drop paths already on base |
| Timestamp-only diff in PR | Included generator metadata files | Omit `ecc-tools.json` / `identity.json` unless intentionally harmonized |

---

## Related

- [`fresh-main-integrity-diff-claygo.md`](../../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md) — Protocol B/C unique-path discovery
- [`integrative-merge.md`](../../oramasys-method/references/integrative-merge.md) — synthesize mode for dual-generator inputs
- [`periscope-ecc/SKILL.md`](../../periscope-ecc/SKILL.md) — ECC mirror verifier + dependency instinct pair policy
- [`docs/reference/periscope-cursor-repo-rules.md`](../../../../docs/reference/periscope-cursor-repo-rules.md) — periscope branch model
