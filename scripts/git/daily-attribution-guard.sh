#!/usr/bin/env bash
set -euo pipefail
PT="${PERPETUA_TOOLS_PATH:-/agent/repos/Perpetua-Tools}"
exec bash "$PT/scripts/git/daily-attribution-guard.sh"
