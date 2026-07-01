# MCP Bridge (OpenClaw ↔ Cline)

MCP (Model Context Protocol) is the tool-level bridge. Unlike ACP (full agent
delegation), MCP lets one agent call another's **tools** without surrendering
the conversation loop.

## Direction matters

Cline is an MCP **client**, not an MCP server. `cline mcp --help` shows only
`install|add` (to register MCP servers *inside* Cline). There is no
`cline mcp serve`. Therefore:

- ❌ Do **not** add a `cline` entry to `mcp.servers` in OpenClaw config —
  Cline cannot be an MCP server.
- ✅ The working direction is: **OpenClaw serves → Cline consumes**.

## Wiring: expose OpenClaw tools to Cline

```bash
# 1. OpenClaw exposes its channels/tools over MCP stdio
openclaw mcp serve

# 2. Register OpenClaw as an MCP server inside Cline
cline mcp install openclaw -- npx -y openclaw mcp serve
```

After step 2, Cline sessions can call OpenClaw's tools (channel sends, memory,
cron, exec, etc.) directly from within a Cline task.

## OpenClaw MCP management commands

| Command | Description |
| --- | --- |
| `openclaw mcp serve` | Expose OpenClaw channels over MCP stdio |
| `openclaw mcp add <name> --command <cmd> --args <a> <b>` | Add an MCP server from flags + probe before saving |
| `openclaw mcp set <name> --json '{...}'` | Set one MCP server from a JSON object |
| `openclaw mcp list` | List OpenClaw-managed MCP servers |
| `openclaw mcp show [name]` | Show one server or the full `mcp.servers` config |
| `openclaw mcp probe` | Connect to configured servers and list capabilities |
| `openclaw mcp status` | Show transport status without connecting |
| `openclaw mcp doctor` | Check configured servers for static setup problems |
| `openclaw mcp configure <name>` | Update operator controls without replacing the server |
| `openclaw mcp tools <name>` | Update per-server tool include/exclude filters |
| `openclaw mcp login <name>` | Authorize an OAuth MCP server |
| `openclaw mcp logout <name>` | Clear stored OAuth credentials |
| `openclaw mcp reload` | Dispose cached MCP runtimes so new config is used next turn |
| `openclaw mcp unset <name>` | Remove one MCP server |

## MCP server config shape (in `openclaw.json`)

```json
{
  "mcp": {
    "servers": {
      "<name>": {
        "enabled": true,
        "command": "npx",
        "args": ["-y", "pkg@latest"],
        "env": {"KEY": "value"},
        "transport": "stdio",
        "cwd": "/optional/working/dir"
      }
    }
  }
}
```

`transport` can be `stdio`, `sse`, or `streamable-http`. For `sse`/`http`, use
`url` instead of `command`/`args`.

## Use cases

- **Cline calls OpenClaw channels**: Cline, mid-task, sends a Telegram message
  or reads OpenClaw memory via MCP tools — without leaving the Cline session.
- **Tool filtering**: use `openclaw mcp tools openclaw --include <tool>` to
  expose only a subset of OpenClaw tools to Cline.
- **OAuth MCP servers**: if Cline needs an OAuth-backed MCP server, use
  `openclaw mcp login <name>` to authorize it once.
