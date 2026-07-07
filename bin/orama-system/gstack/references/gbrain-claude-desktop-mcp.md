## GBrain on Claude Desktop (MCP) — ported from the CLI

Claude Desktop uses a **separate** MCP config from the CLI:
`~/Library/Application Support/Claude/claude_desktop_config.json` (NOT `~/.claude.json`).
Port the same servers there (`gbrain` + `code-review-graph`) to give Desktop the CLI's tool
surface. Note: filesystem skills (`~/.agents/skills/`, `~/.claude/skills/`) are CLI-only — they
do not load in Desktop; the portable knowledge is the **MCP servers**, so register both.

**Gotcha (fixed 2026-06-14):** Desktop launches MCP servers with a **minimal PATH**
(`/usr/bin:/bin`) and does NOT inherit your shell. The `~/.bun/bin/gbrain` binary needs `bun`
on PATH, so a plain `gbrain serve` wrapper fails with `env: bun: No such file or directory`
and the server shows disconnected. The CLI works only because it inherits the terminal PATH.

**Canonical Desktop wrapper** (`.mcpServers.gbrain`) — source `.env` for the DB URL AND
prepend `~/.bun/bin`:

```json
{
  "command": "/bin/sh",
  "args": ["-c", ". \"$HOME/.gbrain/.env\"; export PATH=\"$HOME/.bun/bin:/opt/homebrew/bin:/usr/local/bin:$PATH\"; exec \"$HOME/.bun/bin/gbrain\" serve"]
}
```

Restart Claude Desktop after editing (MCP servers load at app start). Verify in a Desktop-like
minimal env before restarting:

```bash
env -i HOME="$HOME" PATH=/usr/bin:/bin /bin/sh -c '. "$HOME/.gbrain/.env"; export PATH="$HOME/.bun/bin:$PATH"; gbrain doctor --json' | head
```

`code-review-graph` is already PATH-safe (absolute `/opt/homebrew/bin/uvx` command) — no wrapper
needed. Back up the config (`cp … config.json config.json.bak-<ts>`) before editing.