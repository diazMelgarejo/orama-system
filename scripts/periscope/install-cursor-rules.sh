#!/usr/bin/env bash
# Install Cursor rules + git attribution guards into a periscope clone.
# Sources: orama-system scripts/periscope/* templates + scripts/git/* (when present).
set -euo pipefail

ORAMA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RULES_DIR="$ORAMA_ROOT/scripts/periscope/cursor-rules-templates"
GUARD_TPL="$ORAMA_ROOT/scripts/periscope/git-guard-templates"
GIT_SRC="$ORAMA_ROOT/scripts/git"
PERISCOPE_REPO="${PERISCOPE_REPO:-$HOME/Documents/oramasys/tools/periscope}"

GIT_FILES=(
  disable-cursor-commit-attribution.sh
  commit-clean.sh
  check_identity.sh
  check_commit_message.sh
  cursor-hooks-id.sh
  install-local-hooks.sh
  hooks/commit-msg.strip-coauthor
)

log() { printf '>>> %s\n' "$*"; }

[[ -d "$PERISCOPE_REPO/.git" ]] || {
  echo "install-cursor-rules: not a git repo: $PERISCOPE_REPO" >&2
  exit 1
}

# --- .cursor/rules ---
mkdir -p "$PERISCOPE_REPO/.cursor/rules"
for f in "$RULES_DIR"/*.mdc; do
  [[ -f "$f" ]] || continue
  dest="$PERISCOPE_REPO/.cursor/rules/$(basename "$f")"
  cp "$f" "$dest"
  log "rule: $(basename "$f")"
done

# --- scripts/git (orama canonical → origin/main → bundled templates) ---
mkdir -p "$PERISCOPE_REPO/scripts/git/hooks"
copy_git_file() {
  local rel="$1"
  local dest="$PERISCOPE_REPO/scripts/git/$rel"
  mkdir -p "$(dirname "$dest")"
  if [[ -f "$GIT_SRC/$rel" ]]; then
    cp "$GIT_SRC/$rel" "$dest"
    log "git: $rel (workspace)"
  elif git -C "$ORAMA_ROOT" show "origin/main:scripts/git/$rel" >"$dest" 2>/dev/null; then
    log "git: $rel (orama origin/main)"
  elif [[ -f "$GUARD_TPL/$(basename "$rel")" ]]; then
    cp "$GUARD_TPL/$(basename "$rel")" "$dest"
    log "git: $rel (template)"
  else
    echo "install-cursor-rules: missing $rel" >&2
    exit 1
  fi
  chmod +x "$dest" 2>/dev/null || true
}
for rel in "${GIT_FILES[@]}"; do
  copy_git_file "$rel"
done

# Periscope-specific apply script (overwrites generic if copied above)
cp "$GUARD_TPL/apply-attribution-guards.sh" "$PERISCOPE_REPO/scripts/git/apply-attribution-guards.sh"
chmod +x "$PERISCOPE_REPO/scripts/git/apply-attribution-guards.sh"

# --- AGENTS.md snippet (idempotent) ---
AGENTS_SNIP="$GUARD_TPL/AGENTS-cursor-cloud-git.md"
if [[ -f "$PERISCOPE_REPO/AGENTS.md" ]] && [[ -f "$AGENTS_SNIP" ]]; then
  if ! grep -q "## Cursor Cloud: git commits" "$PERISCOPE_REPO/AGENTS.md"; then
    printf '\n' >> "$PERISCOPE_REPO/AGENTS.md"
    cat "$AGENTS_SNIP" >> "$PERISCOPE_REPO/AGENTS.md"
    log "AGENTS.md: appended Cursor Cloud git section"
  else
    log "AGENTS.md: Cursor Cloud git section already present"
  fi
fi

bash "$PERISCOPE_REPO/scripts/git/apply-attribution-guards.sh" 2>/dev/null || true

log "OK: installed rules + scripts/git under $PERISCOPE_REPO"
