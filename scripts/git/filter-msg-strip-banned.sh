#!/usr/bin/env bash
# git filter-branch --msg-filter helper: scrub banned attribution from messages.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
FILTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$FILTER_DIR/banned_attribution_lib.sh" ]]; then
  # shellcheck source=banned_attribution_lib.sh
  source "$FILTER_DIR/banned_attribution_lib.sh"
elif [[ -f "$REPO_ROOT/scripts/git/banned_attribution_lib.sh" ]]; then
  # shellcheck source=banned_attribution_lib.sh
  source "$REPO_ROOT/scripts/git/banned_attribution_lib.sh"
else
  PT_GUARD="${PERPETUA_TOOLS_GUARD:-/agent/repos/Perpetua-Tools}"
  # shellcheck source=banned_attribution_lib.sh
  source "$PT_GUARD/scripts/git/banned_attribution_lib.sh"
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  line_lc="$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')"
  case "$line_lc" in
    co-authored-by:*)
      if coauthor_line_should_drop "$line_lc" "$REPO_ROOT"; then
        continue
      fi
      ;;
  esac
  if line_matches_banned_pattern "$line_lc" "$REPO_ROOT" \
    || line_matches_private_forbidden_literal "$line_lc" "$REPO_ROOT"; then
    continue
  fi
  printf '%s\n' "$line"
done
