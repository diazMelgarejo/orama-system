#!/usr/bin/env bash
# git filter-branch --env-filter helper: remap author/committer when banned.
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

_scrub_identity_field() {
  local value="$1"
  local value_lc
  value_lc="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  if identity_field_should_scrub "$value_lc" "$REPO_ROOT"; then
    return 0
  fi
  return 1
}

if _scrub_identity_field "${GIT_AUTHOR_NAME:-}" || _scrub_identity_field "${GIT_AUTHOR_EMAIL:-}"; then
  GIT_AUTHOR_NAME="$(expunge_fallback_name)"
  GIT_AUTHOR_EMAIL="$(expunge_fallback_email)"
fi

if _scrub_identity_field "${GIT_COMMITTER_NAME:-}" || _scrub_identity_field "${GIT_COMMITTER_EMAIL:-}"; then
  GIT_COMMITTER_NAME="$(expunge_fallback_name)"
  GIT_COMMITTER_EMAIL="$(expunge_fallback_email)"
fi

export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
