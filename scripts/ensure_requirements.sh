#!/usr/bin/env bash
# scripts/ensure_requirements.sh — startup hard-requirements composition root.
# Keeps the historical platform/model probe byte-identical in
# ensure_platform_requirements.sh and adds the canonical ai-cli-mcp readiness gate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM_ENSURE="$SCRIPT_DIR/scripts/ensure_platform_requirements.sh"
MCP_ENSURE="$SCRIPT_DIR/bin/orama-system/scripts/install-mcp-stack.sh"

bash "$PLATFORM_ENSURE" "$@"

if [ "${ORAMA_SKIP_MCP_BOOTSTRAP:-0}" = "1" ]; then
  printf '[ensure] WARN  MCP readiness bypassed by ORAMA_SKIP_MCP_BOOTSTRAP=1\n' >&2
  exit 0
fi

mcp_args=(--core-only --non-interactive)
for arg in "$@"; do
  case "$arg" in
    --check) mcp_args+=(--verify) ;;
    --force) mcp_args+=(--force) ;;
  esac
done

if [ ! -x "$MCP_ENSURE" ] && [ ! -f "$MCP_ENSURE" ]; then
  printf '[ensure] ERROR canonical MCP installer missing: %s\n' "$MCP_ENSURE" >&2
  exit 1
fi

bash "$MCP_ENSURE" "${mcp_args[@]}"
