# Fresh-Main Integrity Diff (CLAYGO) — Git Reference Card

> **Use when:** Post-merge regression check; stale branch with merge noise; PR triage
> ("what is actually unique here?"); integrity audit after several merges; suspicion of
> silent wrong-merge / content loss.
> **Goal:** Diff a branch's **true unique contribution** against **current** `origin/main`
> using an ephemeral fresh-main baseline — not the local checkout's stale `main` ref.
> **CLAYGO:** **C**lean **l**ast run's ephemeral artifacts **a**s **y**ou **g**o **o**ut —
> teardown at end of every run **and** remove previous run's paths before starting again.

Origin: PR #280 → #284 clean extraction (stale branch had ~12 merge commits; only 2–3
memory files were truly unique vs `origin/main`).

---

## When to use

| Situation | Use this card |
|-----------|----------------|
| "Is my branch corrupt or just behind `main`?" | ✅ |
| Integrity check after merges landed while worktree stayed on a feature branch | ✅ |
| Stale PR / branch with noisy merge history — extract true unique files | ✅ |
| Normal single-commit PR on fresh branch | Optional — `git diff origin/main...HEAD` from canonical checkout is enough |
| History rewrite / expunge | ❌ use [`expunge-contaminated-history.md`](expunge-contaminated-history.md) |
| Mac ↔ Win dirty sync only | ❌ use [`safe-cross-host-sync-reference-card.md`](safe-cross-host-sync-reference-card.md) |

**Repos:** run per repo (`orama-system`, `Perpetua-Tools`).

---

## Non-negotiables

| Rule | Why |
|------|-----|
| **CLAYGO start:** delete previous run's temp dir/worktree before creating a new one | Avoids diffing against a stale fresh baseline |
| **CLAYGO end:** always remove ephemeral clone/worktree | Leaves no dangling `git worktree list` entries |
| Fetch `origin/main` immediately before baseline | Local `main` ref may be 30–70 commits stale |
| Compare **committed** trees, not working-tree overlay noise | See [local-runtime-overlay](local-runtime-overlay-reference-card.md) for PT `config/devices.yml` / `config/models.yml` |
| Never `git checkout` overlay files to "fix" integrity diffs | Overlay is intentional local cache |
| Never judge unique work by ahead/behind counts alone after rewrites | Use tree diff + `git cherry -v` |

---

## Protocol A — integrity check (fresh `origin/main` vs local `origin/main` ref)

Answers: "Did GitHub `main` land correctly?" (not "what's unique on my branch?")

```bash
REPO=$(git rev-parse --show-toplevel)
NAME=$(basename "$REPO")
CLAYGO="${TMPDIR:-/tmp}/claygo-integrity-${NAME}-$$"

# CLAYGO: clean previous run(s) for this repo name, then isolate this run
rm -rf "${TMPDIR:-/tmp}"/claygo-integrity-${NAME}-* 2>/dev/null || true
mkdir -p "$CLAYGO"

git fetch origin main --prune
git clone --depth 1 --branch main "$(git -C "$REPO" remote get-url origin)" "$CLAYGO/fresh"

# Local committed main ref (may be stale — that's what we're testing)
LOCAL_MAIN=$(mktemp -d)
git -C "$REPO" archive origin/main | tar -x -C "$LOCAL_MAIN"

diff -rq "$CLAYGO/fresh" "$LOCAL_MAIN" \
  | grep -vE 'Only in.*(\.git|__pycache__|\.pytest_cache)' || true
# 0 content diffs (except caches) => origin/main ref matches GitHub

# CLAYGO teardown
rm -rf "$CLAYGO" "$LOCAL_MAIN"
```

---

## Protocol B — branch true unique contribution vs current `origin/main`

Answers: "What does this branch add that `main` does not have **right now**?"

Run from the **branch under review** (canonical checkout or dedicated worktree):

