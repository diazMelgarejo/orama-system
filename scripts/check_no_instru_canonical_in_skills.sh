#!/usr/bin/env bash
# Guard (CLAUDE-instru progressive weaning, 2026-05-23 plan): no skill may cite
# CLAUDE-instru as its Canonical source. Prevents the dependency from regressing.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HITS=$(rg -l 'Canonical:.*CLAUDE-instru' "$ROOT/bin/orama-system/skills" 2>/dev/null || true)
if [ -n "$HITS" ]; then
  echo "FAIL: skills still cite CLAUDE-instru as Canonical (weaning regression):" >&2
  echo "$HITS" >&2
  exit 1
fi
echo "OK: no CLAUDE-instru canonical refs in bin/orama-system/skills"
