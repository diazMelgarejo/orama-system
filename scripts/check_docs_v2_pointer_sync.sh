#!/usr/bin/env bash
# Pre-commit glue (orama side): when a canonical docs/v2 decision changes, verify
# the downstream Perpetua-Tools pointer is still in sync. The sync LOGIC is
# canonical here in orama (scripts/git/sync-docs-v2-pointers.sh) — this glue only
# locates the sibling PT checkout and delegates. Skips gracefully when PT is not a
# sibling (e.g. GitHub CI), so it never blocks a clean canonical-only commit.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for cand in "${PERPETUA_TOOLS_ROOT:-}" \
            "$ROOT/../perplexity-api/Perpetua-Tools"; do
  [[ -n "$cand" && -d "$cand/.git" ]] || continue
  exec bash "$ROOT/scripts/git/sync-docs-v2-pointers.sh" --check "$cand"
done
echo "skip: Perpetua-Tools not found as sibling (set PERPETUA_TOOLS_ROOT to enable docs/v2 pointer sync check)" >&2
exit 0
