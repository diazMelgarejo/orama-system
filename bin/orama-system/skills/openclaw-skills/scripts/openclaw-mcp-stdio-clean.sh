#!/usr/bin/env bash
# openclaw-mcp-stdio-clean.sh — wrap `openclaw mcp serve` with a pure-JSON stdout.
#
# WHY: the openclaw CLI prints Doctor/Config warning box-art (│ ◇ ├ └ …) to
# STDOUT before and during `mcp serve`. MCP stdio clients (Claude Desktop,
# Claude CLI) parse stdout as newline-delimited JSON-RPC, so any banner line
# produces "Unexpected token '│'" and the server is marked failed.
# `openclaw doctor --fix` cannot clear every warning class (e.g. the persistent
# "Left plugin install index in place …" migration notice), so filtering is the
# durable fix: JSON-RPC lines always start with '{'; banner lines never do.
#
# Register (CLI):     claude mcp add openclaw -- bash <this script>
# Register (Desktop): "command": "bash", "args": ["<this script>"]
set -uo pipefail

OPENCLAW_BIN="${OPENCLAW_BIN:-$HOME/.local/bin/openclaw}"

if [ ! -x "$OPENCLAW_BIN" ]; then
  echo '{"jsonrpc":"2.0","method":"notifications/message","params":{"level":"error","data":"openclaw binary not found; set OPENCLAW_BIN"}}'
  exit 127
fi

# stdin passes straight to openclaw; stdout is filtered to JSON-RPC lines only;
# stderr passes through untouched (Claude shows it in MCP logs).
"$OPENCLAW_BIN" mcp serve "$@" | grep --line-buffered '^{'
