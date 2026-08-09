#!/usr/bin/env bash
# Write gitignored banned-attribution pattern files from local-only registries.
# Never embed forbidden tokens in tracked repository source.
set -euo pipefail

DEST="${1:-}"
if [[ -z "$DEST" ]]; then
  echo "usage: seed-banned-attribution-patterns.sh <dest-file>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../git/banned_attribution_lib.sh
source "$SCRIPT_DIR/../git/banned_attribution_lib.sh"

declare -A seen=()
tokens=()

_add_token() {
  local raw="$1" key
  raw="${raw%%#*}"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  [[ -n "$raw" ]] || return 0
  key="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  [[ -n "${seen[$key]:-}" ]] && return 0
  seen[$key]=1
  tokens+=("$raw")
}

if [[ -n "${OPENCLAW_BANNED_ATTRIBUTION_SEED_FILE:-}" && -f "${OPENCLAW_BANNED_ATTRIBUTION_SEED_FILE}" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    _add_token "$line"
  done <"${OPENCLAW_BANNED_ATTRIBUTION_SEED_FILE}"
fi

while IFS= read -r token; do
  _add_token "$token"
done < <(list_private_literal_values "$ORAMA_ROOT" forbidden_attribution 2>/dev/null || true)

# Resolve via the shared registry lookup (honors OPENCLAW_ATTRIBUTION_PATTERNS
# when set) instead of hardcoding the default ~/.cursor/openclaw path -- a
# configured override pointing elsewhere was previously silently ignored by
# this guard even though list_banned_pattern_tokens itself already resolves
# it correctly.
CONFIGURED_PATTERNS="$(banned_patterns_file "$ORAMA_ROOT")"
if [[ -f "$CONFIGURED_PATTERNS" ]]; then
  while IFS= read -r token; do
    _add_token "$token"
  done < <(list_banned_pattern_tokens "$ORAMA_ROOT" 2>/dev/null || true)
fi

if [[ "${#tokens[@]}" -eq 0 ]]; then
  echo "ERROR: no banned-attribution seed tokens found" >&2
  echo "Provide OPENCLAW_BANNED_ATTRIBUTION_SEED_FILE or workspace .verboten-literals.local forbidden_attribution= lines." >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
{
  echo "# Banned attribution tokens (one per line, case-insensitive substring match)"
  for token in "${tokens[@]}"; do
    printf '%s\n' "$token"
  done
} >"$DEST"
chmod 600 "$DEST" 2>/dev/null || true
printf 'OK: %s (%s token(s))\n' "$DEST" "${#tokens[@]}"
