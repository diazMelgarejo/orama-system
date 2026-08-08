#!/usr/bin/env bash
# Restore one branch onto origin/main, preferring incoming patch on conflicts.
# Verifies final tree matches the source tip when possible.
#
# Usage: restore-branch-theirs.sh [repo_path] <branch-name>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
BRANCH="${2:?branch name required}"
cd "$REPO"
git fetch origin --prune

source_ref=""
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  source_ref="origin/$BRANCH"
elif git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  source_ref="$BRANCH"
else
  echo "ERROR: no source for $BRANCH" >&2
  exit 1
fi

target_tree="$(git rev-parse "$source_ref^{tree}")"
mapfile -t commits < <(git cherry origin/main "$source_ref" | awk '/^\+/{print $2}')
if [[ "${#commits[@]}" -eq 0 ]]; then
  echo "skip: $BRANCH has no unique commits vs origin/main"
  exit 0
fi

push_git() {
  if [[ -x "$SCRIPT_DIR/history-surgery-push.sh" ]]; then
    bash "$SCRIPT_DIR/history-surgery-push.sh" "$@"
  else
    git -c core.hooksPath=/dev/null push "$@"
  fi
}

work="__restore_${BRANCH//\//_}"
git checkout -B "$work" origin/main
git clean -fdq

for c in "${commits[@]}"; do
  if git cherry-pick -X theirs "$c"; then
    echo "  OK $c"
    continue
  fi
  if [[ -f .git/CHERRY_PICK_HEAD ]] && git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "  SKIP empty $c"
    git cherry-pick --skip
    continue
  fi
  if [[ -f .git/CHERRY_PICK_HEAD ]]; then
    while IFS= read -r f; do
      [[ -n "$f" ]] || continue
      git checkout --theirs -- "$f" 2>/dev/null || git rm -f -- "$f" 2>/dev/null || true
      git add -- "$f" 2>/dev/null || true
    done < <(git diff --name-only --diff-filter=U)
    if git diff --cached --quiet; then
      git cherry-pick --skip
      echo "  SKIP empty-after-theirs $c"
      continue
    fi
    git cherry-pick --continue --no-edit
    echo "  RESOLVED $c"
    continue
  fi
  echo "  FAIL $c" >&2
  git cherry-pick --abort 2>/dev/null || true
  exit 1
done

final_tree="$(git rev-parse HEAD^{tree})"
if [[ "$final_tree" != "$target_tree" ]]; then
  echo "WARN: tree mismatch for $BRANCH — aligning from source tip"
  git checkout "$source_ref" -- .
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "fix(restore): align $BRANCH tree after cherry-reanchor onto origin/main"
  fi
fi

mb="$(git merge-base HEAD origin/main)"
main_tip="$(git rev-parse origin/main)"
[[ "$mb" == "$main_tip" ]] || { echo "FAIL: merge-base != main" >&2; exit 1; }

if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  push_git --force origin "${work}:refs/heads/${BRANCH}"
else
  push_git -u origin "${work}:refs/heads/${BRANCH}"
fi

git branch -D "$work" 2>/dev/null || true
git fetch origin "$BRANCH" 2>/dev/null || true
tip="$(git rev-parse "origin/$BRANCH" 2>/dev/null || git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
echo "OK: restored $BRANCH -> $tip"
