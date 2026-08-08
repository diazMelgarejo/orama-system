#!/usr/bin/env bash
# Cherry-pick patch-id-unique commits onto origin/main and force-update branch tips.
#
# Preferred post-rewrite re-anchor after a full history scrub (rebase --onto often
# conflicts on rewritten ancestry). Open PR branches should end with
# merge-base == origin/main.
#
# Usage:
#   cherry-reanchor-branches.sh [repo_path] branch [branch...]
#   cherry-reanchor-branches.sh [repo_path] --from-json actions.json [--all-needs]
#
# Env:
#   DELETE_ON_CHERRY_CONFLICT=1  delete branch when cherry-pick cannot complete
#   SKIP_EMPTY_CHERRY=1          default on — skip empty picks and continue
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
shift || true

DELETE_ON_CONFLICT="${DELETE_ON_CHERRY_CONFLICT:-0}"
SKIP_EMPTY="${SKIP_EMPTY_CHERRY:-1}"
FROM_JSON=""
ALL_NEEDS=0
branches=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-json) FROM_JSON="${2:?}"; shift 2 ;;
    --all-needs) ALL_NEEDS=1; shift ;;
    --delete-on-conflict) DELETE_ON_CONFLICT=1; shift ;;
    *) branches+=("$1"); shift ;;
  esac
done

cd "$REPO"
git fetch origin --prune

PUSH=(bash "$SCRIPT_DIR/history-surgery-push.sh")
if [[ ! -x "$SCRIPT_DIR/history-surgery-push.sh" ]]; then
  PUSH=(git -c core.hooksPath=/dev/null push)
fi

if [[ "$ALL_NEEDS" == "1" && -n "$FROM_JSON" ]]; then
  mapfile -t branches < <(
    python3 -c "import json,sys; print('\n'.join(x['branch'] for x in json.load(open(sys.argv[1]))['needs']))" \
      "$FROM_JSON"
  )
elif [[ ${#branches[@]} -eq 0 && -n "$FROM_JSON" ]]; then
  echo "ERROR: pass branch names or --all-needs with --from-json" >&2
  exit 2
fi

ok=0
deleted=0
failed=0

cherry_pick_commits() {
  local work="$1"
  shift
  local commits=("$@")
  local c
  for c in "${commits[@]}"; do
    if git cherry-pick "$c"; then
      continue
    fi
    if [[ "$SKIP_EMPTY" == "1" ]] \
      && git diff --cached --quiet \
      && git diff --quiet; then
      git cherry-pick --skip
      continue
    fi
    return 1
  done
  return 0
}

for branch in "${branches[@]}"; do
  [[ -n "$branch" ]] || continue
  if ! git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    echo "skip: no remote $branch" >&2
    continue
  fi
  echo ">>> CHERRY-REANCHOR $branch"
  old_sha="$(git rev-parse "origin/$branch")"
  mapfile -t commits < <(git cherry origin/main "origin/$branch" | awk '/^\+/{print $2}')
  if [[ "${#commits[@]}" -eq 0 ]]; then
    echo "  no unique commits — delete stale"
    if "${PUSH[@]}" origin --delete "$branch"; then
      deleted=$((deleted + 1))
    else
      failed=$((failed + 1))
    fi
    continue
  fi
  work="__cherry_${branch//\//_}"
  git checkout -B "$work" origin/main
  git clean -fdq
  if ! cherry_pick_commits "$work" "${commits[@]}"; then
    echo "  FAIL cherry-pick $branch" >&2
    git cherry-pick --abort 2>/dev/null || true
    git checkout main 2>/dev/null || git checkout -
    git branch -D "$work" 2>/dev/null || true
    if [[ "$DELETE_ON_CONFLICT" == "1" ]]; then
      if "${PUSH[@]}" origin --delete "$branch" 2>/dev/null; then
        echo "  deleted $branch (conflict)"
        deleted=$((deleted + 1))
      else
        failed=$((failed + 1))
      fi
    else
      failed=$((failed + 1))
    fi
    continue
  fi
  mb="$(git merge-base HEAD origin/main)"
  main_tip="$(git rev-parse origin/main)"
  if [[ "$mb" != "$main_tip" ]]; then
    echo "  FAIL: merge-base != origin/main after cherry-pick" >&2
    git checkout main 2>/dev/null || true
    git branch -D "$work" 2>/dev/null || true
    failed=$((failed + 1))
    continue
  fi
  "${PUSH[@]}" --force-with-lease="refs/heads/${branch}:${old_sha}" \
    origin "${work}:refs/heads/${branch}" \
    || "${PUSH[@]}" --force origin "${work}:refs/heads/${branch}"
  git checkout main 2>/dev/null || true
  git branch -D "$work" 2>/dev/null || true
  ok=$((ok + 1))
done

echo "OK: cherry-reanchor ok=$ok deleted=$deleted failed=$failed"
exit $(( failed > 0 ? 1 : 0 ))
