#!/usr/bin/env bash
# install-skills.sh — refresh the user-global Claude skills from this repo.
#
# Copy + auto-resync model (decided 2026-06-10): the global skills under
# ~/.claude/skills are real-dir COPIES, not symlinks. This keeps them available
# even when the (volatile) orama-system checkout briefly vanishes — the last good
# copy persists. start.sh runs this every session start so the copies stay current.
#
# Additive by design: rsync WITHOUT --delete, so any global-only content (e.g. a
# locally-installed sub-skill not tracked here) is preserved. Idempotent and safe
# to run repeatedly. No-op (exit 0) if HOME or the repo skills are unavailable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_HOME="${HOME:-}/.claude/skills"

if [ -z "${HOME:-}" ]; then
  echo "[install-skills] HOME unset — skipping" >&2
  exit 0
fi
if ! command -v rsync >/dev/null 2>&1; then
  echo "[install-skills] rsync not found — skipping" >&2
  exit 0
fi

mkdir -p "$SKILLS_HOME"

# repo source dir  ->  global skill name
# Keep this list in sync with the canonical skill homes in the repo.
sync_one() {
  local src="$1" name="$2"
  if [ ! -d "$REPO_ROOT/$src" ]; then
    echo "[install-skills] source missing, skipping: $src" >&2
    return 0
  fi
  rsync -a "$REPO_ROOT/$src/" "$SKILLS_HOME/$name/"
  echo "[install-skills] synced $name <- $src"
}

sync_one "bin/orama-system"                       "orama-system"
sync_one "bin/orama-system/skills/oramasys-method" "oramasys-method"
sync_one ".claude/skills/agent-methodology"        "agent-methodology"

# Drop files that were renamed in-repo (rsync without --delete can't remove them).
# The 5-stage methodology reference was renamed ultrathink-5-stages.md ->
# oramasys-5-stages.md; clear the stale copy so global matches the repo.
rm -f "$SKILLS_HOME/orama-system/references/ultrathink-5-stages.md" 2>/dev/null || true

echo "[install-skills] done (copy + auto-resync; global skills current with repo)"
