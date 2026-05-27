#!/usr/bin/env bash
# Verify user-level + repo-level git guards are active (cloud VM or local).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOME="${HOME:-/home/ubuntu}"
errors=0

fail() {
  echo "FAIL: $*" >&2
  errors=$((errors + 1))
}

ok() {
  echo "OK: $*"
}

cd "$REPO_ROOT"

if [[ ! -x "${HOME}/.cursor/openclaw/hooks/session-apply-git-guards.sh" ]]; then
  fail "missing ${HOME}/.cursor/openclaw/hooks/session-apply-git-guards.sh (run install-user-git-environment.sh)"
else
  ok "user session hook installed"
fi

if [[ ! -f "${HOME}/.cursor/hooks.json" ]]; then
  fail "missing ${HOME}/.cursor/hooks.json"
else
  ok "user hooks.json present"
fi

hooks_path="$(git config --local --get core.hooksPath 2>/dev/null || true)"
if [[ "$hooks_path" != ".githooks" ]]; then
  fail "core.hooksPath=${hooks_path:-<unset>} expected .githooks"
else
  ok "core.hooksPath=.githooks"
fi

email="$(git config --local user.email 2>/dev/null || true)"
if [[ "$email" != "diazMelgarejo@gmail.com" ]]; then
  fail "user.email=${email:-<unset>} expected diazMelgarejo@gmail.com"
else
  ok "user.email=diazMelgarejo@gmail.com"
fi

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/git/cursor-hooks-id.sh"
ws_id="$(cursor_hooks_id "$REPO_ROOT")"
coauthor="${HOME}/.cursor/agent-hooks/${ws_id}/commit-msg.cursor.co-author"
if [[ -f "$coauthor" && -x "$coauthor" ]]; then
  fail "Cursor co-author hook still executable: $coauthor"
else
  ok "Cursor co-author hook disabled or absent"
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
cat >"$tmp" <<'MSG'
test: verify guards

Co-authored-by: random <unknown-person@random-domain-xyz.io>
MSG
if bash "${REPO_ROOT}/scripts/git/check_commit_message.sh" "$tmp" 2>/dev/null; then
  fail "check_commit_message.sh should reject unlisted co-author"
else
  ok "commit-msg policy blocks unlisted co-author"
fi

if [[ "$errors" -gt 0 ]]; then
  echo "verify-git-guards: $errors failure(s)" >&2
  exit 1
fi
echo "verify-git-guards: all checks passed"
