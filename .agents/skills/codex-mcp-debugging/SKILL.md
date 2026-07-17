---
name: codex-mcp-debugging
description: Use when debugging Codex CLI MCP config errors, stdio vs HTTP transport, bearer_token_env_var confusion, Exa wrapper setup, or codex mcp list failures. Loads the canonical in-repo skill.
---

# codex-mcp-debugging thin wrapper

Canonical skill: `bin/orama-system/skills/codex-mcp-debugging/SKILL.md`

## Before use

```bash
git fetch origin --prune
git status --short --branch
```

If the worktree is clean and tracking `origin`:

```bash
git pull --ff-only
```

If the worktree is dirty, not tracking origin, or cannot fast-forward, do not overwrite local work. Report the drift and read the current canonical card with that caveat.

## Load canonical skill

Open and follow `bin/orama-system/skills/codex-mcp-debugging/SKILL.md`. Do not copy behavior from this wrapper.

## Windows UTF-8 note

```powershell
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```
