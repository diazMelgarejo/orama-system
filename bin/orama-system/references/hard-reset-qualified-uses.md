# Hard Reset — Qualified Uses

> **Role:** the one place that says *when* `git reset --hard <ref>` is a
> legitimate orama tool, and the gate every use must pass. Playbook rows and
> scripts that recommend it link here instead of restating it.
> **Why this exists:** the playbook recommends it in two places
> ([`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)
> conflict table; `docs/wiki/06-multi-agent-collab.md` Orphan Branch Recovery)
> while a dozen skills say "never hard-reset `main`". Both are right; neither
> said what separates the cases. This card does. Nothing is removed — each use
> is kept and given its conditions (orama-way: additive, never amputate).

---

## What it does, and the one property that matters

A hard reset moves the current branch pointer **and overwrites the working
tree and index to match**. Commits that were reachable only from the old
pointer become reflog-only; uncommitted changes are gone with no reflog entry.
It is therefore only safe when *everything it would discard is either
worthless, already preserved elsewhere, or deliberately being discarded by
someone with authority to do so.*

## The qualifying gate (all must hold, in order)

| # | Check | How | If it fails |
| --- | --- | --- | --- |
| 1 | Tree is clean | `git status --porcelain` is empty (untracked too) | commit or park on a WIP ref first |
| 2 | Nothing is left unreferenced | no commit reachable only from the ref(s) being moved lacks a patch-equivalent in the target (`git cherry`; see [`reanchor-after-rewrite.md`](../skills/git-history-surgery/references/reanchor-after-rewrite.md)). A commit another branch, tag or remote-tracking ref still holds is *not* at risk. A detached HEAD is the one holder with no name — **never** an ahead/behind count | back up (3) and re-anchor instead |
| 3 | A recovery ref exists | `git branch backup/<name>-<stamp> HEAD` (or a tag) *before* resetting | create it; it costs nothing |
| 4 | Target is an exact SHA | `git rev-parse origin/<b>` after a fresh fetch, then reset to that SHA | never reset to a name that can move mid-command |
| 5 | You own the branch | local-only, or a branch you alone push to; or operator named it | use a fresh worktree instead (below) |
| 6 | Not shared PR history | the branch is not an open PR head that others fetch | use [`concurrent-head-reapply.md`](concurrent-head-reapply.md) |

Checks 1–4 are mechanical and scriptable. Checks 5–6 are authority checks:
a script can warn, a human or the operator decides.

The autoresearch hook blocks the literal command in agent sessions. That is a
stop sign for an *agent*, not a defect: the operator runs it, or the agent uses
the non-destructive equivalent below.

## The non-destructive equivalent (prefer it)

For every use below that is not a *mirror* or a *ruled rewrite*, the same
outcome needs no reset:

```bash
git fetch origin "$B"
git worktree add -b "$NEW" "$HUB/$NEW" "origin/$B"   # absolute path
# copy or cherry-pick the intended files into $HUB/$NEW
```

The old checkout is untouched and remains the recovery reference.

---

## Use cases — kept, and what qualifies each

### 1. Orphan-branch recovery (no common ancestor)

*Where:* conflict-playbook row `rebase add/add on every file`; wiki 06.
*Purpose:* `git merge-base HEAD origin/main` exits 1, so a rebase conflicts on
every file. The branch's history is unrelated to `main`; only its *files*
carry intent.
*Qualify:* gates 1–4, **plus** write down the 5-or-so files you will re-apply
*before* resetting (copy them out, or rely on the backup ref). Prove
"orphan" with `git merge-base` exit status, not with a large conflict count.
*Prefer:* fresh worktree from `origin/main` + copy the files in.

### 2. Disposable mirror of a remote branch

*Purpose:* a sibling checkout nobody edits must equal `origin/<branch>` so the
agent environment is reproducible.
*Qualify:* the checkout is a **pure mirror** — declared as such. Gates 1–2
must be *checked, not assumed*: if the mirror is dirty or has unique commits,
someone edited a mirror; fail loudly rather than erase it.
*Implementation:* `scripts/cursor/lib-mirror-sync.sh` `mirror_sync_checkout`,
called by `cloud-install.sh` `clone_sibling`. It checks gate 1 (clean tree,
untracked included) and gate 2 (the move leaves no commit unreferenced that
lacks a patch-equivalent in the remote), captures the target SHA once after the
fetch (gate 4), and then moves the branch with `checkout -B <sha>` — on a verified
clean tree that needs no hard reset at all. Anything it cannot prove safe is
*refused, never erased*: status 10 dirty, 11 unpushed commits, 12 cannot verify.
`clone_sibling` warns and leaves the checkout untouched so cloud boot is not
killed; `CLOUD_INSTALL_ON_DIVERGED_MIRROR=fail` makes it a hard failure.
Covered by `tests/test_cloud_install_mirror_sync.py`. Backed by PT
`lesson_fdcff1271292` (PT PR #441, **pending merge**).
*History:* before this, `clone_sibling` reset unconditionally and the card listed
it as unsupported; that gap is closed.

### 3. Fork `main` is an upstream mirror

*Where:* `scripts/periscope/rebuild-deps-prs-onto-merged.sh`;
`scripts/git/alphaclaw-sync-integration-with-main.sh`.
*Why these exist (first principles, from PT memory):*

- **Periscope** — `main` and `agentsview` are upstream mirrors; `merged` is the
  only integration base, and a rewrite recovery must preserve both mirror
  parents and the proven `merged` tree (`lesson_fdb82283644f`). The script
  exists because three dependabot PRs were merged into the mirror by mistake.
  Re-pointing `main` restores the invariant "tree-identical to upstream" and
  the three commits are re-homed onto `merged`. Those three SHAs are therefore
  the *only* commits that may legitimately be dropped.
- **AlphaClaw** — the integration branch never merges into `main`; the flow is
  merge PRs into `main`, sync upstream into `main`, then reverse-merge `main`
  *into* the integration branch with union merges, never deleting
  (`lesson_881de77084d5`). Session start syncs `main` fast-forward-only
  (`lesson_9fffe4530a95`). Moving local `main` to `origin/main` is that
  fast-forward; local work that is not a fast-forward is anomalous, not
  something to discard.

*Qualify:* the declaration that `main` is a mirror is itself the authority
(gate 5) and is written in the repo's docs, not inferred by the script. The
re-point runs through `mirror_repoint_to_upstream` / `mirror_sync_checkout`
(`scripts/cursor/lib-mirror-sync.sh`): clean tree; every commit it would leave
unreferenced must be one the caller **declared** (periscope: the three
`COMMIT_*` SHAs; AlphaClaw: none); a backup ref is created first; the remote
is updated with an expected-head lease so a concurrent push is not overwritten.
Never apply this to a repo where `main` carries unique work (the canonical
"never hard-reset `main`" rule). Covered by `tests/test_fork_main_repoint.py`.

*Bugs found by applying the gate* (PT `lesson_7fa7d6219657` and
`lesson_9fd72be1baa7`, both in PT PR #441, **pending merge**): (1) the periscope
script ran
`git fetch origin upstream`, which asks `origin` for a branch named `upstream`
and never fetches the `upstream` remote, so the re-point target could be stale
or missing; (2) the AlphaClaw script's second step moved the *integration*
branch to its remote with the same blind reset, silently dropping unpushed
integration commits and reporting success.

### 4. Ruled history rewrite / expunge

*Where:* `expunge-contaminated-history.md` step 05.
*Purpose:* move `main` to a clean tip after contaminated history was purged.
*Qualify:* an explicit, recorded operator ruling for *that* rewrite
(lesson `lesson_f11f751d7446`: squash/rewrite/expunge are reserved for
human-approved privacy, security, or faulty-history remediation). Gates 3–4
apply with extra force: the backup ref is the proof of what was removed.

### 4b. PT lessons that prescribe reset-then-replay

*Where:* PT `lesson_3060e4382900` (diverged branch: reset to origin tip,
reapply only your deltas) and `lesson_c4e8f12a9b3d` (periscope: reset to fresh
`origin/merged`, replay the harmonized path delta; provisional).
*Purpose:* recover a branch whose history is no longer worth keeping while
preserving its *intent*.
*Qualify:* these target an **open PR branch**, so gates 5–6 apply: if anyone
else fetches that branch, use a fresh worktree and a fast-forward reapply
([`concurrent-head-reapply.md`](concurrent-head-reapply.md)). The lessons'
intent — keep only your verified delta — is unchanged; only the means is
qualified.

### 5. Test fixtures

*Where:* `tests/test_check_no_pending_merge.py`.
*Purpose:* build a scratch repo state. Qualifies trivially — the repo is a
`tmp_path` the test created. Listed so a future audit does not mistake it for
a recommendation.

---

## Never

- On a shared PR branch to "catch up" — that is the reapply rule.
- To discard a conflicted merge or an unwanted stash — use `git merge --abort`
  or `git stash drop <sha>` after reading it.
- On `main` of a repo where `main` is not a declared mirror.
- Chained with a push in the same command without having printed what will be
  discarded.

## Open items

- Both recommending doc sites should be re-read after the next playbook edit
  to confirm they still link here.
