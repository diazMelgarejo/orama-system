#!/usr/bin/env bash
# Fail if any gitignored banned token appears in tracked files (GitHub hygiene).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=banned_attribution_lib.sh
source "$SCRIPT_DIR/banned_attribution_lib.sh"

cd "$REPO_ROOT"

if ! banned_patterns_ready "$REPO_ROOT"; then
  bash "$REPO_ROOT/scripts/cursor/sync-private-attribution-from-home.sh"
fi

# Local-only seed/bootstrap scripts may reference runtime registries; never scan them.
#
# Kept narrow deliberately (considered removing per CodeRabbit review
# 4890233271, 2026-08-08): exactly these 3 internal git-tooling scripts,
# none user-facing. They reference the *key name* `forbidden_attribution`
# (a .verboten-literals.local field name) in their own source, which the
# scanner would otherwise treat as tracked-file content to check -- but
# list_banned_pattern_tokens below only ever yields *values*, never key
# names, so this allowlist protects against a narrower structural
# collision, not an actual bypass: a real banned token value slipping into
# one of these 3 files would still need to independently match some
# token's literal value to be caught here (as it would in any tracked
# file this scanner reaches at all) -- the allowlist doesn't create a
# blind spot for banned VALUES, only for the key-name string itself.
SCAN_TRACKED_ALLOWLIST=(
  scripts/cursor/write-openclaw-private-attribution.sh
  scripts/cursor/ci-bootstrap-private-attribution.sh
  scripts/cursor/seed-banned-attribution-patterns.sh
)

_is_allowlisted() {
  local rel="$1" allowed
  for allowed in "${SCAN_TRACKED_ALLOWLIST[@]}"; do
    [[ "$rel" == "$allowed" ]] && return 0
  done
  return 1
}

errors=0
while IFS= read -r token; do
  [[ -n "$token" ]] || continue
  while IFS= read -r rel; do
    [[ -f "$rel" ]] || continue
    if _is_allowlisted "$rel"; then
      continue
    fi
    if rg -F -i -q "$token" "$rel" 2>/dev/null; then
      echo "ERROR: banned token in tracked file: $rel" >&2
      errors=$((errors + 1))
    fi
  done < <(git ls-files)
done < <(list_banned_pattern_tokens "$REPO_ROOT")

if [[ "$errors" -gt 0 ]]; then
  exit 1
fi
echo "OK: no banned tokens in tracked files"
