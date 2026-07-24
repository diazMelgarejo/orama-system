---
name: git-history-surgery
description: >
  End-to-end git history surgery for the orama-system stack: scrub contaminated
  history, force-push safely, and recover/re-anchor branches after a rewrite using
  byte-identical tree twins. Invoke when: "expunge git history", "remove secret
  from history", "rewrite author", "scrub commits", "branches are 600 behind",
  "orphaned branch after rewrite", "re-anchor branch to main", "branches lost
  common ancestor", "recover deleted branch", "git history rewrite recovery",
  "byte-identical common ancestor", or "branches all became the same".
---

# Git History Surgery

One source of truth for dangerous git history operations. This skill replaces the
former split between separate rewrite-scrub and branch-recovery skills.

Use it for two related jobs:

| Situation | Procedure |
| --- | --- |
| A secret, forbidden identity, token, or workstation path landed in history | [`references/expunge-contaminated-history.md`](references/expunge-contaminated-history.md) |
| `main` was rewritten and branches now look 600 commits behind/orphaned | [`references/reanchor-after-rewrite.md`](references/reanchor-after-rewrite.md) |

Fail closed: preserve refs, prove the operation is necessary, and use
`--force-with-lease` only after recording the expected remote SHA.

## Windows PowerShell Bootstrap

Before any `fetch`, `rebase`, `push`, scrub, or local verification on the Windows
LM Studio host, run
[`references/windows-powershell-runtime-bootstrap.md`](references/windows-powershell-runtime-bootstrap.md).

## Decision Flow

1. Is there a leaked secret/identity/path in committed history?
   Use the expunge reference, rotate any secret, and require fresh clones.
2. Did a rewrite already happen and branches now look impossible to reason about?
   Use the re-anchor reference and tree-twin scan. Do not trust ahead/behind counts.
3. Is this only a normal bad commit?
   Do not perform history surgery. Use a normal PR or revert.
4. Did the scrub only rewrite metadata/messages while file blobs may also be
   contaminated?
   Treat metadata scrub, current-tree sanitization, PR-branch replay, and
   all-ref blob scanning as separate verification gates. Do not call a scrub
   globally complete until every required gate for the stated scope passes.
5. Is an open PR's final tree correct, but its intermediate branch history
   contains contaminated or chaos-generating commits?
   Use the clean replacement PR option in
   [`references/expunge-contaminated-history.md`](references/expunge-contaminated-history.md):
   preserve the old PR/ref, replay the final tree onto current `origin/main` as
   a fresh branch, prove tree equivalence, close the old PR, and open a sanitized
   replacement PR.
6. Mac ↔ Win (or any peer) must sync `main` while the worktree is dirty?
   Use [`references/safe-cross-host-sync-reference-card.md`](references/safe-cross-host-sync-reference-card.md) —
   stash → `pull --ff-only` → pop → commit → push. Never `reset --hard` or force-push `main`.
   On **Perpetua-Tools**, also read [`references/local-runtime-overlay-reference-card.md`](references/local-runtime-overlay-reference-card.md)
   — stash `config/devices.yml` / `config/models.yml` explicitly when needed; never `git checkout` overlay paths.
7. Post-merge integrity check or stale branch with merge noise — what is truly unique vs current `main`?
   Use [`references/fresh-main-integrity-diff-claygo.md`](references/fresh-main-integrity-diff-claygo.md)
   (ephemeral fresh `origin/main` baseline; **CLAYGO** clean before/after each run).
   Canonical protocol: [`../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md`](../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md).

## Non-Negotiables

- Never paste the real forbidden token into PR titles, commit messages, issue
  comments, shell history, or docs. Use placeholders.
- Never force-push without a recorded lease target.
- Never judge rewritten branches by `merge-base`, `rev-list --count`, or GitHub
  ahead/behind alone.
- Never interpret a branch suddenly showing hundreds of commits after a scrub as
  hundreds of semantic changes without first checking tree twins. It is usually
  rewritten ancestry.
