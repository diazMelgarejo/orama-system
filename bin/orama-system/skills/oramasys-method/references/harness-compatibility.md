# Harness Compatibility

Use the current harness's native planning, shell, file, browser, and MCP
tools. Treat local integrations as preferred tiers, not permission to invent
unavailable capabilities. State a brief fallback and use the cheapest available
equivalent before a network or paid tier.

For Mode 2 or 3 reasoning, use `mcp-oramasys` when the harness exposes it.
Legacy `mcp-ultrathink-*` names are aliases only. The HTTP fallback is
`POST /oramasys` on port 8001.
