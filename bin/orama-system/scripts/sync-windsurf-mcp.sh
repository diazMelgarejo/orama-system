#!/usr/bin/env bash
# sync-windsurf-mcp.sh — Idempotent Windsurf MCP stack for orama-system
#
# Merges bin/orama-system/config/windsurf-mcp.stack.json (code-review-graph +
# ai-cli-mcp + exa + firecrawl) into ~/.codeium/windsurf/mcp_config.json,
# preserving any unrelated servers already present (e.g. omniroute).
#
# exa/firecrawl use the hosted mcp-remote proxy (npx -y mcp-remote@0.14.3 <url>) —
# no local API key needed, same pattern already proven for Claude Code's own
# config. CRG uses the same Ollama/bge-m3 embedding wiring as Cursor.
#
# Platform: patches CRG_OPENAI_BASE_URL at sync — macOS/Linux :11434, Windows :1234
#
# Usage:
#   bash bin/orama-system/scripts/sync-windsurf-mcp.sh [--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/openclaw-env.sh
source "$SCRIPT_DIR/lib/openclaw-env.sh"

STACK_JSON="$SCRIPT_DIR/../config/windsurf-mcp.stack.json"
TARGET_MCP="${WINDSURF_MCP_JSON:-$HOME/.codeium/windsurf/mcp_config.json}"
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg (see --help)" >&2
      exit 2
      ;;
  esac
done

# Prefix every status line with this script's name for multi-script log clarity.
_log() { printf '[sync-windsurf-mcp] %s\n' "$*"; }

# Exit with an actionable error if jq is not on PATH; every merge step below needs it.
_require_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "Error: jq required (brew install jq)" >&2
    exit 1
  }
}

# Copy the stack template to $tmp and patch it with this host's CRG endpoint
# (and Python interpreter, if resolvable) before it is merged into the target.
_build_stack_json() {
  local tmp="$1"
  local pybin crg_base
  pybin="$(_crg_python_bin)" || pybin=""
  crg_base="$(_crg_openai_base_url)"
  cp "$STACK_JSON" "$tmp"
  jq --arg base "$crg_base" '
    .mcpServers["code-review-graph"].env.CRG_OPENAI_BASE_URL = $base
  ' "$tmp" > "${tmp}.base" && mv "${tmp}.base" "$tmp"
  if [ -n "$pybin" ]; then
    jq --arg py "$pybin" '
      .mcpServers["code-review-graph"].env.PYTHON = $py
    ' "$tmp" > "${tmp}.py" && mv "${tmp}.py" "$tmp"
  fi
}

# Merge stack servers into target; preserve unrelated servers already in target.
_merge_into() {
  local target="$1"
  local stack="$2"
  if [ -f "$target" ]; then
    jq -s '
      .[0] as $t | .[1] as $s |
      $t * { mcpServers: (($t.mcpServers // {}) * ($s.mcpServers // {})) }
    ' "$target" "$stack"
  else
    cat "$stack"
  fi
}

_require_jq
[ -f "$STACK_JSON" ] || { echo "Missing stack: $STACK_JSON" >&2; exit 1; }

stack_tmp="$(mktemp)"
_build_stack_json "$stack_tmp"

_log "Stack: $STACK_JSON"
_log "CRG base URL: $(_crg_openai_base_url)"
_log "Target: $TARGET_MCP"

if $DRY_RUN; then
  _log "would write → $TARGET_MCP"
  jq -r '.mcpServers | keys[]' "$stack_tmp" | sed 's/^/  server: /'
  rm -f "$stack_tmp"
  exit 0
fi

# Back up any existing file before the first sync touches it today.
if [ -f "$TARGET_MCP" ]; then
  bak="${TARGET_MCP}.bak-$(date +%Y%m%d)"
  [ -f "$bak" ] || cp "$TARGET_MCP" "$bak"
fi

# Create the parent first: the shell opens the redirect target before _merge_into runs.
mkdir -p "$(dirname "$TARGET_MCP")"
_merge_into "$TARGET_MCP" "$stack_tmp" > "${TARGET_MCP}.sync-windsurf.tmp"
jq empty "${TARGET_MCP}.sync-windsurf.tmp"
mv "${TARGET_MCP}.sync-windsurf.tmp" "$TARGET_MCP"
rm -f "$stack_tmp"
_log "✓ → $TARGET_MCP"
jq -r '.mcpServers | keys[]' "$TARGET_MCP" | sed 's/^/    /'
_log "Done. Restart Windsurf or reload MCP servers in Settings → MCP."
