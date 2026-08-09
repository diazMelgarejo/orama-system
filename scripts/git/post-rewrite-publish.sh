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

git fetch origin --prune 2>/dev/null || true

if [[ "$PUSH_MAIN" == "1" ]]; then
  echo ">>> force-push main (hooks off)"
  "${PUSH[@]}" --force origin main:main \
    || "${PUSH[@]}" --force-with-lease origin main:main
fi

if [[ "$PUSH_ALL_BRANCHES" == "1" ]]; then
  echo ">>> force-push all local branches (hooks off)"
  while read -r branch; do
    [[ -n "$branch" ]] || continue
    [[ "$branch" == "main" ]] && continue
    echo "  $branch"
    "${PUSH[@]}" --force-with-lease origin "${branch}:${branch}" 2>/dev/null \
      || "${PUSH[@]}" --force origin "${branch}:${branch}" 2>/dev/null \
      || echo "warn: push failed $branch" >&2
  done < <(git for-each-ref refs/heads --format='%(refname:short)')
fi

unset HISTORY_SURGERY_ACTIVE
if [[ -x scripts/git/install-local-hooks.sh ]]; then
  bash scripts/git/install-local-hooks.sh
fi

echo "OK: post-rewrite-publish complete for $(basename "$PWD")"
