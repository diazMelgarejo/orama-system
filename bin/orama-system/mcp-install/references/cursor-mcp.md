# Cursor MCP stack (orama-system)

## Source of truth

| File | Role |
|------|------|
| `bin/orama-system/config/cursor-mcp.stack.json` | Canonical server definitions (CRG + ai-cli-mcp) |
| `orama-system/.cursor/mcp.json` | Project config — auto-loaded when the workspace root is this repo |
| `~/.cursor/mcp.json` | User-global config (legacy home for `ai-cli-mcp` only) |
| `OpenClaw/.mcp.json` | Claude Code / OpenClaw hub (CRG only; not Cursor) |

## Sync (idempotent)

```bash
# Project stack (CRG + ai-cli-mcp) — run after pull or embed-mode changes
bash bin/orama-system/scripts/sync-cursor-mcp.sh

# Also add code-review-graph to ~/.cursor/mcp.json (OpenClaw parent workspace)
bash bin/orama-system/scripts/sync-cursor-mcp.sh --also-user

# Optional Gemini analyzer lane
bash bin/orama-system/scripts/sync-cursor-mcp.sh --include-gemini
```

Wired from:

- `install-mcp-stack.sh` (Step 5b)
- `ensure_orama_cursor_crg_mcp` in `scripts/lib/openclaw-env.sh`
- `crg-embed-mode` (via `sync_orama_cursor_crg_from` for CRG env only)

## Cursor merge behavior

Cursor loads **user** and **project** MCP configs together. To avoid duplicate `ai-cli-mcp` processes:

1. Open **orama-system** as the workspace root → project file supplies the full stack.
2. Keep `ai-cli-mcp` in `~/.cursor/mcp.json` for other repos; do not duplicate it in the user file when the project already defines it (project wins for same name — reload MCP if tools look doubled).
3. Use `--also-user` only to add **code-review-graph** globally when the workspace is the OpenClaw parent folder.

## After changes

Reload MCP in **Cursor Settings → MCP**, or restart Cursor. Confirm tools: `code-review-graph` MCP (`*_tool` suffix in Cursor) and `ai-cli-mcp`.

## CLI fallback

If MCP tools are absent in a session, use:

```bash
uvx code-review-graph status --repo "$ORAMA_REPO_ROOT"
uvx code-review-graph detect-changes --repo "$ORAMA_REPO_ROOT" --base <sha>
```

See `bin/orama-system/skills/code-review/references/mcp-tools-crg.md`.
