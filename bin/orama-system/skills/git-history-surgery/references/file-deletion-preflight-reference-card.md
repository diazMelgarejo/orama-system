# Whole-file Deletion Preflight — Reference Card

> **Durable invariant.** A tracked file disappearance is a high-signal scope
> change. Block it at both commit and push boundaries until it is reviewed or
> deliberately justified. Canonical checker:
> `scripts/git/check_file_deletion_guard.sh`.

## Purpose

Git correctly represents a removed path as status `D`, but `git add -u`, a
wrong worktree, or a malformed Git data API tree can turn a narrow change into
many deletions without a Git error. The cost is disproportionate: a remote
ref can publish a tree that omits large sections of the repository.

The guard has two independent layers:

| Boundary | Checker | Catches |
| --- | --- | --- |
| Before commit | `--staged` | accidental removals placed in the index |
| Before push | `--range <remote>..<local>` | commits made without hooks and the final outgoing tree |

Both layers inspect only `git diff --diff-filter=D`. They do **not** block
line deletions, ordinary edits, or renames.

## Required proof bundle

Before every ordinary commit and push, establish scope from Git—not memory:

```bash
git status --short
git diff --cached --name-status
bash scripts/git/check_file_deletion_guard.sh --staged
git diff --name-status origin/main..HEAD
bash scripts/git/check_file_deletion_guard.sh --range origin/main..HEAD
```

For a Git data/tree API publication, require the returned tree SHA to equal
local `HEAD^{tree}` before creating the commit or updating the branch ref. Do
not update the ref if the tree SHAs differ; this catches truncated blob
payloads and omitted tree entries before the remote branch becomes visible.

## Block and recovery

| Exit | Symbol | Meaning |
| --- | --- | --- |
| 0 | `GIT_SCOPE_OK` | No whole-file removal, or explicit justified exception |
| 9 | `GIT_SCOPE_E_FILE_DELETION` | One or more `D`-status paths require review |
| 2 | — | Usage error or not in a Git repository |

On block, inspect the listed paths. If accidental before commit, use
`git restore --staged --worktree -- <path>`; if already committed, restore or
amend it before publishing. Re-run the checker and inspect `--name-status`.

## Intentional exception

An intentional removal needs both variables for that command:

```bash
GIT_ALLOW_FILE_DELETIONS=1 \
GIT_FILE_DELETION_JUSTIFICATION='why this exact file removal is safe' \
git commit -m 'chore: remove obsolete asset'
```

The commit and PR must record the reason and affected paths. `--no-verify` is
not a routine bypass: it disables unrelated safety controls and leaves no
evidence that the deletion was reviewed.

## Enforcement and portability

- `.githooks/pre-commit` runs `--staged`.
- `.githooks/pre-push` runs `--range` for every outgoing branch ref.
- The script uses Bash 3.2-safe `while IFS= read -r` loops; do not introduce
  `mapfile`, `readarray`, associative arrays, or newer-Bash-only syntax.
- `scripts/git/guard-sync-manifest.sh` designates it as canonical
  cross-repository guard tooling. Downstream copies must be synchronized from
  Orama rather than locally forked.

## Regression specification

`tests/test_check_file_deletion_guard.py` proves clean/staged/range behavior,
requires both override values, checks hook wiring, and runs `bash -n` for
portable syntax. Add a failing regression case before changing the guard.

## Related

- `bin/orama-system/skills/git-file-deletion-guard/SKILL.md` — discovery wrapper
- `bin/orama-system/skills/git-history-surgery/SKILL.md` — parent doctrine
- `bin/orama-system/skills/git-history-surgery/references/pending-operation-push-guard-reference-card.md`
  — separate protection against unfinished operations
- `docs/wiki/08-git-hygiene-and-branching.md` — operational checklist
