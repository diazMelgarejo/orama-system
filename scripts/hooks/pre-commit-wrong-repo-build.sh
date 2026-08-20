#!/usr/bin/env bash
# Pre-commit hook: Verify repository target and directory bounds to prevent wrong-repo builds.
# Incident context: 2026-05-14 Wrong Repo Build incident (docs/wiki/10-wrong-repo-build-what-not-to-do.md)
set -euo pipefail

# Fail closed if git cannot resolve a repository root at all, rather than
# silently falling back to the current directory (which could be anywhere).
if ! ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "❌ [PRE-COMMIT GUARD] Could not resolve repository root via git — refusing to proceed" >&2
  exit 1
fi
cd "$ROOT"

# Check 1: Origin remote identity verification. Match the exact canonical
# owner/repo, not any URL that merely contains "orama-system" (which also
# matches a fork under a different owner, a different host, or a repo with
# an unrelated suffix like "orama-system-archive"). Check both the fetch
# URL and the push URL -- a separate push URL could target another repo
# even when the fetch URL looks correct.
_canonical_remote_re='^(https://github\.com/|git@github\.com:)(diazMelgarejo|oramasys)/orama-system(\.git)?/?$'
if git remote -v | grep -q "^origin"; then
  origin_fetch_url="$(git remote get-url origin 2>/dev/null || true)"
  origin_push_url="$(git remote get-url --push origin 2>/dev/null || true)"
  for url in "$origin_fetch_url" "$origin_push_url"; do
    if [[ -n "$url" ]] && ! [[ "$url" =~ $_canonical_remote_re ]]; then
      echo "❌ [PRE-COMMIT GUARD] Wrong origin remote detected: $url" >&2
      echo "Expected repository: diazMelgarejo/orama-system or oramasys/orama-system" >&2
      exit 1
    fi
  done
fi

# Check 2: Verify staged files are within the canonical repository root.
# NUL-delimited output so filenames with spaces, newlines, or glob
# characters are handled as single entries rather than word-split.
while IFS= read -r -d '' file; do
  if [[ "$file" == /* ]] || [[ "$file" == ../* ]]; then
    echo "❌ [PRE-COMMIT GUARD] Staged file path escapes repo boundary: $file" >&2
    exit 1
  fi
done < <(git diff --cached --name-only -z)

exit 0
