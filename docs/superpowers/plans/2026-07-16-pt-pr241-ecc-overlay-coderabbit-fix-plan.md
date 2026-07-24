# PT PR #241 ECC Overlay CodeRabbit Fix Plan

**Status:** executed on PT PR branch after Claude review
**Target PR:** [Perpetua-Tools #241](https://github.com/diazMelgarejo/Perpetua-Tools/pull/241)
**Target branch:** `chore/ecc-overlay-ed387-review-gate-20260715`
**Scope:** fix all five CodeRabbit review comments as one cohesive ECC overlay hardening pass.

## Context

PR #241 makes the `vendor/ecc-tools` overlay intent-aware: a reviewed TSV registry
classifies approved local overlay paths, `save --review` prints a digest-bound
candidate, `save --approve` writes only the reviewed candidate, and update/upgrade
restore the existing approved patch without rewriting it.

The review comments are valid because they all tighten the same invariant:
the overlay patch is an adaptive, reviewed intent artifact, not a blind snapshot.
The follow-up should therefore be one small cohesive commit rather than five
unrelated edits.

## Confirmed Current State

- Claude review found the original plan was missing a required Step 0:
  PR #241 had become `CONFLICTING`/`DIRTY` against current PT `main`.
- PR #241 was reconciled with current PT `main` first, preserving main's newer
  memory and lockfile changes while synthesizing the ECC overlay conflicts.
- Follow-up commit pushed to the PR branch: `8f04c4b1`.
- CodeRabbit posted five actionable comments.
- `scripts/git/ecc-local-overlay.tsv` is the intent registry.
- `scripts/git/ecc-local-additions.patch` remains only the portable application artifact.
- The PT coordination-board PR #205 row was stale and has been released; no open claims remain.

## Step 0: Reconcile Current PT Main First

Before applying CodeRabbit fixes, merge current PT `main` into the PR branch and
resolve conflicts by synthesis:

- keep main's newer `.agent/memory/*`, candidate, and `uv.lock` state;
- keep PR #241's intent-registry overlay model;
- preserve main's `_restore()` logic that applies each registered path
  independently so an existing `new-file` overlay cannot mask an `additive`
  overlay elsewhere;
- resolve the patch file conflict without changing the reviewed overlay content.

Validation for Step 0:

```bash
git merge --no-ff origin/main
git diff --name-only --diff-filter=U
```

Expected: no unresolved files after synthesis.

## Fix Set

### 1. Documentation Wording

File: `scripts/git/ecc-local-additions.md`

Change the opening description from "Five reviewed local-only paths" to
"Five reviewed local overlay paths." Keep "local-only" only where it describes
`new-file` entries in the overlay contract.

Reason: `.env.example` is an `additive` overlay against an upstream-owned file,
so calling all five paths "local-only" blurs the registry semantics.

### 2. UTF-8 Locale Before Text I/O

File: `scripts/git/ecc-submodule-sync.sh`

Set repository-standard locale variables immediately after `set -euo pipefail`,
before any manifest, patch, or TSV read:

```bash
export LC_ALL="${LC_ALL:-C.UTF-8}"
export LANG="${LANG:-C.UTF-8}"
```

If macOS compatibility rejects `C.UTF-8` in local smoke tests, use the repo's
established fallback pattern instead of inventing a new locale policy.

Reason: TSV and patch contents may include UTF-8 text; locale must be fixed
before `_load_overlay_manifest` reads tracked text.

### 3. Dedicated Temporary Index For Candidate Generation

File: `scripts/git/ecc-submodule-sync.sh`

Refactor `_make_candidate` so intent-to-add never touches the developer's real
submodule index:

- create `local tmp_index`
- export/use `GIT_INDEX_FILE="$tmp_index"` only for the candidate-generation block
- seed it with `git read-tree HEAD`
- run `git add --intent-to-add -A` without suppressing errors
- run `git diff --binary --cached HEAD` or equivalent against the temporary index
- remove the temporary index in all exit paths
- propagate failures instead of silently writing an incomplete candidate

Reason: the current `git add --intent-to-add -A || true` and `git reset -q || true`
can hide failures and momentarily mutate the real submodule index.

### 4. Reject Mode-Only And Non-Regular Overlay Entries

File: `scripts/git/ecc-submodule-sync.sh`

Extend candidate validation beyond numstat counts:

- for `additive`, reject any `new file mode`, `deleted file mode`, `old mode`,
  `new mode`, rename, copy, or symlink mode transition
- for `new-file`, require `new file mode 100644`
- reject symlink modes such as `120000`
- preserve the existing add-only and expected-create-count checks

Reason: the registry allows content overlays, not symlink creation, mode-only
changes, or executable-bit drift.

### 5. Show Full Candidate Hunks Before Approval

File: `scripts/git/ecc-submodule-sync.sh`

In `_review_candidate`, keep the current path/mode/intent assessment and stat,
but print the full candidate patch hunks before showing the approval digest.
Use an existing Git diff renderer such as:

```bash
git -C "$SUB" apply --stat "$CANDIDATE"
git -C "$SUB" apply --summary "$CANDIDATE"
sed -n '1,240p' "$CANDIDATE"
```

If the patch can exceed a readable terminal size later, add paging only as a
follow-up. For this PR, full hunk output is preferred because the reviewed patch
is deliberately small.

Reason: digest approval must be based on seeing the actual content, not only
path summaries and file counts.

## Suggested Implementation Order

1. Run Step 0 above if the PR branch is behind or conflicting.
2. Edit docs wording first; no behavior change.
3. Add UTF-8 locale export near the script entry point.
4. Refactor `_make_candidate` to use a temporary index.
5. Harden `_validate_candidate` with mode-transition checks.
6. Expand `_review_candidate` output to show full hunks.
7. Run targeted shell validation.
8. Run repo hygiene.
9. Commit one cohesive follow-up to the PR branch.

## Validation

Run from the PT PR #241 worktree:

```bash
bash -n scripts/git/ecc-submodule-sync.sh
bash scripts/git/ecc-submodule-sync.sh save --review
python3 scripts/review/repo_hygiene.py .
gh pr checks 241 --repo diazMelgarejo/Perpetua-Tools --watch=false
```

Expected review output must still include the existing successful signal:

```text
save: reviewed candidate contains 5 approved file diff(s)
```

Observed on the pushed fix branch:

```text
save: reviewed candidate contains 5 approved file diff(s)
repo hygiene checks passed
```

Add two negative smoke checks if time permits:

```bash
# mode-only drift is rejected
# symlink or non-100644 new-file drift is rejected
```

## Commit Shape

```text
fix(ecc): harden reviewed overlay approval flow
```

Commit body should mention:

- preserves the intent-registry model;
- protects the real submodule index during candidate creation;
- rejects mode/symlink drift;
- prints full candidate hunks before digest approval;
- updates wording so additive overlays are not mislabeled local-only.

## Non-Goals

- Do not merge PR #241 without explicit operator approval.
- Do not rewrite the overlay patch outside `save --approve`.
- Do not change the ECC upstream pin unless the PR branch already owns that change.
- Do not mine old PR #205 branches in this pass; that board row was stale and cleared.
