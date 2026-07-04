#!/usr/bin/env bash
# exa-mcp-wrapper.sh — stdio MCP server for Exa.ai
#
# Resolves EXA_API_KEY from (priority order):
#   1. Shell environment
#   2. ~/.openclaw/openclaw.json (.env.EXA_API_KEY)
#   3. macOS Keychain (openclaw.exa.api_key)
#
# Registered in: claude_desktop_config.json, orama .mcp.json, PT .mcp.json

set -euo pipefail

# 1. Already in env
if [[ -z "${EXA_API_KEY:-}" ]]; then
  # 2. openclaw.json
  OC_JSON="${HOME}/.openclaw/openclaw.json"
  if [[ -f "$OC_JSON" ]]; then
    EXA_API_KEY=$(python3 -c "
import json,pathlib
d=json.loads(pathlib.Path('${HOME}/.openclaw/openclaw.json').read_text())
print((d.get('env') or {}).get('EXA_API_KEY',''))
" 2>/dev/null || true)
  fi
fi

if [[ -z "${EXA_API_KEY:-}" ]]; then
  # 3. macOS Keychain
  EXA_API_KEY=$(security find-generic-password -s "openclaw.exa.api_key" -w 2>/dev/null || true)
fi

if [[ -z "${EXA_API_KEY:-}" ]]; then
  echo '{"jsonrpc":"2.0","error":{"code":-32000,"message":"EXA_API_KEY not set — run: openclaw config set env.EXA_API_KEY <key>"},"id":null}' >&2
  exit 1
fi

export EXA_API_KEY

# Use the nvm node that's already on PATH for Claude Desktop
NODE_BIN="${HOME}/.nvm/versions/node/v22.22.2/bin"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="${NODE_BIN}:${PATH}"
fi

exec npx -y exa-mcp-server
