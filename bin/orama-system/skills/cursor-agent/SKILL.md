---
name: cursor-agent
description: >-
  Install, configure, and operate the Cursor Agent CLI (`cursor-agent`) for
  fanning out light tasks in parallel alongside the main Sonnet 4.6 session.
  Cross-platform: macOS/Linux via bash installer, Windows via PowerShell.
  DO NOT confuse with `agent` (Grok Build TUI at ~/.grok/bin/agent) — different tool.
version: 1.1.0
license: Apache 2.0
compatibility: darwin, linux, windows, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - cursor agent
  - cursor-agent
  - fan out tasks
  - cursor cli
  - cursor background agent
allowed-tools: bash, file-operations
---

# Cursor Agent Skill

## Disambiguation

**`cursor-agent`** (`~/.local/bin/cursor-agent`) is Cursor's native background agent CLI.
It is **NOT** the same as `agent` (`~/.grok/bin/agent`, the Grok Build TUI).
Always invoke Cursor agents as `cursor-agent`, never as bare `agent`.

| Command | Binary | What it is |
|---------|--------|------------|
| `cursor-agent` | `~/.local/bin/cursor-agent` | Cursor's background agent — use this |
| `agent` | `~/.grok/bin/agent` | Grok Build TUI — separate product |

## Install

### macOS / Linux

```bash
curl https://cursor.com/install -fsS | bash
# Installs to ~/.local/bin/cursor-agent; adds ~/.local/bin to PATH
```

Verify:

```bash
cursor-agent --version    # e.g. 2026.06.24-00-45-58-9f61de7
cursor-agent models       # list available models
```

### Windows (PowerShell 5+)

```powershell
iwr -UseBasicParsing https://cursor.com/install.ps1 | iex
# Installs to %LOCALAPPDATA%\cursor-agent\ (versioned shims under versions\)
```

Canonical paths (cross-platform):

| OS | `cursor-agent` binary | Permanent PATH entry |
|----|----------------------|----------------------|
| macOS / Linux | `~/.local/bin/cursor-agent` | `~/.local/bin` |
| Windows | `%LOCALAPPDATA%\cursor-agent\cursor-agent.cmd` | `%LOCALAPPDATA%\cursor-agent` |

Idempotent PATH bootstrap (orama-system repo root):

```powershell
.\platform\windows\ensure-partner-cli-paths.ps1
```

Verify (PowerShell):

```powershell
cursor-agent --version
cursor-agent models
```

### Authentication

```bash
cursor-agent login          # browser OAuth flow; tokens stored in OS keychain
cursor-agent status         # verify login, show account info
```

Set API key via env var instead of browser flow:

```bash
export CURSOR_API_KEY="sk-..."   # never commit; load from macOS Keychain or .env
cursor-agent models              # confirms key is accepted
```

## Available Models

Key models for task fanout (from `cursor-agent models`):

| Model string | Display name | When to use |
|---|---|---|
| `composer-2.5` | Composer 2.5 | **Default for all light/parallel tasks** |
| `auto` | Auto | Fallback when composer-2.5 unavailable or task ambiguous |
| `claude-opus-4-8-low` | Opus 4.8 Low | Mechanical tasks (format, rename, scaffold) |
| `claude-opus-4-8-medium` | Opus 4.8 Medium | Standard coding tasks |
| `claude-opus-4-8-high` | Opus 4.8 1M | Complex refactors |
| `gpt-5.3-codex-low` | Codex 5.3 Low | Fast, cheap file edits |
| `claude-4.6-sonnet-medium` | Sonnet 4.6 1M | **Orchestrator-override only** — dispatched exclusively when Opus 4.8 Ultracode / Fable 5 workflow explicitly demands it |

Parameterised model override syntax (bracket notation):

```bash
cursor-agent --model 'claude-opus-4-8[context=1m,effort=high,fast=false]' ...
```

## Model Selection Policy

Three tiers — apply in order:

| Tier | Model | When |
|------|-------|------|
| 1 — Default | `composer-2.5` | All light/parallel tasks; use unless there is an explicit reason not to |
| 2 — Fallback | `auto` | When `composer-2.5` is unavailable or the task is ambiguous and Cursor should self-select |
| 3 — Orchestrator-override | `claude-4.6-sonnet-medium` | ONLY when an orchestrator (Opus 4.8 Ultracode or Fable 5 workflow) explicitly demands it for a fan-out subtask. NOT a general default. |

**Never use `claude-4.6-sonnet-medium` as a default.** If no orchestrator has demanded it, use `composer-2.5` (or `auto` as fallback).

## Key Options (from `cursor-agent --help`)

