#!/usr/bin/env bash
# Cursor Cloud Agent — unconditional attribution guards (canonical: ~/.cursor/openclaw).
set -euo pipefail

HOME="${HOME:-/home/ubuntu}"
export HOME
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALLER="${CURSOR_CLOUD_ATTRIBUTION_INSTALLER:-$HOME/.cursor/openclaw/install-cursor-cloud-attribution.sh}"
PT="${PERPETUA_TOOLS_PATH:-$HOME/openclaw-v1/Perpetua-Tools}"
[[ -d /agent/repos/Perpetua-Tools ]] && PT="/agent/repos/Perpetua-Tools"

seed_from_pt() {
  local dest="${HOME}/.cursor/openclaw/cursor-cloud-attribution/rules"
  mkdir -p "$dest"
  for rule in no-commit-attribution.mdc never-undo-attribution-expunge.mdc \
    banned-attribution-local.mdc zero-banned-attribution-everywhere.mdc; do
    [[ -f "$PT/.cursor/rules/$rule" ]] || continue
    install -m 0644 "$PT/.cursor/rules/$rule" "$dest/$rule"
  done
  [[ -x "$PT/scripts/cursor/install-user-git-environment.sh" ]] && \
    PERPETUA_TOOLS_PATH="$PT" ORAMA_SYSTEM_PATH="$REPO_ROOT" \
      bash "$PT/scripts/cursor/install-user-git-environment.sh" || true
}

if [[ -x "$INSTALLER" ]]; then
  exec bash "$INSTALLER"
fi

# First boot on a fresh VM: seed openclaw from Perpetua-Tools checkout, then install.
seed_from_pt
if [[ -x "$INSTALLER" ]]; then
  exec bash "$INSTALLER"
fi

if [[ -x "$PT/scripts/git/daily-attribution-guard.sh" ]]; then
  PERPETUA_TOOLS_PATH="$PT" WORKSPACE_ROOT="${WORKSPACE_ROOT:-/agent/repos}" \
    bash "$PT/scripts/git/daily-attribution-guard.sh" || true
fi

echo "WARN: cursor cloud attribution installer not found at $INSTALLER" >&2
exit 0
