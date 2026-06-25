---
name: cursor-agent
description: >-
  Install, configure, and operate the Cursor background agent CLI (`agent`) for
  fanning out light tasks in parallel alongside the main Sonnet 4.6 session.
  Cross-platform: macOS/Linux via bash installer, Windows via PowerShell.
version: 1.0.0
license: Apache 2.0
compatibility: darwin, linux, windows, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - cursor agent
  - cursor-agent
  - fan out tasks
  - cursor cli
  - grok agent
  - agent --help
allowed-tools: bash, file-operations
---

# Cursor Agent Skill

## Purpose

Use the Cursor background agent (`agent` CLI, binary at `~/.grok/bin/agent`) to
fan out **light, parallelisable tasks** alongside the main Sonnet 4.6 orchestration
session. The pattern: Sonnet 4.6 keeps judgment, architecture, and synthesis; cursor
agents handle mechanical subtasks (file rewriting, grep-and-replace, doc generation,
test scaffolding) concurrently.

## Install

### macOS / Linux

```bash
curl https://cursor.com/install -fsS | bash
# Adds ~/.grok/bin/ to PATH. Re-source shell or open a new terminal.
```

Verify:

```bash
agent --version     # should print a version string
agent models        # confirm at least one model is listed
```

### Windows (PowerShell 5+)

```powershell
iex (iwr -UseBasicParsing https://cursor.com/install.ps1).Content
# Appends %LOCALAPPDATA%\Programs\cursor to PATH
```

Verify (PowerShell):

```powershell
agent --version
agent models
```

### Authentication

```bash
agent login          # opens browser OAuth flow; tokens stored in OS keychain
agent login --oauth  # explicit OAuth (same as default; useful for scripting)
```

## Key Commands (from `agent --help`)

| Command | Purpose |
|---------|---------|
| `agent -p "prompt"` | Single-turn headless prompt — prints result to stdout and exits |
| `agent -m <model>` | Override model (default: `grok-build`) |
| `agent --effort <level>` | Effort level: `low`, `medium`, `high`, `xhigh`, `max` |
| `agent --output-format json` | Machine-readable JSON output (headless only) |
| `agent --max-turns <N>` | Cap agent turns (prevents runaway loops) |
| `agent --cwd <dir>` | Run in a different directory |
| `agent -w [name]` | Start in a new git worktree |
| `agent models` | List available models |
| `agent mcp` | Manage MCP server configurations |
| `agent memory` | Manage cross-session memory |
| `agent sessions` | List, search, or restore sessions |
| `agent agent stdio` | Run agent over stdio (programmatic pipe integration) |
| `agent agent headless` | Run headlessly over Cursor WebSocket relay |
| `agent inspect` | Show configuration Grok discovers for this directory |

## Light Task Fanout Pattern

Use `agent -p` single-turn mode to parallelize tasks that don't need judgment:

```bash
# Dispatch 3 light tasks in parallel (background jobs)
agent -p "Add type annotations to scripts/discover.py" \
      -m grok-build --effort medium --output-format json &

agent -p "Write docstrings for all public functions in bin/orama-system/skills/cursor-agent/SKILL.md" \
      -m grok-build --effort low --output-format json &

agent -p "Run tests and report failures" \
      -m grok-build --effort low &

wait  # collect all when done
```

**Division of labour:**

| Main session (Sonnet 4.6) | Cursor agent (grok-build) |
|--------------------------|--------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & CIDF review | Test scaffolding |
| Final crystallisation | Format/lint fixes |

**Budget rule:** cursor agents consume Cursor API credits (not Anthropic tokens).
Light tasks = `--effort low` or `medium`. Reserve `high`/`xhigh` for cases where
a cursor agent is the primary solver, not a helper.

## Integrating with orama-system Workflow

In Stage 4 (Masterful Execution), dispatch mechanical subtasks as cursor agent
single-turns and await them while the main session proceeds with judgment work:

```bash
# Stage 4 parallel dispatch example
_AGENT_JOBS=()
agent -p "Scan bin/ for TODO comments and produce a markdown list" \
      --output-format json > /tmp/todos.json &
_AGENT_JOBS+=($!)

# ... do judgment work in main session ...

# Collect when done
wait "${_AGENT_JOBS[@]}"
cat /tmp/todos.json | python3 -c "import sys,json; [print(l) for l in json.load(sys.stdin).get('lines',[])]"
```

## Windows / Hermes Harness

On Windows, the install adds `agent` to the user `PATH` automatically.
Run from PowerShell or Git Bash — both work.

```powershell
# PowerShell single-turn
agent -p "List all .py files modified in the last 24h" --output-format json
```

From Hermes one-shot, prefix with `hermes chat --provider nous` for provider tasks;
use `agent -p` directly for file/code tasks that don't need Nous Portal credentials.

## Worktree Isolation

For tasks that write files, use `agent -w` to isolate in a git worktree and avoid
conflicts with the main session:

```bash
agent -w cursor-agent-fix -p "Refactor scripts/foo.py to add logging"
# Works in a fresh worktree; merge back with git after review
```

## MCP Integration

Cursor agents can use MCP servers. Register servers the same way as Claude Code:

```bash
agent mcp add --name my-server --command "npx my-mcp-server"
agent mcp list
```

MCP config is shared across Cursor projects unless `--cwd` overrides the project root.

## Caution

- `--always-approve` skips all tool permission prompts — use only in trusted CI/CD
- `agent agent headless` uses Cursor's WebSocket relay (requires network); prefer `stdio` for local CI
- Log output is written to `~/.grok/logs/` — check there if an agent run hangs
- On Windows, `%LOCALAPPDATA%\Programs\cursor\agent.exe` — ensure it is on `PATH` before invoking from PT scripts

## References

- Platform affinity (when to use cursor agents vs Hermes vs OpenClaw): [`../hermes-harness/references/platform-affinity-routing.md`](../hermes-harness/references/platform-affinity-routing.md)
- orama-system Stage 4 execution: [`../../../SKILL.md § MODE 2 Stage 4`](../../../SKILL.md)
- Win PATH bootstrap: [`../hermes-harness/SKILL.md § Windows Bring-Up`](../hermes-harness/SKILL.md)
