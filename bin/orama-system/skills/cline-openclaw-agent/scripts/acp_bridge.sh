#!/usr/bin/env bash
# ACP bridge launcher: OpenClaw (client) drives Cline (server) via ACP.
# Usage: acp_bridge.sh --cwd /path/to/repo [--session agent:cline-agent:main] [--provenance meta+receipt]

set -euo pipefail

CWD=""
SESSION=""
PROVENANCE=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cwd) CWD="${2:-}"; shift 2 ;;
    --session) SESSION="${2:-}"; shift 2 ;;
    --provenance) PROVENANCE="${2:-}"; shift 2 ;;
    --verbose|-v) VERBOSE=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$CWD" ]] && { echo "Usage: acp_bridge.sh --cwd <dir> [--session <key>] [--provenance <mode>]" >&2; exit 2; }
command -v cline >/dev/null 2>&1 || { echo "cline CLI not found on PATH" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../../../../../" && pwd)"
RESOLVER="$ORAMA_ROOT/scripts/openclaw/resolve-openclaw.sh"

cmd=("$RESOLVER" acp client --server cline --server-args --acp --cwd "$CWD")
[[ -n "$SESSION" ]] && cmd+=(--session "$SESSION")
[[ -n "$PROVENANCE" ]] && cmd+=(--provenance "$PROVENANCE")
[[ "$VERBOSE" == true ]] && cmd+=(-v)

exec "${cmd[@]}"
