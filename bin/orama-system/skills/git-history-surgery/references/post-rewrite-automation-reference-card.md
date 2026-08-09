# Post-Rewrite Automation — Reference Card

> **Use when:** local expunge / `filter-repo` finished, `main` and branches need
> publishing, stale remotes deleted, and open PR branches reanchored on rewritten
> `origin/main`.
> **Goal:** one scripted path from "local rewrite done" to "GitHub clean + branches
> healthy" without pre-push stalls or manual per-branch guesswork.
> **Origin:** 2026-08-08 VERBOTEN expunge — manual tmux loops replaced by this card.

Applies to **any repo** in the workspace; scripts live in **orama-system**
`scripts/git/` and accept a `repo_path` argument.

---

## Rule (agents: inviolable)

```text
After history surgery:
  1. hooks OFF → publish → reanchor → verify → hooks ON
  2. never leave pre-push running during multi-branch force-push
  3. delete MERGED/in-main remotes; cherry-reanchor the rest onto origin/main
```

See also: [`history-surgery-hooks-safeguard-reference-card.md`](history-surgery-hooks-safeguard-reference-card.md).

---

## One-command finish (preferred)

From the rewritten repo (or pass any workspace repo path):

```bash
# orama-system canonical scripts — run against any repo path.
# $ORAMA_SYSTEM_PATH / $PERPETUA_TOOLS_PATH are this workspace's documented
# sibling-repo variables (see scripts/resolve_orama_root.sh /
# resolve_perp_harness.sh) — never hardcode a workstation path here.
ALLOW_MAIN_PUSH=1 PUSH_MAIN=1 PUSH_ALL_BRANCHES=1 \
  bash "$ORAMA_SYSTEM_PATH/scripts/git/post-rewrite-finish.sh" "$ORAMA_SYSTEM_PATH"

ALLOW_MAIN_PUSH=1 PUSH_MAIN=1 PUSH_ALL_BRANCHES=0 \
  bash "$ORAMA_SYSTEM_PATH/scripts/git/post-rewrite-finish.sh" "$PERPETUA_TOOLS_PATH"
```

`post-rewrite-finish.sh` runs, in order:

1. `post-rewrite-publish.sh` — force-push `main` (+ optional all branches), hooks off
2. `post-rewrite-reanchor.sh` — scan → delete merged → cherry-reanchor open branches
3. `scan-tracked-banned-tokens.sh` (when present)
4. Local-only `origin/main` meta/blob verify (counts only — never prints literals)

Restore hooks is automatic via `install-local-hooks.sh` at end of publish.

---

## Step-by-step (when you need control)

### 1. Publish rewritten refs

```bash
export HISTORY_SURGERY_ACTIVE=1
export ALLOW_MAIN_PUSH=1

bash scripts/git/post-rewrite-publish.sh .

# optional: every local branch (after filter-repo removed origin once)
PUSH_ALL_BRANCHES=1 bash scripts/git/post-rewrite-publish.sh .
```

If GitHub `main` is protected (`GH006`), temporarily disable branch protection or
push clean history to `main-expunged-clean-<date>` and swap default branch.

### 2. Scan branch health (tree twins — not ahead/behind)

```bash
bash scripts/git/reanchor_scan.sh . origin/main remotes | tee /tmp/reanchor-scan.txt
python3 scripts/git/parse-reanchor-scan.py /tmp/reanchor-scan.txt > /tmp/actions.json
```

| Scan label | Meaning | Action |
| ---------- | ------- | ------ |
| `MERGED/in-main` | Tip tree already in `main` | **Delete** remote branch |
| `NEEDS-REANCHOR` | Unique commits above a main tree-twin | **Cherry-reanchor** |
| `NO-TWIN` | Disjoint from rewritten `main` | Manual review / clean replay |

### 3. Delete stale merged branches

```bash
bash scripts/git/delete-merged-remote-branches.sh . --from-json /tmp/actions.json
# preview: add --dry-run
```

### 4. Cherry-reanchor open PR branches

Preferred after full blob/metadata scrub (`rebase --onto` often conflicts).

```bash
# Default: never delete remotes on cherry-pick failure (DELETE_ON_CHERRY_CONFLICT=0).
bash scripts/git/cherry-reanchor-branches.sh . --from-json /tmp/actions.json --all-needs
```

If automation previously deleted open PR branches, recover from local tips:

```bash
bash scripts/git/restore-deleted-branches.sh . <branch> [<branch>...]
# hard conflicts / submodule repos:
bash scripts/git/restore-branch-theirs.sh . <branch>
```

Success criterion for each surviving branch:

```bash
[ "$(git merge-base origin/main "origin/<branch>")" = "$(git rev-parse origin/main)" ]
```

Empty cherry-picks are skipped by default (`SKIP_EMPTY_CHERRY=1`).

### 5. Verify GitHub `main`

```bash
bash scripts/git/scan-tracked-banned-tokens.sh   # current tree
# all-ref origin/main scan runs inside post-rewrite-finish.sh
```

---

## Script map

| Script | Role |
| ------ | ---- |
| `history-surgery-git.sh` | `git -c core.hooksPath=/dev/null` wrapper |
| `history-surgery-push.sh` | hooks-off `git push` |
| `reanchor_scan.sh` | tree-twin detector (existing) |
| `parse-reanchor-scan.py` | scan → JSON actions |
| `delete-merged-remote-branches.sh` | remove `MERGED/in-main` remotes |
| `cherry-reanchor-branches.sh` | replay `git cherry` `+` commits on `main` |
| `restore-deleted-branches.sh` | safe reanchor; local source; never deletes on failure |
| `restore-branch-theirs.sh` | conflict/submodule recovery with tree align |
| `post-rewrite-publish.sh` | force-push phase |
| `post-rewrite-reanchor.sh` | scan + delete + cherry orchestrator |
| `post-rewrite-finish.sh` | publish + reanchor + verify |

---

## Forbidden

| Action | Why |
| ------ | --- |
| Per-branch push with default hooks after rewrite | Pre-push guard-sync stalls; false blocks |
| `rebase --onto` as first choice after full scrub | Rewritten ancestry → conflict storms |
| Trust `NEEDS-REANCHOR` as "broken" when `merge-base == origin/main` | Open PR branches *should* be N commits ahead |
| Delete branches before `parse-reanchor-scan` / user ack | May destroy unique PR work |
| `DELETE_ON_CHERRY_CONFLICT=1` without explicit operator ack | Accidentally deleted open PR #283 and siblings |

---

## Related

- [`reanchor-after-rewrite.md`](reanchor-after-rewrite.md) — tree-twin theory
- [`expunge-contaminated-history.md`](expunge-contaminated-history.md) — scrub sequence
- [`history-surgery-hooks-safeguard-reference-card.md`](history-surgery-hooks-safeguard-reference-card.md)
- [`../SKILL.md`](../SKILL.md) — decision item 13
