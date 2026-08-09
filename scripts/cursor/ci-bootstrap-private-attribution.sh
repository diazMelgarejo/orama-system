#!/usr/bin/env bash
# Self-contained CI bootstrap for gitignored attribution patterns (no orama checkout required).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOME="${HOME:-/home/ubuntu}"
OPENCLAW="${HOME}/.cursor/openclaw"
PRIVATE="${REPO_ROOT}/.cursor/private"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OPENCLAW/private-lessons" "$PRIVATE"
chmod 700 "$OPENCLAW" "$PRIVATE" 2>/dev/null || true

PATTERNS_OPENCLAW="${OPENCLAW}/banned-attribution-patterns"
if [[ -s "$PATTERNS_OPENCLAW" && -s "${PRIVATE}/banned-attribution-patterns" ]]; then
  printf 'OK: CI bootstrap already present → %s\n' "$PATTERNS_OPENCLAW"
  exit 0
fi

if ! bash "$SCRIPT_DIR/seed-banned-attribution-patterns.sh" "$PATTERNS_OPENCLAW" 2>/dev/null; then
  # No local-only registry available (expected in CI -- registries are
  # workspace-local by design, never checked into the repo; see
  # docs/v2/47-portable-memory-local-topology-invariant.md). Fall back to a
  # placeholder so the mandatory hooks-active/attribution-guard steps below
  # can still run; they don't depend on this file's literal contents.
  {
    echo "# Banned attribution tokens (one per line, case-insensitive substring match)"
    echo "REDACTED"
  } >"$PATTERNS_OPENCLAW"
  chmod 600 "$PATTERNS_OPENCLAW"
fi
install -m 0600 "$PATTERNS_OPENCLAW" "${PRIVATE}/banned-attribution-patterns"

printf 'OK: CI bootstrap → %s and %s\n' "$PATTERNS_OPENCLAW" "${PRIVATE}/banned-attribution-patterns"
