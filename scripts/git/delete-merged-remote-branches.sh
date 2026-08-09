#!/usr/bin/env bash
# Delete remote branches whose tips are already tree-twins in origin/main.
#
# Usage:
#   delete-merged-remote-branches.sh [repo_path] [--dry-run]
#   delete-merged-remote-branches.sh [repo_path] --from-json actions.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
shift || true
DRY_RUN=0
FROM_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --from-json) FROM_JSON="${2:?}"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

cd "$REPO"
git fetch origin --prune

PUSH=(bash "$SCRIPT_DIR/history-surgery-push.sh")
if [[ ! -x "$SCRIPT_DIR/history-surgery-push.sh" ]]; then
  PUSH=(git -c core.hooksPath=/dev/null push)
fi

branches=()
if [[ -n "$FROM_JSON" ]]; then
  branch_list="$(mktemp)"
  if ! python3 -c "import json,sys; print('\n'.join(json.load(open(sys.argv[1]))['merged']))" \
      "$FROM_JSON" >"$branch_list"; then
    echo "ERROR: failed to parse merged branches from $FROM_JSON" >&2
    rm -f "$branch_list"
    exit 1
  fi
  while IFS= read -r branch; do
    [[ -n "$branch" ]] && branches+=("$branch")
  done < "$branch_list"
  rm -f "$branch_list"
else
  scan="$(mktemp)"
  bash "$SCRIPT_DIR/reanchor_scan.sh" "$REPO" origin/main remotes >"$scan"
  branch_list="$(mktemp)"
  if ! python3 "$SCRIPT_DIR/parse-reanchor-scan.py" "$scan" \
      | python3 -c "import json,sys; print('\n'.join(json.load(sys.stdin)['merged']))" \
      >"$branch_list"; then
    echo "ERROR: failed to parse reanchor scan output" >&2
    rm -f "$scan" "$branch_list"
    exit 1
  fi
  while IFS= read -r branch; do
    [[ -n "$branch" ]] && branches+=("$branch")
  done < "$branch_list"
  rm -f "$scan" "$branch_list"
fi

deleted=0
skipped=0
if [[ "${#branches[@]}" -gt 0 ]]; then
  for branch in "${branches[@]}"; do
    [[ -n "$branch" ]] || continue
    [[ "$branch" == "main" ]] && continue
    if ! git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
      skipped=$((skipped + 1))
      continue
    fi
    echo ">>> DELETE merged remote $branch"
    if [[ "$DRY_RUN" == "1" ]]; then
      deleted=$((deleted + 1))
      continue
    fi
    if "${PUSH[@]}" origin --delete "$branch"; then
      deleted=$((deleted + 1))
    else
      echo "warn: delete failed $branch" >&2
    fi
  done
fi

echo "OK: delete-merged-remote-branches deleted=$deleted skipped=$skipped dry_run=$DRY_RUN"
