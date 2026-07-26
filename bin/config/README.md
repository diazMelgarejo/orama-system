# bin/config — redirect layer (no duplicate JSON)

Canonical runtime config lives in **`bin/orama-system/config/`**.

| Legacy path | Canonical |
|-------------|-----------|
| `bin/config/agent_registry.json` | `bin/orama-system/config/agent_registry.json` |
| `bin/config/routing_rules.json` | `bin/orama-system/config/routing_rules.json` |
| `bin/config/mcp.json` | `bin/orama-system/config/mcp.json` |

Files in this directory are **symlinks** to the canonical tree. Loaders and new code should read **`bin/orama-system/config/`** directly.

Cursor MCP stacks (`cursor-mcp.stack.json`, `cursor-mcp.stack.readonly.json`) live only under `bin/orama-system/config/`.
