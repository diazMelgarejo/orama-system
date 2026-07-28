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
| Record `origin/<branch>` SHA immediately after fetch and use it as the explicit lease target | Generic `--force-with-lease` can protect against the wrong expectation after another fetch |
| Build the replacement commit in a unique disposable worktree from the fresh base | Avoids resetting a dirty/canonical checkout or treating a filesystem path as a Git revision |
| Preserve the reviewed synthesis source outside both the PR branch and disposable worktree | Cleanup runs on success and failure; the temporary worktree must never be the only copy |

---

## Protocol — path-scoped replay

Replace `<BASE>`, `<BRANCH>`, and `<PATHS…>` for your repo. Set
`FUSION_SOURCE` to a durable reviewed source outside the branch being rewritten.

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
BASE=merged                    # or main / feature/MacOS-post-install
BRANCH=ecc-tools/periscope-…   # PR head branch
FUSION_SOURCE="${FUSION_SOURCE:?set to the durable reviewed fusion source}"
REPLAY_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/pr-replay.XXXXXX")"
FUSION_WORKTREE="$REPLAY_PARENT/worktree"

cleanup_replay_worktree() {
  git -C "$REPO_ROOT" worktree remove --force "$FUSION_WORKTREE" \
    >/dev/null 2>&1 || true
  rm -rf "$REPLAY_PARENT"
}
trap cleanup_replay_worktree EXIT

# 1) Fetch once and record the exact remote lease before constructing anything
git -C "$REPO_ROOT" fetch origin "$BASE" "$BRANCH"
EXPECTED_REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
printf 'recorded lease: %s\n' "$EXPECTED_REMOTE_SHA"

# 2) Construct the replacement commit from the fresh integration base
git -C "$REPO_ROOT" worktree add --detach "$FUSION_WORKTREE" "origin/$BASE"

# Copy only reviewed, proven-unique paths from the durable source
# Example (periscope ECC fusion):
# cp "$FUSION_SOURCE/.agents/skills/periscope/SKILL.md" \
#    "$FUSION_WORKTREE/.agents/skills/periscope/SKILL.md"
# … repeat for each path in the unique set …

# 3) Stage and commit inside the disposable worktree
git -C "$FUSION_WORKTREE" add -- <PATH1> <PATH2> <PATH3>
git -C "$FUSION_WORKTREE" diff --cached --stat   # MUST show non-empty

(cd "$FUSION_WORKTREE" \
  && bash "$REPO_ROOT/scripts/git/commit-clean.sh" \
    -m "feat: replay harmonized delta onto fresh $BASE")

# 4) Verify the detached replacement commit's exact scope
git -C "$FUSION_WORKTREE" diff --stat "origin/$BASE"..HEAD
git -C "$FUSION_WORKTREE" log --oneline "origin/$BASE"..HEAD
# Expect exactly one commit and only the approved path set.

# 5) Update the PR branch with the explicitly recorded lease
git -C "$FUSION_WORKTREE" push \
  --force-with-lease="refs/heads/$BRANCH:$EXPECTED_REMOTE_SHA" \
  origin "HEAD:refs/heads/$BRANCH"

# 6) The EXIT trap removes the worktree and parent on success or failure
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
| Empty commit pushed; PR shows 0 files changed | `commit-clean.sh` without prior `git add` | Re-stage paths; verify cached stat before commit-clean |
| Fusion content lost during cleanup | Disposable worktree held the only copy | Keep a durable `FUSION_SOURCE` outside the PR branch and replay worktree |
| PR still CONFLICTING | Replayed full bundle instead of delta | Diff against base; drop paths already on base |
| Timestamp-only diff in PR | Included generator metadata files | Omit `ecc-tools.json` / `identity.json` unless intentionally harmonized |
| Force-push overwrote newer remote work | Generic lease used after another fetch | Record `origin/<branch>` once and pass its SHA in the explicit lease refspec |

---

## Related

- [`fresh-main-integrity-diff-claygo.md`](../../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md) — Protocol B/C unique-path discovery
- [`integrative-merge.md`](../../oramasys-method/references/integrative-merge.md) — synthesize mode for dual-generator inputs
- [`periscope-ecc/SKILL.md`](../../periscope-ecc/SKILL.md) — ECC mirror verifier + dependency instinct pair policy
- [`docs/reference/periscope-cursor-repo-rules.md`](../../../../docs/reference/periscope-cursor-repo-rules.md) — periscope branch model
