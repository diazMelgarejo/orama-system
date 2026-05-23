#!/usr/bin/env bash
# openclaw-env.sh — resolve orama install root, OpenClaw parent tree, and bootstrap .mcp.json
#
# Package install layout (predominant): orama-system lives at
#   $OPENCLAW_ROOT/orama-system/   (or any path under ORAMA_INSTALL_DIR)
# with OpenClaw sibling repos (AlphaClaw, Perpetua-Tools, …) under $OPENCLAW_ROOT.
# Standalone clone: parent of the git root is still used when it looks like OpenClaw.
#
# Env overrides (portable — never commit /Users/<name>/…):
#   ORAMA_REPO_ROOT / ORAMA_INSTALL_DIR — orama-system git root (install dir)
#   OPENCLAW_ROOT / ORAMA_OPENCLAW_ROOT — OpenClaw multi-repo parent
#   OPENCLAW_MCP_JSON — path to .mcp.json (default: $OPENCLAW_ROOT/.mcp.json)
#   PERPETUA_TOOLS_ROOT — Perpetua-Tools checkout (optional)
#
# Sourced by first-run-install.sh, setup-embeddings, crg-embed-mode, and repo scripts.
set -euo pipefail

orama_git_root() {
  if [ -n "${ORAMA_REPO_ROOT:-}" ] && [ -d "${ORAMA_REPO_ROOT}/.git" ]; then
    printf '%s\n' "$ORAMA_REPO_ROOT"
    return 0
  fi
  if [ -n "${ORAMA_INSTALL_DIR:-}" ] && [ -d "${ORAMA_INSTALL_DIR}/.git" ]; then
    printf '%s\n' "$ORAMA_INSTALL_DIR"
    return 0
  fi
  local d="$PWD"
  while [ "$d" != "/" ]; do
    if [ -d "$d/.git" ] && [ -d "$d/bin/orama-system" ]; then
      printf '%s\n' "$d"
      return 0
    fi
    d="$(dirname "$d")"
  done
  return 1
}

# Alias for package installers — same as orama_git_root().
orama_install_dir() {
  orama_git_root "$@"
}

detect_openclaw_root() {
  local candidate=""
  if [ -n "${OPENCLAW_ROOT:-}" ] && [ -d "$OPENCLAW_ROOT" ]; then
    candidate="$OPENCLAW_ROOT"
  elif [ -n "${ORAMA_OPENCLAW_ROOT:-}" ] && [ -d "$ORAMA_OPENCLAW_ROOT" ]; then
    candidate="$ORAMA_OPENCLAW_ROOT"
  else
    local orama_root parent
    orama_root="$(orama_git_root)" || return 1
    parent="$(dirname "$orama_root")"
    # Default: parent of orama-system repo (package install: …/OpenClaw/orama-system → …/OpenClaw)
    if [ -d "$parent" ]; then
      candidate="$parent"
    else
      return 1
    fi
  fi
  printf '%s\n' "$candidate"
}

# Public alias used in docs/skills.
orama_openclaw_root() {
  detect_openclaw_root "$@"
}

detect_perpetua_tools_root() {
  if [ -n "${PERPETUA_TOOLS_ROOT:-}" ] && [ -d "$PERPETUA_TOOLS_ROOT" ]; then
    printf '%s\n' "$PERPETUA_TOOLS_ROOT"
    return 0
  fi
  local openclaw_root
  openclaw_root="$(detect_openclaw_root)" || return 1
  local candidate="$openclaw_root/perplexity-api/Perpetua-Tools"
  if [ -d "$candidate" ]; then
    printf '%s\n' "$candidate"
    return 0
  fi
  return 1
}

resolve_openclaw_mcp_json() {
  if [ -n "${OPENCLAW_MCP_JSON:-}" ]; then
    printf '%s\n' "$OPENCLAW_MCP_JSON"
    return 0
  fi
  local root
  root="$(detect_openclaw_root)" || return 1
  printf '%s\n' "$root/.mcp.json"
}