| Option | Purpose |
|--------|---------|
| `--print` / `-p` | Headless single-turn — prints result to stdout (all tools: write, shell) |
| `--model <id>` | Override model |
| `--output-format <fmt>` | `text` \| `json` \| `stream-json` (with `--print`) |
| `--mode plan` | Read-only planning mode (no file edits) |
| `--mode ask` | Q&A explanations, read-only |
| `--auto-review` | Smart Auto: auto-run safe tool calls, prompt on risky ones |
| `--force` / `--yolo` | Auto-approve all tool calls (trusted CI only) |
| `--worktree [-w] [name]` | Isolated git worktree at `~/.cursor/worktrees/<repo>/<name>` |
| `--worktree-base <ref>` | Branch/ref to base new worktree on |
| `--trust` | Trust workspace without prompting (headless mode only) |
| `--sandbox enabled\|disabled` | Override sandbox mode |
| `--resume [chatId]` | Resume a previous session |
| `--continue` | Continue most recent session |

## Light Task Fanout Pattern

**Composer 2.5** (`composer-2.5`) is the default model for parallelising light work
alongside the main orchestration session. Use `auto` as fallback when `composer-2.5`
is unavailable.

```bash
# Parallel single-turn jobs (background)
cursor-agent --print --model composer-2.5 \
  "Add type annotations to scripts/discover.py; only functions, no variables" \
  --output-format json > /tmp/task-a.json &

cursor-agent --print --model gpt-5.3-codex-low \
  "Rename all snake_case variables in tests/test_foo.py to camelCase" \
  --output-format json > /tmp/task-b.json &

wait   # collect when done
```

**Division of labour:**

| Main session (Sonnet 4.6 full orchestration) | cursor-agent (composer-2.5 default) |
|----------------------------------------------|-------------------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & policy review | Test scaffolding |
| Final crystallisation | Format / lint fixes |
| AFRP gate | Single-file refactors |

**Budget note:** `cursor-agent` consumes Cursor credits (not Anthropic API tokens).
Light tasks = `--model composer-2.5` (default) or `--model auto` (fallback) or `gpt-5.3-codex-low`.

## Worktree Isolation

For tasks that write files and must not collide with the main session:

```bash
cursor-agent -w cursor-fix-$(date +%s) \
  --print --model composer-2.5 \
  "Refactor scripts/foo.py to add structured logging"
# Runs in ~/.cursor/worktrees/<repo>/cursor-fix-<ts>/
# Review and merge back with git after the agent completes
```

## orama-system Stage 4 Integration

In Stage 4 (Masterful Execution), dispatch mechanical subtasks as cursor-agent
headless jobs while the main session handles judgment work:

```bash
# Example Stage 4 parallel dispatch
_JOBS=()

cursor-agent --print --model composer-2.5 \
  "Scan bin/ for TODO comments; output as JSON list" \
  --output-format json > /tmp/todos.json &
_JOBS+=($!)

cursor-agent --print --model gpt-5.3-codex-low \
  "Generate pytest stubs for every function in scripts/new_module.py" \
  --trust > /tmp/test-stubs.py &
_JOBS+=($!)

# Main session does judgment work here ...

wait "${_JOBS[@]}"
```

## MCP Integration

Cursor agents inherit the MCP servers configured in the workspace `.cursor/mcp.json`.
Manage them:

```bash
cursor-agent mcp list
cursor-agent mcp add --name my-server --command "npx my-mcp-server"
```

Approve all MCPs automatically in headless mode:

```bash
cursor-agent --print --approve-mcps --model composer-2.5 "..."
```

## Windows / Hermes Harness

On Windows, invoke from PowerShell or Git Bash:

```powershell
cursor-agent --print --model composer-2.5 "task here" --trust
```

From a Hermes-scripted workflow:

```bash
# In Git Bash on Windows
cursor-agent --print --model gpt-5.3-codex-low \
  "List all .py files modified in the last 24h" --output-format json
```

## Update

```bash
cursor-agent update      # update to latest version
cursor-agent about       # show version + system info
```

## Commands Summary

| Command | Purpose |
|---------|---------|
| `cursor-agent login` | Authenticate via browser OAuth |
| `cursor-agent logout` | Sign out and clear stored auth |
| `cursor-agent status` | Show auth status and account |
| `cursor-agent models` | List available models |
| `cursor-agent mcp` | Manage MCP servers |
| `cursor-agent worker` | Start private cloud worker |
| `cursor-agent update` | Update to latest version |
| `cursor-agent about` | Version + system info |
| `cursor-agent ls` | Resume a chat session |
| `cursor-agent resume` | Resume latest chat session |

## References

- Platform affinity (when to use cursor-agent vs Hermes vs OpenClaw): [`../hermes-harness/references/platform-affinity-routing.md`](../hermes-harness/references/platform-affinity-routing.md)
- orama-system Stage 4: [`../../../SKILL.md § MODE 2 Stage 4`](../../../SKILL.md)
- Win PATH bootstrap: [`../hermes-harness/SKILL.md § Windows Bring-Up`](../hermes-harness/SKILL.md)
