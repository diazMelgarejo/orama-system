#!/usr/bin/env bash
# Apply Cursor commit-attribution guards to orama-system + sibling OpenClaw repos.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISABLE="$SCRIPT_DIR/disable-cursor-commit-attribution.sh"
SYNC="$SCRIPT_DIR/sync-attribution-guard-scripts.sh"

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"

# Cursor may pass literal ${workspaceFolder} before expansion — fall back to this repo.
orama_system_path="${ORAMA_SYSTEM_PATH:-$ORAMA_ROOT}"
if [[ "$orama_system_path" == *'${'* ]] || [[ ! -d "$orama_system_path/.git" ]]; then
  orama_system_path="$ORAMA_ROOT"
fi

resolve_git_repo() {
  local r="$1"
  [[ -n "$r" ]] || return 1
  [[ "$r" == *'${'* ]] && return 1
  [[ -d "$r" ]] || return 1
  local abs
  abs="$(cd "$r" && pwd)" || return 1
  [[ -d "$abs/.git" ]] || return 1
  printf '%s' "$abs"
}

raw_candidates=(
  "$ORAMA_ROOT"
  "$orama_system_path"
  "${PERPETUA_TOOLS_PATH:-$OPENCLAW_HOME/Perpetua-Tools}"
  "${PERPETUA_TOOLS_ROOT:-$OPENCLAW_HOME/Perpetua-Tools}"
  "${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
)

declare -A seen=()
unique=()
for r in "${raw_candidates[@]}"; do
  resolved="$(resolve_git_repo "$r" 2>/dev/null || true)"
  [[ -n "$resolved" ]] || continue
  if [[ -n "${seen[$resolved]+x}" ]]; then
    continue
  fi
  seen[$resolved]=1
  unique+=("$resolved")
done

if [[ -x "$SYNC" ]]; then
  for r in "${unique[@]}"; do
    [[ "$r" == "$ORAMA_ROOT" ]] && continue
    bash "$SYNC" "$r"
  done
fi

for r in "${unique[@]}"; do
  bash "$DISABLE" "$r"
done

echo "OK: attribution guards applied for ${#unique[@]} repo path(s)"