_emit_log() {
  local log_fn="$1"
  shift
  case "$log_fn" in
    :|"") ;;
    echo) printf '%s\n' "$@" ;;
    *)
      if declare -F "$log_fn" >/dev/null 2>&1; then
        "$log_fn" "$@"
      else
        printf '%s\n' "$@" >&2
      fi
      ;;
  esac
}

_crg_python_bin() {
  if command -v python3.13 >/dev/null 2>&1; then
    command -v python3.13
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    return 1
  fi
}

_write_minimal_mcp_json() {
  local mcp_json="$1"
  local pybin
  pybin="$(_crg_python_bin)" || return 1
  command -v jq >/dev/null 2>&1 || return 1
  mkdir -p "$(dirname "$mcp_json")"
  if [ -f "$mcp_json" ]; then
    jq --arg py "$pybin" '
      .mcpServers["code-review-graph"] = {
        "command": "uvx",
        "args": ["code-review-graph", "serve"],
        "env": (
          (.mcpServers["code-review-graph"].env // {})
          + {
            "PYTHON": $py,
            "CRG_OPENAI_API_KEY": "ollama",
            "CRG_OPENAI_BASE_URL": "http://localhost:11434/v1",
            "CRG_OPENAI_MODEL": "bge-m3",
            "CRG_OPENAI_DIMENSION": "1024",
            "CRG_ACCEPT_CLOUD_EGRESS": "1"
          }
        )
      }
    ' "$mcp_json" > "${mcp_json}.openclaw.tmp" && mv "${mcp_json}.openclaw.tmp" "$mcp_json"
  else
    jq -n --arg py "$pybin" '{
      "mcpServers": {
        "code-review-graph": {
          "command": "uvx",
          "args": ["code-review-graph", "serve"],
          "env": {
            "PYTHON": $py,
            "CRG_OPENAI_API_KEY": "ollama",
            "CRG_OPENAI_BASE_URL": "http://localhost:11434/v1",
            "CRG_OPENAI_MODEL": "bge-m3",
            "CRG_OPENAI_DIMENSION": "1024",
            "CRG_ACCEPT_CLOUD_EGRESS": "1"
          }
        }
      }
    }' > "$mcp_json"
  fi
}

ensure_openclaw_mcp_json() {
  local log_fn="${1:-:}"
  local root mcp_json

  mcp_json="$(resolve_openclaw_mcp_json)" || {
    _emit_log "$log_fn" "openclaw-env: could not resolve OpenClaw root (set OPENCLAW_ROOT)"
    return 1
  }
  root="$(dirname "$mcp_json")"

  if [ -f "$mcp_json" ] && command -v jq >/dev/null 2>&1; then
    if jq -e '.mcpServers["code-review-graph"]' "$mcp_json" >/dev/null 2>&1; then
      _emit_log "$log_fn" "openclaw-env: $mcp_json already has code-review-graph"
      return 0
    fi
  fi

  if command -v uvx >/dev/null 2>&1; then
    _emit_log "$log_fn" "openclaw-env: code-review-graph install --platform claude-code --repo <openclaw>"
    if uvx code-review-graph install --platform claude-code --repo "$root" >/dev/null 2>&1; then
      if [ -f "$mcp_json" ] && jq -e '.mcpServers["code-review-graph"]' "$mcp_json" >/dev/null 2>&1; then
        _emit_log "$log_fn" "openclaw-env: install registered code-review-graph in $mcp_json"
        return 0
      fi
    fi
    _emit_log "$log_fn" "openclaw-env: install incomplete; writing minimal template"
  fi

  if _write_minimal_mcp_json "$mcp_json"; then
    _emit_log "$log_fn" "openclaw-env: wrote code-review-graph entry to $mcp_json"
    return 0
  fi

  _emit_log "$log_fn" "openclaw-env: failed to create $mcp_json (need jq and python3.13+)"
  return 1
}
