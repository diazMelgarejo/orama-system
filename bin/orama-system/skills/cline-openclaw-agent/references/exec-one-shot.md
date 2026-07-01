# Exec One-Shot (Shell-Out Bridge)

The simplest bridge: the OpenClaw agent invokes `cline` as a subprocess via the
exec tool. Works now with zero config — `tools.exec.security: "full"` is
already set.

## Canonical one-shot (agent-friendly)

```bash
cline "refactor lib/server/openclaw-thinking.js to add a cache" \
  --json \
  --auto-approve true \
    -c $HOME/code/OpenClaw \
  --thinking medium \
  -P cline-pass -m cline-pass/glm-5.2 \
  --timeout 600 --retries 3
```

| Flag | Why |
| --- | --- |
| `--json` | Parseable output for the OpenClaw agent to ingest |
| `--auto-approve true` | No approval prompts (required for non-TTY) |
| `-c <dir>` | Pin the working directory (don't rely on cwd) |
| `--thinking medium` | Match the OpenClaw agent's `thinkingDefault` |
| `-P cline-pass -m cline-pass/glm-5.2` | Use the Cline GLM-5.2 provider |
| `--timeout 600` | Bound long tasks (10 min) |
| `--retries 3` | Limit consecutive mistakes before exit |

## Plan mode (no mutations)

```bash
cline "propose a refactor of lib/foo.js, don't change anything" \
  --plan --json -c /repo
```

Plan mode returns a plan without executing tool calls. Safe for read-only
analysis.

## Resume a session (multi-turn handoff)

```bash
# First turn
cline "fix the tests" --json -c /repo
# → outputs a session id, e.g. 1782825530243_ayapk

# Next turn (continue)
cline --id 1782825530243_ayapk "continue from where you left off" --json
```

Session ids are also available via `cline history --json --limit 1`.

## Worktree isolation (risky changes)

```bash
cline "experimental rewrite of the auth module" \
  --worktree --json -c /repo
```

Creates a detached git worktree under `~/.cline/worktrees/` so the main
working tree is untouched. Merge manually after review.

## Background hub session (long tasks)

```bash
cline "run the full test suite and fix all failures" \
  --zen -c /repo
```

`--zen` starts the session in the background hub (`ws://127.0.0.1:25463/hub`).
Monitor via `cline dashboard` or the Cline Hub UI. See
[hub-daemon.md](hub-daemon.md).

## Custom system prompt

```bash
cline "review this PR" \
  --json -c /repo \
  -s "You are a senior code reviewer. Be concise. Reject PRs that introduce secrets."
```

## Provider/model overrides

```bash
# Use Anthropic Claude instead of Cline GLM
cline "task" -P anthropic -m claude-fable-5 --json -c /repo

# Use OpenRouter free tier
cline "task" -P openrouter -m minimax/minimax-m2.5:free --json -c /repo

# API key override for one run
cline "task" -P openrouter -k sk-or-v1-... --json -c /repo
```

See [provider-auth.md](provider-auth.md) for the full provider list.

## Compaction control

```bash
cline "very long task" --compaction agentic --json -c /repo   # smart compaction
cline "short task" --compaction off --json -c /repo           # no compaction
```

| Mode | Behavior |
| --- | --- |
| `basic` (default) | Standard context compaction |
| `agentic` | Agent-driven compaction (smarter, more tokens) |
| `off` | No compaction (full context retained until limit) |

## Wrapper script

See [../scripts/exec_cline.sh](../scripts/exec_cline.sh) for a safe wrapper
that handles provider selection, JSON parsing, timeout, and error reporting.

## Cost note

`cline-pass` calls bill against **Cline Credits**
(`https://app.cline.bot/credits`). `cline` (base) also bills Cline Credits.
`openrouter`/`anthropic`/`gemini` providers bill their own accounts. Check
balance before long runs. The OpenClaw agent's own model (`openrouter/z-ai/glm-5.2`)
bills OpenRouter, not Cline Credits.
