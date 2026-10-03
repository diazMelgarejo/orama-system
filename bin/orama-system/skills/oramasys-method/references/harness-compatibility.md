# Harness Compatibility

The harness decides the provider path. Do not assume Claude-only (or any
single-provider-only) routing. Model ids, effort, and fast settings follow
[Alexandria model-governance](https://github.com/oramasys/alexandria/blob/docs/mig-pack-ingest-20260925/docs/standards/model-governance.md)
and the orama pin `docs/standards/model-governance.md`. Cursor/Grok Bot
defaults to `grok-4.6` medium with fast off. Anthropic defaults to
`claude-sonnet-5-5` medium. Agents never pick `auto`, `grok-4.5`, high
effort, or fast mode on their own.

Use the current harness's native planning, shell, file, browser, and MCP
tools. Treat local integrations as preferred tiers, not permission to invent
unavailable capabilities. State a brief fallback and use the cheapest available
equivalent before a network or paid tier.

For Mode 2 or 3 reasoning, use `mcp-oramasys` when the harness exposes it.
Legacy `mcp-ultrathink-*` names are aliases only. The HTTP fallback is
`POST /oramasys` on port 8001.