- Never flatten branches to `origin/main` unless the user explicitly asks to
  destroy their distinct branch identity.
- Never treat a clean git rewrite as secret remediation. Rotation is separate.
- Never treat a clean re-anchor as proof that contaminated blobs were removed
  from all refs. Re-anchor repairs graph ancestry; blob expungement needs its
  own all-ref scan.
- Never keep a contaminated PR's intervening commits just to preserve review
  continuity. When the final tree is the artifact worth keeping, a replacement
  PR from a clean branch can be the safer, more reviewable result.
- **Platform line endings:** do not convert Windows-serving files (`platform/windows/**`,
  `*.cmd`, `*.bat`, `*.ps1`) to LF from macOS/Linux. Mac/Linux-owned sources stay LF.
  See [`references/platform-line-endings-turf.md`](references/platform-line-endings-turf.md).
- **Bash 3.2 hook scripts:** macOS `/bin/bash` lacks `mapfile`. New or edited
  `scripts/git/*.sh` must use `while read` loops (see
  [`references/bash-32-git-script-portability.md`](references/bash-32-git-script-portability.md)).
  Install hooks: `bash scripts/git/install-local-hooks.sh` (includes TDD `commit-msg` gate).
- **Never declare a git action complete without querying the actual result.**
  Stating "PR #N merged to main" or "pushed" without having just run
  `gh pr view N --json state,mergedAt` / `git ls-remote` / an equivalent
  direct check is a false status report, not a completed action. This
  happened for real: a PR was reported merged in a planning summary and
  never actually merged, then treated as done for the next several steps.