```bash
REPO=$(git rev-parse --show-toplevel)
NAME=$(basename "$REPO")
BRANCH=$(git rev-parse --abbrev-ref HEAD)
CLAYGO="${TMPDIR:-/tmp}/claygo-unique-${NAME}-$$"

rm -rf "${TMPDIR:-/tmp}"/claygo-unique-${NAME}-* 2>/dev/null || true
mkdir -p "$CLAYGO"

git fetch origin main --prune
git clone --depth 1 --branch main "$(git remote get-url origin)" "$CLAYGO/fresh-main"

# 1) Commit-level unique work (three-dot)
echo "=== unique commits (origin/main...$BRANCH) ==="
git log --oneline origin/main...HEAD

echo "=== patch-id equivalence (already landed?) ==="
git cherry -v origin/main HEAD

# 2) Tree-level unique content (committed HEAD vs fresh main)
BRANCH_TREE=$(mktemp -d)
git archive HEAD | tar -x -C "$BRANCH_TREE"
diff -rq "$CLAYGO/fresh-main" "$BRANCH_TREE" \
  | grep -vE 'Only in.*(\.git|__pycache__|\.pytest_cache)' \
  | head -50

# CLAYGO teardown
rm -rf "$CLAYGO" "$BRANCH_TREE"
```

**Interpretation:**

- Many `git log` lines but tiny/no `diff -rq` delta → merge noise; consider clean extraction (Protocol C).
- `git cherry -v` shows `+` → patch not in `main`; `-` → already landed under different SHA.
- PT overlay paths differ only in working tree → not branch contribution; see overlay card.

---

## Protocol C — clean extraction (stale PR → fresh branch)

When Protocol B shows most diff is merge noise and only a few paths matter:

```bash
git fetch origin
git checkout -b 2026-mm-dd-clean-extract origin/main

# Only paths proven unique in Protocol B (example — replace with your list)
git checkout origin/<stale-branch> -- .agent/memory/candidates/graduated/foo.json

git status --short
python3 scripts/review/repo_hygiene.py .    # both repos as applicable
# Open new PR; close stale PR with supersession note
```

Never merge the stale branch wholesale "to catch up."

---

## Protocol D — ephemeral `git worktree` variant (no clone)

Same semantics as Protocol A/B; use when clone is slow but worktree is acceptable:

```bash
REPO=$(git rev-parse --show-toplevel)
NAME=$(basename "$REPO")
WT="${TMPDIR:-/tmp}/claygo-wt-${NAME}-$$"

rm -rf "${TMPDIR:-/tmp}"/claygo-wt-${NAME}-* 2>/dev/null || true
git fetch origin main --prune
git worktree add --detach "$WT" origin/main

# Example: compare fresh detached main to branch tree
BRANCH_TREE=$(mktemp -d)
git -C "$REPO" archive HEAD | tar -x -C "$BRANCH_TREE"
diff -rq "$WT" "$BRANCH_TREE" | head -50

git worktree remove --force "$WT"
rm -rf "$BRANCH_TREE"
```

---

## Overlay exclusions (Perpetua-Tools)

When running Protocol A/B on a **local checkout** (not a fresh clone), these paths may
show as modified without indicating branch contribution or merge corruption:

- `config/devices.yml`
- `config/models.yml`

**Do not** `git checkout` them. For committed-tree comparison, use `git archive HEAD`
or `git archive origin/<branch>` — not the dirty working tree.

---

## Verification hooks (after extraction or merge)

```bash
python3 scripts/review/repo_hygiene.py .
# PT only:
python3 scripts/git/check_local_runtime_overlay.py . --mode tree
# Targeted tests for touched areas
```

---

## Related

- [`local-runtime-overlay-reference-card.md`](local-runtime-overlay-reference-card.md) — PT discovery cache; never discard
- [`../../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../../git-history-surgery/references/safe-cross-host-sync-reference-card.md) — stash-first sync
- [`../../fable5-git-rebase-safety/SKILL.md`](../../fable5-git-rebase-safety/SKILL.md) — tree-twin / post-rewrite validation
- [`../SKILL.md`](../SKILL.md) — parallel worktree bootstrap
