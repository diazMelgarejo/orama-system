#!/usr/bin/env bash
# install-openclaw-skills.sh — idempotent at every start.sh call and on fresh installs
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILL_ROOT="$REPO_ROOT/bin/orama-system/skills/openclaw-skills"
UPSTREAM_DIR="$SKILL_ROOT/cc-openclaw"

# 1. Initialize submodule if missing
if [ ! -f "$UPSTREAM_DIR/README.md" ]; then
  echo "[install-openclaw-skills] Initializing cc-openclaw submodule..."
  git -C "$REPO_ROOT" submodule update --init --recursive \
    bin/orama-system/skills/openclaw-skills/cc-openclaw
else
  echo "[install-openclaw-skills] cc-openclaw submodule already present, skipping init."
fi

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
