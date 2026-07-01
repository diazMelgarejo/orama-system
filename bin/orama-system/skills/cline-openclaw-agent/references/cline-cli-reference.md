# Cline CLI Reference (v3.0.34)

Exhaustive reference for every command and flag of the `cline` CLI, verified
against `cline --help` on 2026-06-30.

## Binary

```
~/.nvm/versions/node/v22.22.2/bin/cline  (symlink -> ../lib/node_modules/cline/bin/cline)
npm package: cline@3.0.34
```

Resolve with `command -v cline`. If absent, install with
`npm install -g cline` (Node >= 18).

## Top-Level Usage

```
cline [options] [command] [prompt]
```

`prompt` is your task as a single quoted argument, e.g.
`cline "fix the tests"`. Default mode is **act** with auto-approve enabled.

## Global Options

| Flag | Default | Description |
| --- | --- | --- |
| `-V, --version` | — | Output version number |
| `-p, --plan` | off | Run in **plan mode** (no mutations) |
| `--json` | off | Output messages as JSON instead of styled text (agent-friendly) |
| `--auto-approve <boolean>` | `true` | Set tool auto-approval for all tools |
| `-c, --cwd <path>` | current | Working directory |
| `--thinking <level>` | provider default | `none\|low\|medium\|high\|xhigh`; bare `--thinking` = `medium` |
| `--compaction <mode>` | `basic` | `agentic\|basic\|off` — context compaction mode |
| `-i, --tui` | off | Open the terminal user interface (interactive) |
| `--id <session-id>` | — | Resume an existing session by ID |
| `-P, --provider <id>` | `cline` | Provider id |
| `-k, --key <api-key>` | — | API key override for this run |
| `-m, --model <model-id>` | provider default | Model to use with the selected provider |
| `-s, --system <system-prompt>` | — | Override the default system prompt |
| `-z, --zen` | off | Start a session that runs in the background hub |
| `--retries [value]` | `6` | Max consecutive mistakes before exiting |
| `-t, --timeout <seconds>` | `0` | Timeout (0 = no timeout) |
| `--acp` | off | Run in Agent Client Protocol mode (editor integration) |
| `--config <path>` | `~/.cline/data/settings` | Configuration directory |
| `--data-dir <path>` | `~/.cline` | Isolated local state directory |
| `--hooks-dir <path>` | `~/.cline/hooks` | Additional hooks directory |
| `--worktree` | off | Auto-create a detached git worktree under `~/.cline/worktrees/` |
| `--update` | off | Check for updates and install if available |
| `--kanban` | off | Run the kanban app |
| `-v, --verbose` | off | Verbose output |
| `-h, --help` | — | Display help |

## Commands

### `auth [options] [provider]`
Authenticate a provider and configure which model is used. Interactive —
requires a TTY. Example: `cline auth cline-pass`.

### `config [options]`
Show current configuration. Interactive mode requires a TTY; use
`cline config --json` if supported for non-interactive output.

### `plugin`
Manage Cline Plugins.

### `skill [args...]`
Manage Cline Skills via the open skills CLI (`npx skills`).

### `connect [options] [channel]`
Connect to an external channel (e.g. telegram, discord).

### `mcp`
Manage MCP servers. Subcommand: `install|add [options] <name> [targetArgs...]`
— open the MCP add wizard with server fields prefilled. Cline is an MCP
**client**, not a server.

### `doctor`
Diagnose and fix configuration issues.

### `history | h [options] [command]`
List session history or manage saved sessions.

| Flag | Default | Description |
| --- | --- | --- |
| `--json` | off | Output as JSON |
| `--limit <count>` | `50` | Max sessions to show |
| `--page <number>` | — | Page number |
| `--config <dir>` | — | Configuration directory |

Subcommands: `delete`, `update`, `export <sessionId>` (export as standalone
HTML).

### `hook`
Handle a hook payload from stdin.

### `schedule`
Manage scheduled tasks.

### `hub`
Manage the local hub daemon (`ws://127.0.0.1:25463/hub`). Started by
`cline --zen` or `cline hub`.

### `dashboard [options]`
Start the Cline Hub dashboard and open it in a browser.

### `update [options]`
Check for updates and install if available.

### `version`
Show Cline CLI version number.

### `kanban`
Run the kanban app.

## Providers (from `~/.cline/data/settings/providers.json`)

| Provider id | Default model | Auth | Notes |
| --- | --- | --- | --- |
| `cline` | `zai/glm-5.2` | WorkOS OAuth | Cline Credits billing |
| `cline-pass` | `cline-pass/glm-5.2` | WorkOS OAuth | Same token as `cline`; `lastUsedProvider` |
| `anthropic` | `claude-fable-5` | API key | — |
| `openrouter` | `minimax/minimax-m2.5:free` | API key | — |
| `openai-compatible` | `google/gemini-3.1-pro-preview` | API key | Custom baseUrl |
| `openai-codex` | — | OAuth | — |
| `gemini` | `gemini-3.5-flash` | API key | — |
| `sapaicore` | `gpt-5.5` | — | SAP AI Core |

## Upstream Endpoint

All Cline-managed providers (`cline`, `cline-pass`) call:
`https://api.cline.bot/api/v1/chat/completions`

The `cline-pass/` prefix on a model id is **stripped** before the request is
sent; the upstream model id is `zai/glm-5.2`. Billed against Cline Credits
(`https://app.cline.bot/credits`).

## Non-Interactive Patterns

```bash
# One-shot, JSON, auto-approve (agent-friendly)
cline "task" --json --auto-approve true -c /repo --thinking medium \
  -P cline-pass -m cline-pass/glm-5.2 --timeout 600 --retries 3

# Plan mode (no mutations)
cline "propose a refactor" --plan --json -c /repo

# Resume a session
cline --id 1782825530243_ayapk "continue" --json

# Background hub session
cline "long task" --zen -c /repo

# ACP server mode (for openclaw acp client bridge)
cline --acp

# Worktree isolation
cline "risky change" --worktree --json -c /repo

# List past sessions (no API cost)
cline history --json --limit 20
```
