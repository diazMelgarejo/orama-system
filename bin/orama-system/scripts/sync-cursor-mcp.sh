#!/usr/bin/env bash
# sync-cursor-mcp.sh — Idempotent Cursor MCP stack for orama-system
#
# Merges bin/orama-system/config/cursor-mcp.stack.json into:
#   - orama-system/.cursor/mcp.json (project — auto-loaded when workspace is repo root)
#   - ~/.cursor/mcp.json (optional --also-user — adds code-review-graph only)
#
# Cursor merges user + project MCP. The project file carries the full stack
# (CRG + ai-cli-mcp). --also-user merges only code-review-graph into the global
# config so OpenClaw-parent workspaces get CRG without duplicating ai-cli-mcp.
#
# Usage:
#   bash bin/orama-system/scripts/sync-cursor-mcp.sh [--also-user] [--include-gemini] [--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/openclaw-env.sh
source "$SCRIPT_DIR/lib/openclaw-env.sh"

STACK_JSON="$SCRIPT_DIR/../config/cursor-mcp.stack.json"
ALSO_USER=false
INCLUDE_GEMINI=false
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --also-user) ALSO_USER=true ;;
    --include-gemini) INCLUDE_GEMINI=true ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg (see --help)" >&2
      exit 2
      ;;
  esac
done

_log() { printf '[sync-cursor-mcp] %s\n' "$*"; }
_run() { $DRY_RUN && _log "[dry-run] $*" || eval "$@"; }

_require_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "Error: jq required (brew install jq)" >&2
    exit 1
  }
}

_build_stack_json() {
  local tmp="$1"
  local pybin
  pybin="$(_crg_python_bin)" || pybin=""
  cp "$STACK_JSON" "$tmp"
  if [ -n "$pybin" ]; then
    jq --arg py "$pybin" '
      .mcpServers["code-review-graph"].env.PYTHON = $py
    ' "$tmp" > "${tmp}.py" && mv "${tmp}.py" "$tmp"
  fi
  if $INCLUDE_GEMINI; then
    jq '.mcpServers["gemini-cli"] = {
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool@latest"]
    }' "$tmp" > "${tmp}.gemini" && mv "${tmp}.gemini" "$tmp"
  fi
}

# Merge stack servers into target; preserve unrelated servers already in target.
_merge_into() {
  local target="$1"
  local stack="$2"
  mkdir -p "$(dirname "$target")"
  if [ -f "$target" ]; then
    jq -s '
      .[0] as $t | .[1] as $s |
      $t * { mcpServers: (($t.mcpServers // {}) * ($s.mcpServers // {})) }
    ' "$target" "$stack"
  else
    cat "$stack"
  fi
}

_sync_file() {
  local target="$1"
  local label="$2"
  local stack_tmp
  stack_tmp="$(mktemp)"
  _build_stack_json "$stack_tmp"
  if $DRY_RUN; then
    _log "would write $label → $target"
    jq -r '.mcpServers | keys[]' "$stack_tmp" | sed 's/^/  server: /'
    rm -f "$stack_tmp"
    return 0
  fi
  _merge_into "$target" "$stack_tmp" > "${target}.sync-cursor.tmp"
  jq empty "${target}.sync-cursor.tmp"
  mv "${target}.sync-cursor.tmp" "$target"
  rm -f "$stack_tmp"
  _log "✓ $label → $target"
  jq -r '.mcpServers | keys[]' "$target" | sed 's/^/    /'
}

_require_jq
[ -f "$STACK_JSON" ] || { echo "Missing stack: $STACK_JSON" >&2; exit 1; }

ORAMA_ROOT="$(orama_git_root)" || { echo "Not in orama-system repo (set ORAMA_REPO_ROOT)" >&2; exit 1; }
PROJECT_MCP="$ORAMA_ROOT/.cursor/mcp.json"

_log "Stack: $STACK_JSON"
_log "Project MCP: $PROJECT_MCP"
_sync_file "$PROJECT_MCP" "project"

if $ALSO_USER; then
  USER_MCP="${HOME}/.cursor/mcp.json"
  _log "User MCP (CRG only): $USER_MCP"
  crg_only="$(mktemp)"
  stack_tmp="$(mktemp)"
  _build_stack_json "$stack_tmp"
  jq '{ mcpServers: { "code-review-graph": .mcpServers["code-review-graph"] } }' "$stack_tmp" > "$crg_only"
  if $DRY_RUN; then
    _log "would merge code-review-graph into user → $USER_MCP"
  else
    _merge_into "$USER_MCP" "$crg_only" > "${USER_MCP}.sync-cursor.tmp"
    jq empty "${USER_MCP}.sync-cursor.tmp"
    mv "${USER_MCP}.sync-cursor.tmp" "$USER_MCP"
    _log "✓ user (CRG only) → $USER_MCP"
  fi
  rm -f "$stack_tmp" "$crg_only"
else
  _log "Tip: pass --also-user to add code-review-graph to ~/.cursor/mcp.json (OpenClaw parent workspace)."
fi

_log "Done. Restart Cursor or reload MCP servers in Settings → MCP."
