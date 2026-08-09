#!/usr/bin/env bash
# Force-publish rewritten refs to origin (hooks off). Run after local expunge completes.
#
# Usage:
#   post-rewrite-publish.sh [repo_path]
#
# Env:
#   PUSH_MAIN=1          force-push main (default 1)
#   PUSH_ALL_BRANCHES=1  force-push every local branch (default 0)
#   ALLOW_MAIN_PUSH=1    required for repos with Phase 0 main guard
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
cd "$REPO"

PUSH_MAIN="${PUSH_MAIN:-1}"
PUSH_ALL_BRANCHES="${PUSH_ALL_BRANCHES:-0}"
export HISTORY_SURGERY_ACTIVE=1
export ALLOW_MAIN_PUSH="${ALLOW_MAIN_PUSH:-1}"

PUSH=(bash "$SCRIPT_DIR/history-surgery-push.sh")
if [[ ! -x "$SCRIPT_DIR/history-surgery-push.sh" ]]; then
  PUSH=(git -c core.hooksPath=/dev/null push)
fi

cleanup_publish() {
  local cleanup_failed=0
  unset HISTORY_SURGERY_ACTIVE
  if [[ -x "$SCRIPT_DIR/install-local-hooks.sh" ]]; then
    bash "$SCRIPT_DIR/install-local-hooks.sh" || cleanup_failed=1
  fi
  return "$cleanup_failed"
}
trap 'status=$?; trap - EXIT; cleanup_status=0; cleanup_publish || cleanup_status=$?; if [[ $status -ne 0 ]]; then exit $status; fi; exit $cleanup_status' EXIT

git fetch origin --prune 2>/dev/null || true

if [[ "$PUSH_MAIN" == "1" ]]; then
  echo ">>> force-push main (hooks off)"
  main_old_sha="$(git rev-parse origin/main)"
  "${PUSH[@]}" --force-with-lease="refs/heads/main:${main_old_sha}" origin main:main
fi

if [[ "$PUSH_ALL_BRANCHES" == "1" ]]; then
  echo ">>> force-push all local branches (hooks off)"
  failed_branches=()
  while IFS= read -r branch; do
    [[ -n "$branch" ]] || continue
    [[ "$branch" == "main" ]] && continue
    echo "  $branch"
    old_sha=""
    if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
      old_sha="$(git rev-parse "origin/$branch")"
    fi
    if [[ -n "$old_sha" ]]; then
      "${PUSH[@]}" --force-with-lease="refs/heads/${branch}:${old_sha}" \
        origin "${branch}:${branch}" || failed_branches+=("$branch")
    else
      "${PUSH[@]}" -u origin "${branch}:${branch}" || failed_branches+=("$branch")
    fi
  done < <(git for-each-ref refs/heads --format='%(refname:short)')
  if [[ "${#failed_branches[@]}" -gt 0 ]]; then
    printf 'ERROR: failed to publish rewritten branch(es): %s\n' "${failed_branches[*]}" >&2
    exit 1
  fi
fi

echo "OK: post-rewrite-publish complete for $(basename "$PWD")"