- **After `gh pr merge` on ANY branch other than main (a stacked/dependent
  PR), capture the PR's own merged-commit SHA and verify against that --
  not a raw `HEAD == origin/<source-branch>` comparison.** `gh pr merge`
  updates the branch on GitHub; your local checkout does NOT update
  itself, AND GitHub commonly deletes the source branch immediately after
  merge (a default repo setting), so `origin/<source-branch>` may no
  longer exist to compare against at all. Capture the real result first:
  `gh pr view N --json mergeCommit,state,mergedAt` (or `git ls-remote
  origin <target-branch>` if the source branch is expected to be gone),
  then verify your local tip matches that captured SHA with exact
  comparison (`git rev-parse HEAD` == the captured SHA) before doing
  further local work, or `git merge-base --is-ancestor <captured-sha>
  HEAD` if further local commits are expected on top. If you keep working
  locally without this, later local merges can silently carry a stale,
  pre-merge version of files the remote merge already fixed.
  `merge-base --is-ancestor` alone proves ancestry (A is in B's history)
  but NOT exact identity -- two different refs can both be ancestors of
  each other when one is a merge commit containing the other; capture the
  specific SHA GitHub actually produced, don't infer it from ancestry.

## Verification

After any history surgery:

```bash
python scripts/review/repo_hygiene.py .
bash scripts/git/reanchor_scan.sh <repo> origin/main [heads|remotes|all]
git log --all --format="%B" | grep -i "<token>"   # must print nothing
git reflog --all | wc -l                          # should be near-zero after scrub
```

If the incident involved forbidden file contents, memory files, local identity
literals, or secrets, also run an all-ref blob scan with local-only pattern
input. The scanner must report counts/labels only, not literal values. A clean
working tree is not enough evidence for an all-history claim.

For PR branch cleanup without contamination, rebase or merge normally; do not use
this skill unless history was rewritten or contaminated.

## Multi-Agent Branch Merge

When independent agents produce concurrent branches, use this protocol before
any merge. This is distinct from history surgery — no rewrite is involved, but
the same discipline (simulate before touching, record lease targets) applies.

### Quick protocol (full detail in reference)

```bash
# 1. Simulate BOTH merges before touching either
git merge --no-commit --no-ff <branch-A>
git diff --name-only --diff-filter=U   # enumerate conflicts
git merge --abort
# repeat for branch-B

# 2. Present every conflict to human; wait for direction
# 3. Resolve all in one pass (union/superset/additive/correct strategy)
# 4. Verify: pytest + hygiene + no remaining conflict markers
# 5. Push → CI → GitHub API merge
# 6. Wait 10 minutes; confirm mergeable_state: clean; proceed to next merge
```

**Conflict resolution strategies:** `additive` (empty+content→take content),
`union` (both partial→concatenate), `superset` (verify inclusion→take larger),
`architecturally-correct` (bug→take fix), `api-correct` (casing→take lowercase).

### Absorbing external/automated PR content (mandatory ordering)

When adapting content from other agents' or bots' branches (autobot CI-fix
PRs, a teammate's rebased branch, cherry-picks) into a branch you're actively
working on, **do all remote-sync merges first, then replay the new/adapted
content on top — never interleave them**:

1. **Preserve the adapted/new content first, before any remote-sync
   merge** — commit it to a temporary branch (`git checkout -b
   <tag>-preserve && git add -A && git commit -m "<tag>: preserve before
   remote sync"`) or `git stash push -u -m "<tag>"` (the `-u` is
   mandatory: untracked files are otherwise silently left behind and can
   be lost or clobbered by the merge in step 2). Do this even if the
   content is still uncommitted/in-progress -- a remote-sync merge
   operating on a dirty working tree can conflict with or silently
   overwrite exactly the content you're trying to protect.
2. Once step 1's preservation is confirmed (branch exists, or `git stash
   list` shows the entry), fetch and merge every relevant already-merged
   remote ref into the now-clean local branch (`origin/main`,
   `origin/<this-branch>` if a stacked PR was merged separately, etc.).
   **Verify with the check that actually matches what you just did, not
   exact SHA equality by default:**
   - If you fast-forwarded the SAME tracking branch to its own remote
     (no local commits of your own on top), exact equality is correct:
     `git rev-parse HEAD` == `git rev-parse origin/<branch>`.
   - If you MERGED `origin/main` (or another ref) into a branch that has
     its own local commits -- the actual case this section is about --
     the merge produces a new commit that has the remote ref as an
     ancestor, never an equal SHA. Use `git merge-base --is-ancestor
     origin/main HEAD` instead; exact equality will never be true here
     and checking for it anyway either always fails (false alarm) or
     gets silently skipped, neither of which verifies anything.
   Don't assume a prior fetch is still current either way -- fetch fresh
   before checking.
3. Reapply/cherry-pick the preserved content (from the temp branch or
   `git stash pop`) on top of that clean, synced base.
4. Run the full relevant test suite before committing — a clean cherry-pick
   (no conflict markers) is necessary but not sufficient; it can still land
   on stale symbols/APIs if step 2 was skipped or incomplete.

Doing this out of order — replaying new content first, syncing remotes
after — is exactly how a later "sync main" merge can silently re-introduce
an already-fixed bug: git's 3-way merge has no way to know your replayed
content already superseded what's arriving from upstream, so a conflicting
upstream version can win without ever showing a conflict marker.

**Key invariant:** `"merged": true` on GitHub ≠ content on branch.
Always verify: `git diff origin/main...origin/<branch>` after any merge.

See full decision tree and verification commands:
[`references/multi-agent-collaboration-protocol.md` § Nested-Branch Merge Protocol](references/multi-agent-collaboration-protocol.md)



When a commit includes a version bump, always use the centralized sync script —
**never** `sed -i` or manual multi-file edits:

```bash
# 1. Edit the single source of truth only
#    src/orama_system/_version.py  →  __version__ = "X.Y.Z.W"

# 2. Propagate to all 25+ canonical surfaces
python3 scripts/sync_version.py

# 3. Verify
python3 -m pytest tests/test_version_docs.py

# 4. Commit everything together
git add -A
git commit -m "chore(version): bump to X.Y.Z.W"
```

If `scripts/sync_version.py --check` exits 1 after a commit, a surface is stale.
Run the script (no flags) to fix it, then amend or add a follow-up commit.

See: [`docs/LESSONS.md` — 2026-06-21 centralized version system](../../../../docs/LESSONS.md)
See: [`docs/wiki/06-multi-agent-collab.md`](../../../../docs/wiki/06-multi-agent-collab.md) (full surface registry)

## References

- [`references/safe-cross-host-sync-reference-card.md`](references/safe-cross-host-sync-reference-card.md) — stash-first Mac↔Win `main` sync (non-destructive; distinct from history surgery)
- [`references/local-runtime-overlay-reference-card.md`](references/local-runtime-overlay-reference-card.md) — PT `config/devices.yml` / `config/models.yml` discovery cache (never discard; never commit)
- [`references/fresh-main-integrity-diff-claygo.md`](references/fresh-main-integrity-diff-claygo.md) — ephemeral fresh-main diff; true unique branch contribution; CLAYGO teardown
- [`references/multi-agent-collaboration-protocol.md`](references/multi-agent-collaboration-protocol.md) — full nested-branch merge protocol (7 steps, 6 strategies, invariants, GitHub API commands)
- [`skills/using-git-worktrees/SKILL.md`](../using-git-worktrees/SKILL.md) — parallel agent worktree lifecycle; Step 3 embeds the merge trigger
- [`docs/wiki/06-multi-agent-collab.md`](../../../../docs/wiki/06-multi-agent-collab.md) — version registry + Nested-Branch Merge Protocol table
- [`references/platform-line-endings-turf.md`](references/platform-line-endings-turf.md) — CRLF on Windows turf; LF on Mac/Linux; no cross-platform EOL tug-of-war
- [`references/expunge-contaminated-history.md`](references/expunge-contaminated-history.md)
- [`references/reanchor-after-rewrite.md`](references/reanchor-after-rewrite.md)
- [`references/windows-powershell-runtime-bootstrap.md`](references/windows-powershell-runtime-bootstrap.md)
- [`references/bash-32-git-script-portability.md`](references/bash-32-git-script-portability.md) — macOS bash 3.2; no `mapfile` in hook scripts; `check_tdd_commit.sh` pattern
- [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../docs/wiki/08-git-hygiene-and-branching.md)
- [`docs/wiki/13-alphaclaw-fork-contrib-branches.md`](../../../../docs/wiki/13-alphaclaw-fork-contrib-branches.md)
- [`scripts/git/reanchor_scan.sh`](../../../../scripts/git/reanchor_scan.sh)
- [`scripts/sync_version.py`](../../../../scripts/sync_version.py) — version propagation
- [`src/orama_system/_version.py`](../../../../src/orama_system/_version.py) — single source of truth

## v2 Authoring Standards

When rewriting history or amending commits in skill/reference files, ensure the
amended content is LINT-015 compliant — all fenced blocks labeled.  
Reference: `bin/orama-system/references/skill-architecture-guide.md` § v2 Mandatory Code Creation Standards.

## Related skills

- [[icloud-escape-move]] — relocate a repo tree out of iCloud to a plain local path (mv → worktree repair → compatibility symlink); a freshly-moved tree can look orphaned until re-anchored with this skill.
- [[security]] — upstream of this skill: category-only tracked policy, the local-only registry pattern, OpSec vs SecOps vocabulary, and verification-gate discipline for keeping a leak from happening in the first place. Use `security` before a leak lands; use `git-history-surgery` once one already has.
- [[fable5-git-rebase-safety]] — the tree-twin doctrine this skill's reanchor step relies on, plus a granular per-file/per-commit triage (patch-id matching, scoping against a specific PR's merge commit, detecting structural supersession) for auditing branches/worktrees that look stale or divergent before deciding what to reanchor, discard, or replay.


## Post-Review Micro-Remediation

When addressing review findings (CodeRabbit or human) on an open PR: cluster
findings by root cause, fix once at the abstraction level, keep every commit
mechanically attributable to its failure class, and never accumulate revert
chains — reset to a safety-ref-protected ancestor instead when policy allows.

Full doctrine: [`references/post-review-micro-remediation.md`](../../references/post-review-micro-remediation.md)
