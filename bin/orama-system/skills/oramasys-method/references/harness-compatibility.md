# Harness Compatibility

Model tier choice follows the existing routing policy (`.cursor/commands/model-route.md`
and the workflow tiering). When that policy cannot decide, or the chosen tier cannot
run on this harness, fall back to the harness default or an allowed alternative per
the Alexandria standard (PR #1, tip `e7ee9db6`, Proposed) and the orama pin
`docs/standards/model-governance.md`: Cursor/Grok Bot `grok-4.7` medium with fast
off; Anthropic `claude-sonnet-5-5` medium. A fallback never raises effort, turns on
fast mode, or escalates. `grok-4.5` and `grok-4.6` are outdated ids.

Use the current harness's native planning, shell, file, browser, and MCP
tools. Treat local integrations as preferred tiers, not permission to invent
unavailable capabilities. State a brief fallback and use the cheapest available
equivalent before a network or paid tier.

For Mode 2 or 3 reasoning, use `mcp-oramasys` when the harness exposes it.
Legacy `mcp-ultrathink-*` names are aliases only. The HTTP fallback is
`POST /oramasys` on port 8001.
