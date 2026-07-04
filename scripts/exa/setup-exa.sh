#!/usr/bin/env bash
# setup-exa.sh — one-shot Exa.ai integration bootstrap
#
# Steps:
#   1. Installs exa-py Python package
#   2. Accepts EXA_API_KEY (interactively or via --key flag)
#   3. Stores key in ~/.openclaw/openclaw.json + macOS Keychain
#   4. Adds Exa MCP server to Claude Desktop config
#   5. Writes .mcp.json for orama-system and Perpetua-Tools
#
# Usage:
#   bash setup-exa.sh
#   bash setup-exa.sh --key exa_abc123...

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PT_ROOT="${HOME}/code/OpenClaw/perplexity-api/Perpetua-Tools"
DESKTOP_CFG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
MCP_WRAPPER="${SCRIPT_DIR}/exa-mcp-wrapper.sh"

# Parse --key flag
API_KEY="${EXA_API_KEY:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --key) API_KEY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "[exa-setup] Starting Exa.ai integration bootstrap"

# 1. Install exa-py
echo "[exa-setup] Installing exa-py..."
pip3 install -q exa-py && echo "[exa-setup] exa-py installed"

# 2. Get API key
if [[ -z "$API_KEY" ]]; then
  echo "[exa-setup] Enter your Exa API key (from https://dashboard.exa.ai/keys):"
  read -r -s API_KEY
  echo
fi

if [[ -z "$API_KEY" ]]; then
  echo "[exa-setup] ERROR: No API key provided" >&2
  exit 1
fi

# 3a. Store in macOS Keychain
echo "[exa-setup] Storing key in macOS Keychain (openclaw.exa.api_key)..."
security add-generic-password -s "openclaw.exa.api_key" -a "$(whoami)" -w "$API_KEY" -U 2>/dev/null && \
  echo "[exa-setup] Keychain: OK"

# 3b. Store in ~/.openclaw/openclaw.json
OC_JSON="${HOME}/.openclaw/openclaw.json"
if [[ -f "$OC_JSON" ]]; then
  echo "[exa-setup] Injecting EXA_API_KEY into ~/.openclaw/openclaw.json..."
  python3 - <<PYEOF
import json, pathlib, sys

path = pathlib.Path("$OC_JSON")
data = json.loads(path.read_text())
data.setdefault("env", {})["EXA_API_KEY"] = "$API_KEY"
path.write_text(json.dumps(data, indent=2))
print("[exa-setup] openclaw.json: OK")
PYEOF
fi

# 4. Add to Claude Desktop MCP config
chmod +x "$MCP_WRAPPER"
echo "[exa-setup] Registering Exa MCP server in Claude Desktop config..."
python3 - <<PYEOF
import json, pathlib, sys

cfg_path = pathlib.Path("$DESKTOP_CFG")
cfg = json.loads(cfg_path.read_text())
servers = cfg.setdefault("mcpServers", {})

servers["exa"] = {
    "command": "bash",
    "args": ["$MCP_WRAPPER"],
    "env": {}
}

cfg_path.write_text(json.dumps(cfg, indent=2))
print("[exa-setup] Claude Desktop config: OK (restart Claude Desktop to activate)")
PYEOF

# 5a. Write orama-system .mcp.json
ORAMA_MCP="${ORAMA_ROOT}/.mcp.json"
echo "[exa-setup] Writing ${ORAMA_MCP}..."
python3 - <<PYEOF
import json, pathlib

path = pathlib.Path("$ORAMA_MCP")
data = json.loads(path.read_text()) if path.exists() else {}
data.setdefault("mcpServers", {})["exa"] = {
    "command": "bash",
    "args": ["$MCP_WRAPPER"],
    "env": {}
}
path.write_text(json.dumps(data, indent=2))
print("[exa-setup] orama-system .mcp.json: OK")
PYEOF

# 5b. Write Perpetua-Tools .mcp.json
PT_MCP="${PT_ROOT}/.mcp.json"
if [[ -d "$PT_ROOT" ]]; then
  echo "[exa-setup] Writing ${PT_MCP}..."
  python3 - <<PYEOF
import json, pathlib

path = pathlib.Path("$PT_MCP")
data = json.loads(path.read_text()) if path.exists() else {}
data.setdefault("mcpServers", {})["exa"] = {
    "command": "bash",
    "args": ["$MCP_WRAPPER"],
    "env": {}
}
path.write_text(json.dumps(data, indent=2))
print("[exa-setup] Perpetua-Tools .mcp.json: OK")
PYEOF
fi

echo ""
echo "[exa-setup] Done. Exa.ai is wired into:"
echo "  - Claude Desktop MCP  (restart app)"
echo "  - orama-system .mcp.json"
echo "  - Perpetua-Tools .mcp.json"
echo "  - Python: from exa_search import search, find_similar"
echo ""
echo "[exa-setup] Quick test:"
echo "  python3 $SCRIPT_DIR/exa_search.py 'orama system AI coding agent'"
