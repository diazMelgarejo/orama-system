#!/usr/bin/env bash
# Regression tests for commit-clean empty-commit guards.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
failures=0

fail() {
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}

pass() {
  echo "OK: $*"
}

run_in_repo() {
  local work="$1"
  shift
  (
    cd "$work"
    "$@"
  )
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git -C "$tmp" init -q
git -C "$tmp" config user.name "Test User"
git -C "$tmp" config user.email "codex@openai.com"
mkdir -p "$tmp/scripts/git"
for helper in commit-clean.sh verify-staged-for-commit.sh banned_attribution_lib.sh; do
  install -m 0755 "$SCRIPT_DIR/$helper" "$tmp/scripts/git/$helper"
done
printf 'base\n' >"$tmp/README.md"
git -C "$tmp" add README.md
run_in_repo "$tmp" bash "$tmp/scripts/git/commit-clean.sh" -m "init" >/dev/null

printf 'unstaged only\n' >"$tmp/README.md"

if run_in_repo "$tmp" bash "$tmp/scripts/git/commit-clean.sh" -m "should fail unstaged" >/dev/null 2>&1; then
  fail "commit-clean must reject unstaged-only working tree"
else
  pass "blocks commit when edits are unstaged"
fi

if run_in_repo "$tmp" bash "$tmp/scripts/git/verify-staged-for-commit.sh" >/dev/null 2>&1; then
  fail "verify-staged must reject empty index"
else
  pass "verify-staged rejects empty index"
fi

git -C "$tmp" add README.md
if ! run_in_repo "$tmp" bash "$tmp/scripts/git/verify-staged-for-commit.sh" >/dev/null 2>&1; then
  fail "verify-staged must accept staged delta"
else
  pass "verify-staged accepts staged delta"
fi

sha="$(run_in_repo "$tmp" bash "$tmp/scripts/git/commit-clean.sh" -m "staged commit")"
if [[ -z "$sha" ]]; then
  fail "commit-clean must return a sha for staged commit"
else
  pass "commit-clean succeeds with staged changes"
fi

if [[ "$(git -C "$tmp" rev-parse HEAD)" != "$sha" ]]; then
  fail "branch tip must advance after commit-clean"
else
  pass "branch tip advances"
fi

if ! git -C "$tmp" diff --quiet HEAD -- README.md; then
  fail "committed file must match staged content"
else
  pass "committed tree includes staged content"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "commit_clean_test: $failures failure(s)" >&2
  exit 1
fi

echo "commit_clean_test: all checks passed"
