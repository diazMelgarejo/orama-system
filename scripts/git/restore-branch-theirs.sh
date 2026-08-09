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
commits=()
while IFS= read -r commit; do
  [[ -n "$commit" ]] && commits+=("$commit")
done < <(git cherry origin/main "$source_ref" | awk '/^\+/{print $2}')
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
old_sha=""
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  old_sha="$(git rev-parse "origin/$BRANCH")"
fi
work_dir="$(mktemp -d)"
if ! git worktree add -B "$work" "$work_dir" origin/main >/dev/null; then
  echo "ERROR: could not create disposable worktree for $BRANCH" >&2
  rm -rf "$work_dir"
  exit 1
fi

cleanup_restore_worktree() {
  if [[ -n "${work_dir:-}" && -d "$work_dir" ]]; then
    git -C "$work_dir" cherry-pick --abort 2>/dev/null || true
    git worktree remove --force "$work_dir" 2>/dev/null || rm -rf "$work_dir"
    work_dir=""
  fi
  git branch -D "$work" 2>/dev/null || true
}
trap 'status=$?; trap - EXIT; cleanup_restore_worktree; exit $status' EXIT

if ! (
  cd "$work_dir"
  for c in "${commits[@]}"; do
    if git cherry-pick -X theirs "$c"; then
      echo "  OK $c"
      continue
    fi
    if git rev-parse --verify CHERRY_PICK_HEAD >/dev/null 2>&1 \
      && git diff-index --quiet HEAD -- 2>/dev/null; then
      echo "  SKIP empty $c"
      git cherry-pick --skip
      continue
    fi
    if git rev-parse --verify CHERRY_PICK_HEAD >/dev/null 2>&1; then
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
); then
  exit 1
fi

final_tree="$(git -C "$work_dir" rev-parse 'HEAD^{tree}')"
if [[ "$final_tree" != "$target_tree" ]]; then
  echo "WARN: tree mismatch for $BRANCH — aligning from source tip"
  git -C "$work_dir" checkout "$source_ref" -- .
  git -C "$work_dir" add -A
  if ! git -C "$work_dir" diff --cached --quiet; then
    git -C "$work_dir" commit -m "fix(restore): align $BRANCH tree after cherry-reanchor onto origin/main"
  fi
fi

mb="$(git -C "$work_dir" merge-base HEAD origin/main)"
main_tip="$(git rev-parse origin/main)"
if [[ "$mb" != "$main_tip" ]]; then
  echo "FAIL: merge-base != main" >&2
  exit 1
fi

if [[ -n "$old_sha" ]]; then
  if ! push_git --force-with-lease="refs/heads/${BRANCH}:${old_sha}" \
    origin "${work}:refs/heads/${BRANCH}"; then
    echo "FAIL: lease rejected for $BRANCH; fetch/review and retry with a fresh recorded lease" >&2
    exit 1
  fi
else
  if ! push_git -u origin "${work}:refs/heads/${BRANCH}"; then
    echo "FAIL: push failed for new remote branch $BRANCH" >&2
    exit 1
  fi
fi

cleanup_restore_worktree
trap - EXIT
git fetch origin "$BRANCH" 2>/dev/null || true
tip="$(git rev-parse "origin/$BRANCH" 2>/dev/null || git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
echo "OK: restored $BRANCH -> $tip"
