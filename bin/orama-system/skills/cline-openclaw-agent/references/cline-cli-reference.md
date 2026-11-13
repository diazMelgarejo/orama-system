# Cline CLI Reference (v3.0.34)

<!-- wandb-inference-working-config -->
## W&B inference, not the Cline CLI

When this guidance mentions Cline and the call is W&B inference,
use the OpenAI client and Weave setup in
[wandb-inference-working-config.md](wandb-inference-working-config.md).
The Cline CLI returns `invalid model ID` for the model that client
completes. Do not send a CoreWeave team/project string. Shell-source
the operator W&B env file before reading `DEEPSEEK_V4_FLASH_WANDB`.

> **Update 2026-11-10 (verified on CLI 3.0.74 by the Windows and Mac hosts; Cline benchmark finding).** The CLI is now
> 3.0.74. There is no `task` subcommand: the prompt is a bare positional argument. Cline's own default is act mode with
> tool auto-approval ON, so review or unattended runs should pass `--plan --auto-approve false` unless the operator
> authorises act mode. An npm install on Windows ships `cline.cmd`: never pass a prompt through a cmd shim; launch node
> with the package entry script. The text below is the 3.0.34 record and is kept as history.
>
> **Live working code:** `scripts/cline_autoresearcher.py` (`_cline_argv`, `_cline_launcher`, `dispatch_cline`,
> `dispatch_autoresearcher`) and `scripts/autoresearcher_lock.py` (`BackendLock`); the Windows watcher autostart is
> the AutoResearcher block in `platform/windows/start.ps1`.

Exhaustive reference for every command and flag of the `cline` CLI, verified
against `cline --help` on 2026-06-30.

## Binary

```text
~/.nvm/versions/node/v22.22.2/bin/cline  (symlink -> ../lib/node_modules/cline/bin/cline)
npm package: cline@3.0.34
```

Resolve with `command -v cline`. If absent, install with
`npm install -g cline` (Node >= 18).

## Top-Level Usage

```text
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

Manage MCP servers. Subcommands `install` and `add` accept a server name plus
target args — use the interactive wizard to prefill fields. Cline is an MCP
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
| `cline` | `zai/glm-5.3-flash` | WorkOS OAuth | Cline Credits billing |
| `cline-pass` | `cline-pass/glm-5.3-flash` | WorkOS OAuth | Same token as `cline`; `lastUsedProvider` |
| `anthropic` | `claude-fable-5` | API key | — |
| `openrouter` | `cohere/north-mini-code:free` | API key | — |
| `openai-compatible` | `gemini-3.8-flash` | API key | Custom baseUrl |
| `openai-codex` | — | OAuth | — |
| `gemini` | Saved model (host-specific) | API key | Selecting without an override can retain a different saved model |
| `sapaicore` | `gpt-5.5` | — | SAP AI Core |

## Upstream Endpoint

All Cline-managed providers (`cline`, `cline-pass`) call:
`https://api.cline.bot/api/v1/chat/completions`

The `cline-pass/` prefix on a model id is **stripped** before the request is
sent; the upstream model id is `zai/glm-5.3-flash`. Billed against Cline Credits
(`https://app.cline.bot/credits`).

## Non-Interactive Patterns

On CLI 3.0.74 the prompt is a bare positional argument and a ONE-WORD prompt is rejected as a mistyped
subcommand (the AutoResearcher controller pads it as "Task: <word>"; a prompt that starts with a hyphen is
padded too). Use prompts of two or more words in every example below.

```bash
# One-shot, JSON, auto-approve (agent-friendly)
cline "review the lock module" --json --auto-approve true -c /repo --thinking medium \
  -P cline-pass -m cline-pass/glm-5.3-flash --timeout 600 --retries 3

# Plan mode (no mutations)
cline "propose a refactor" --plan --json -c /repo

# Resume a session
cline --id 1782825530243_ayapk "continue with the next step" --json

# Background hub session
cline "long task" --zen -c /repo

# ACP server mode (for openclaw acp client bridge)
cline --acp

# Worktree isolation
cline "risky change" --worktree --json -c /repo

# List past sessions (no API cost)
cline history --json --limit 20
```
