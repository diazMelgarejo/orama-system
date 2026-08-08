#!/usr/bin/env bash
# Rewrite all refs to scrub banned attribution from commit metadata (history expunge).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${1:-}" && -d "${1}/.git" ]]; then
  REPO_ROOT="$(cd "$1" && pwd)"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
MSG_FILTER="$SCRIPT_DIR/filter-msg-strip-banned.sh"
ENV_FILTER="$SCRIPT_DIR/filter-env-scrub-banned.sh"
# shellcheck source=banned_attribution_lib.sh
source "$SCRIPT_DIR/banned_attribution_lib.sh"

cd "$REPO_ROOT"

if [[ -x scripts/cursor/sync-private-attribution-from-home.sh ]]; then
  bash scripts/cursor/sync-private-attribution-from-home.sh
fi

if ! banned_patterns_ready "$REPO_ROOT"; then
  echo "ERROR: .cursor/private/banned-attribution-patterns missing" >&2
  exit 1
fi

chmod +x "$MSG_FILTER" "$ENV_FILTER"

echo "Rewriting commit metadata (all refs): author/committer remap + message scrub…"
export FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch -f \
  --env-filter "REPO_ROOT='$REPO_ROOT' bash '$ENV_FILTER'" \
  --msg-filter "REPO_ROOT='$REPO_ROOT' bash '$MSG_FILTER'" \
  --tag-name-filter cat -- --all

git for-each-ref --format='%(refname)' refs/original/ 2>/dev/null | while read -r ref; do
  git update-ref -d "$ref" 2>/dev/null || true
done

git reflog expire --expire=now --all
git gc --prune=now --aggressive

while IFS= read -r h; do
  ae_lc="$(git log -1 --format=%ae "$h" | tr '[:upper:]' '[:lower:]')"
  an_lc="$(git log -1 --format=%an "$h" | tr '[:upper:]' '[:lower:]')"
  ce_lc="$(git log -1 --format=%ce "$h" | tr '[:upper:]' '[:lower:]')"
  cn_lc="$(git log -1 --format=%cn "$h" | tr '[:upper:]' '[:lower:]')"
  body_lc="$(git log -1 --format=%B "$h" | tr '[:upper:]' '[:lower:]')"
  if metadata_contains_scrub_target "$ae_lc" "$an_lc" "$ce_lc" "$cn_lc" "$body_lc" "$REPO_ROOT"; then
    echo "FAIL: banned attribution metadata still on $h" >&2
    exit 1
  fi
done < <(git rev-list --all)
echo "OK: no banned attribution metadata remains in any reachable commit"
