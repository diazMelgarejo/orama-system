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
| 2 | Nothing unpushed is unique | `git cherry -v <target>` shows no `+` lines, or each `+` has a tree twin (see [`reanchor-after-rewrite.md`](../skills/git-history-surgery/references/reanchor-after-rewrite.md)) — **never** an ahead/behind count | back up (3) and re-anchor instead |
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
*Status:* **no script currently qualifies.** `scripts/cursor/cloud-install.sh`
`clone_sibling` resets without gates 1–2, so it is an *unqualified* reset that
this card does not endorse: treat it as unsupported until the checks land (see
"Open items"). It is named here so the gap is visible, not as a use case.

### 3. Fork `main` is an upstream mirror

*Where:* `scripts/periscope/rebuild-deps-prs-onto-merged.sh`;
`scripts/git/alphaclaw-sync-integration-with-main.sh`.
*Purpose:* in a fork where `main` is *defined* as the upstream mirror and real
work lives on `merged` / integration branches, `main` is re-pointed to
upstream.
*Qualify:* the declaration that `main` is a mirror is itself the authority
(gate 5) — it must be written in the repo's docs, not inferred by the script.
Gate 2 still applies; publish with an expected-head compare
(`--force-with-lease`), never a bare force. Never apply this to a repo where
`main` carries unique work (the canonical "never hard-reset `main`" rule).

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

- `cloud-install.sh clone_sibling` should run gates 1–2 before resetting and
  stop on a dirty mirror. Not changed here: it is a behavioural change to an
  install script and needs its own test.
- Both recommending doc sites should be re-read after the next playbook edit
  to confirm they still link here.
