#!/usr/bin/env bash
# print-lan-peer-token.sh — show ORAMA_CONTROL_PLANE_TOKEN for LAN peer .env.local handoff
#
# Mac → Win: run on Mac; paste output into Win orama-system .env.local
# Win → Mac: use scripts/env/print-lan-peer-token.ps1 on Windows instead
#
# Never commit the token. chmod 600 on .env.local after paste.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

_pt_root() {
  for var in PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT PERPETUA_TOOLS_PATH PT_HOME; do
    local v="${!var:-}"
    if [ -n "$v" ] && [ -f "${v}/orchestrator/fastapi_app.py" ]; then
      echo "$v"
      return 0
    fi
  done
  if [ -f "$REPO_ROOT/.paths" ]; then
    # shellcheck disable=SC1090
    local PT_DIR
    PT_DIR="$(grep '^PT_DIR=' "$REPO_ROOT/.paths" | cut -d= -f2- | tr -d '"')"
    if [ -n "$PT_DIR" ] && [ -f "${PT_DIR}/orchestrator/fastapi_app.py" ]; then
      echo "$PT_DIR"
      return 0
    fi
  fi
  return 1
}

PT_DIR="$(_pt_root)" || {
  echo "Set PERPETUA_TOOLS_ROOT to your Perpetua-Tools clone." >&2
  exit 1
}

TOKEN_PATH="${PT_DIR}/.state/control_plane_token"
if [ ! -f "$TOKEN_PATH" ]; then
  echo "No token yet. Run from orama-system:"
  echo "  ./start.sh --lan-peer --no-open"
  exit 1
fi

TOKEN="$(tr -d '[:space:]' < "$TOKEN_PATH")"
echo ""
echo "=== Win .env.local (orama-system) — add or replace this line ==="
echo "ORAMA_CONTROL_PLANE_TOKEN=${TOKEN}"
echo ""
echo "Then on Win:"
echo '  .\platform\windows\start.ps1 --stop'
echo '  .\platform\windows\start.ps1 --lan-peer --no-open'
echo '  python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json'
echo ""
