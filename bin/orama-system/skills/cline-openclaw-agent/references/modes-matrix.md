# Cline CLI Modes Matrix (Exhaustive)

Every Cline CLI mode, when to use it, and how it maps to OpenClaw delegation.

## Execution Modes

| Mode | Flag | Mutates? | Interactive? | Use case |
| --- | --- | --- | --- | --- |
| **Act** | (default) | yes | no (with `--auto-approve true`) | Execute a task with tool loops |
| **Plan** | `-p, --plan` | no | no | Propose a plan without changes; read-only analysis |
| **TUI** | `-i, --tui` | yes | yes (TTY) | Interactive terminal UI; not for agent delegation |
| **Zen/Hub** | `-z, --zen` | yes | no | Background hub session; long-running tasks |
| **ACP** | `--acp` | yes | no (stdio) | Agent Client Protocol server; for `openclaw acp client` |
| **Worktree** | `--worktree` | yes (in worktree) | no | Isolated git worktree; safe for risky changes |
| **Kanban** | `--kanban` | no | yes | Kanban board app; project tracking |

## Output Modes

| Mode | Flag | Description |
| --- | --- | --- |
| **Styled text** | (default) | Human-readable colored output |
| **JSON** | `--json` | Machine-readable JSON messages (agent-friendly) |
| **Verbose** | `-v, --verbose` | Detailed logging to stderr |

## Thinking Levels

| Level | Flag | Notes |
| --- | --- | --- |
| none | `--thinking none` | No reasoning |
| low | `--thinking low` | Light reasoning |
| medium | `--thinking medium` | Bare `--thinking` = medium; matches OpenClaw default |
| high | `--thinking high` | Deep reasoning |
| xhigh | `--thinking xhigh` | Maximum reasoning |

Omit `--thinking` to leave the provider default. OpenRouter GLM-5.2 supports
`xhigh`/`high` (default `high`); `medium` may be clamped to `high` upstream.

## Compaction Modes

| Mode | Flag | Behavior |
| --- | --- | --- |
| basic | `--compaction basic` (default) | Standard context compaction |
| agentic | `--compaction agentic` | Agent-driven smart compaction |
| off | `--compaction off` | No compaction; full context until limit |

## Management Commands

| Command | Purpose | Interactive? |
| --- | --- | --- |
| `auth [provider]` | Authenticate + configure model | yes (TTY) |
| `config` | Show current configuration | yes (TTY) |
| `plugin` | Manage Cline Plugins | yes |
| `skill [args]` | Manage Cline Skills (`npx skills`) | yes |
| `connect [channel]` | Connect to external channel (telegram/discord) | yes |
| `mcp` | Manage MCP servers (client-side; `install\|add`) | yes |
| `doctor` | Diagnose + fix config issues | no |
| `history \| h` | List/export/delete session history | no (`--json`) |
| `hook` | Handle a hook payload from stdin | no |
| `schedule` | Manage scheduled tasks | yes |
| `hub` | Manage the local hub daemon | no |
| `dashboard` | Start Cline Hub dashboard in browser | yes |
| `update` | Check + install updates | no |
| `version` | Show version | no |
| `kanban` | Run kanban app | yes |

## Session Management

| Action | Command |
| --- | --- |
| List sessions | `cline history --json --limit 50` |
| Resume a session | `cline --id <session-id> "continue" --json` |
| Export a session (HTML) | `cline history export <session-id>` |
| Delete a session | `cline history delete <session-id>` |
| Update a session | `cline history update <session-id>` |

## Provider/Model Selection

| Flag | Description |
| --- | --- |
| `-P, --provider <id>` | Provider id (default `cline`) |
| `-m, --model <model-id>` | Model for the session |
| `-k, --key <api-key>` | API key override for one run |

Providers: `cline`, `cline-pass`, `anthropic`, `openrouter`, `openai-compatible`,
`openai-codex`, `gemini`, `sapaicore`. See [provider-auth.md](provider-auth.md).

## Isolation/State Flags

| Flag | Default | Description |
| --- | --- | --- |
| `--config <path>` | `~/.cline/data/settings` | Configuration directory |
| `--data-dir <path>` | `~/.cline` | Isolated local state |
| `--hooks-dir <path>` | `~/.cline/hooks` | Additional hooks directory |
| `--worktree` | off | Detached git worktree under `~/.cline/worktrees/` |

## Bounds

| Flag | Default | Description |
| --- | --- | --- |
| `--retries [value]` | 6 | Max consecutive mistakes before exit |
| `-t, --timeout <seconds>` | 0 | Timeout (0 = none) |

## OpenClaw Delegation Mapping

| OpenClaw need | Cline mode | Command |
| --- | --- | --- |
| One-shot task, parseable result | Act + JSON | `cline "task" --json --auto-approve true` |
| Read-only analysis | Plan + JSON | `cline "task" --plan --json` |
| Streaming structured delegation | ACP | `openclaw acp client --server cline --server-args --acp` |
| Long background task | Zen | `cline "task" --zen` |
| Risky change, isolate | Worktree | `cline "task" --worktree --json` |
| Cline calls OpenClaw tools | MCP | `openclaw mcp serve` → `cline mcp install` |
| Resume across turns | Session id | `cline --id <id> "continue" --json` |
