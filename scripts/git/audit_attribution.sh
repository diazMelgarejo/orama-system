#!/usr/bin/env bash
# Scan last N commits on refs for identity + Co-authored-by policy (commit-msg hook).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
N="${1:-79}"
HOOK="$ROOT/scripts/git/check_commit_message.sh"
refs=(HEAD main origin/main)
for ref in "${refs[@]}"; do
  sha=$(git rev-parse -q --verify "$ref" 2>/dev/null) || { printf '%s\tMISSING\t-\t-\n' "$ref"; continue; }
  verboten=0 bad_author=0 count=0
  while read -r h; do
    count=$((count+1))
    tmp=$(mktemp)
    git log -1 --format=%B "$h" > "$tmp"
    ae=$(git log -1 --format=%ae "$h")
    case "$ae" in diazMelgarejo@gmail.com|Lawrence@cyre.me) ;; *) bad_author=$((bad_author+1)) ;; esac
    [[ -x "$HOOK" ]] && "$HOOK" "$tmp" >/dev/null 2>&1 || verboten=$((verboten+1))
    rm -f "$tmp"
  done < <(git log -"$N" --format=%H "$ref")
  clean=no
  [[ $verboten -eq 0 ]] && clean=yes
  printf '%s\t%s\tverboten=%s\tbad_author=%s\tcommits=%s\tclean_new_work=%s\n' \
    "$ref" "${sha:0:12}" "$verboten" "$bad_author" "$count" "$clean"
done
