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
| `main` was rewritten and branches look 600 commits behind/orphaned | [`references/reanchor-after-rewrite.md`](references/reanchor-after-rewrite.md) |

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

## Non-Negotiables

- Never paste the real forbidden token into PR titles, commit messages, issue
  comments, shell history, or docs. Use placeholders.
- Never force-push without a recorded lease target.
- Never judge rewritten branches by `merge-base`, `rev-list --count`, or GitHub
  ahead/behind alone.
- Never flatten branches to `origin/main` unless the user explicitly asks to
  destroy their distinct branch identity.
- Never treat a clean git rewrite as secret remediation. Rotation is separate.
- **Platform line endings:** do not convert Windows-serving files (`platform/windows/**`,
  `*.cmd`, `*.bat`, `*.ps1`) to LF from macOS/Linux. Mac/Linux-owned sources stay LF.
  See [`references/platform-line-endings-turf.md`](references/platform-line-endings-turf.md).
- **Bash 3.2 hook scripts:** macOS `/bin/bash` lacks `mapfile`. New or edited
  `scripts/git/*.sh` must use `while read` loops (see
  [`references/bash-32-git-script-portability.md`](references/bash-32-git-script-portability.md)).
  Install hooks: `bash scripts/git/install-local-hooks.sh` (includes TDD `commit-msg` gate).

## Verification

After any history surgery:

```bash
python scripts/review/repo_hygiene.py .
bash scripts/git/reanchor_scan.sh <repo> origin/main [heads|remotes|all]
git log --all --format="%B" | grep -i "<token>"   # must print nothing
git reflog --all | wc -l                          # should be near-zero after scrub
```

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

## Related skills

- [[icloud-escape-move]] — relocate a repo tree out of iCloud to a plain local path (mv → worktree repair → compatibility symlink); a freshly-moved tree can look orphaned until re-anchored with this skill.
