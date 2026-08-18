#!/usr/bin/env bash
# Pre-commit hook: Verify repository target and directory bounds to prevent wrong-repo builds.
# Incident context: 2026-05-14 Wrong Repo Build incident (docs/wiki/10-wrong-repo-build-what-not-to-do.md)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# Check 1: Origin remote identity verification
if git remote -v | grep -q "origin"; then
  origin_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -n "$origin_url" ]] && ! echo "$origin_url" | grep -qE "diazMelgarejo/orama-system|oramasys/orama-system|orama-system"; then
    echo "❌ [PRE-COMMIT GUARD] Wrong origin remote detected: $origin_url" >&2
    echo "Expected repository: diazMelgarejo/orama-system" >&2
    exit 1
  fi
fi

# Check 2: Verify staged files are within the canonical repository root
staged_files="$(git diff --cached --name-only 2>/dev/null || true)"
if [[ -n "$staged_files" ]]; then
  for file in $staged_files; do
    if [[ "$file" == /* ]] || [[ "$file" == ../* ]]; then
      echo "❌ [PRE-COMMIT GUARD] Staged file path escapes repo boundary: $file" >&2
      exit 1
    fi
  done
fi

exit 0
