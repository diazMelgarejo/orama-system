#!/usr/bin/env bash
# install-openclaw-skills.sh — idempotent at every start.sh call and on fresh installs
set -euo pipefail

# Resolve repo root from this script's location, not the caller's cwd.
# This is safe whether start.sh is invoked from inside the repo, via an
# absolute path, or from a symlink in another directory.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)"
SKILL_ROOT="$REPO_ROOT/bin/orama-system/skills/openclaw-skills"
UPSTREAM_DIR="$SKILL_ROOT/cc-openclaw"
SUBMODULE_PATH="bin/orama-system/skills/openclaw-skills/cc-openclaw"

# 1. Always run submodule update so the working tree tracks the pinned SHA.
# The README.md guard previously skipped the update on already-initialized
# submodules, which left the working tree on a stale SHA after `git pull`
# advanced the gitlink pointer without updating the submodule checkout.
echo "[install-openclaw-skills] Syncing cc-openclaw submodule to pinned SHA..."
git -C "$REPO_ROOT" submodule update --init --recursive --progress "$SUBMODULE_PATH"

# 2. Verify Nine Skills are present (smoke check)
# Upstream stores skills in .claude/skills/<id>/SKILL.md
REQUIRED_SKILLS=(
  openclaw-new-agent openclaw-add-channel openclaw-add-cron
  openclaw-dream-setup openclaw-add-script openclaw-add-secret
  openclaw-status openclaw-restart openclaw-stow
)
for skill in "${REQUIRED_SKILLS[@]}"; do
  if [ ! -f "$UPSTREAM_DIR/skills/$skill/SKILL.md" ] && \
     [ ! -f "$UPSTREAM_DIR/.claude/skills/$skill/SKILL.md" ]; then
    echo "[install-openclaw-skills] WARNING: $skill SKILL.md not found in upstream"
  fi
done

# 3. Our extensions are already in $SKILL_ROOT — no copy needed (patch-on-top model)
echo "[install-openclaw-skills] Extensions at $SKILL_ROOT are versioned in orama-system."
echo "[install-openclaw-skills] Done."
