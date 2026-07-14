---
name: antigravity-agent
description: >-
  Operate the Antigravity CLI (`agy`) for fanning out light/parallel tasks
  alongside the main orchestration session — same fan-out tier as `kimi` and
  `cursor-agent`. Direct CLI invocation, NOT an OpenClaw agent config entry:
  see "Why direct CLI, not OpenClaw" for the root-cause history behind that
  choice. Verified live on macOS 2026-07-11 (v1.1.1).
version: 1.0.0
license: Apache 2.0
compatibility: darwin, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - agy
  - antigravity
  - antigravity cli
  - antigravity agent
  - fan out to agy
  - fan out to antigravity
  - gemini via antigravity
allowed-tools: bash, file-operations
---

# Antigravity Agent Skill

## Disambiguation

**`agy`** is Google's Antigravity CLI — a standalone agentic coding tool in
the same category as `kimi`, `cursor-agent`, and `codex`: a fan-out worker the
main session can dispatch light/parallel tasks to, NOT an internal oramasys
stage worker (does not belong in `bin/config/agent_registry.json`, which is
reserved for SOUL-file-backed OpenClaw/oramasys agents bound to a gateway
provider).

| Command | Runtime discovery | What it is |
|---------|-------------------|------------|
| `agy` | `command -v agy` | Google Antigravity CLI — use this |
| `kimi` | `command -v kimi` | Moonshot Kimi Code CLI — see `../kimi-agent/SKILL.md` |
| `cursor-agent` | `command -v cursor-agent` | Cursor's background agent — see `../cursor-agent/SKILL.md` |

## Why direct CLI, not OpenClaw (root-cause history, 2026-07-11)

An earlier session built a persistent OpenClaw agent (`gemini-coder`) around
a fabricated `google-antigravity` provider stanza in `openclaw.json` —
model names copied from `agy models` output, but wired to nothing. The
stanza had only a bare `models` array (name/price list), no `api`, no
`baseUrl`, unlike the real `google` provider (`{api, baseUrl, models}`) or
plugin-supplied providers like `codex` (`{}` — the installed plugin
supplies its own catalog). `openclaw plugins list` (71 entries) had zero
rows for "antigravity"; the ClawHub marketplace has no real Antigravity
provider plugin either. `openclaw models auth login --provider
google-antigravity` failed live with "Error: No provider plugins found" —
there was no code path that could ever authenticate or run inference
through OpenClaw for this provider. The `google-antigravity` provider
stanza and its `agy-*` alias entries were deleted from `openclaw.json` as
part of this correction; `gemini-coder` (the OpenClaw agent) now points at
the real `google` plugin (`google/gemini-3.1-pro-preview`) as a secondary
path, but is not the primary way to reach Antigravity.

**The actual Antigravity CLI (`agy`) needs none of that.** It can be discovered
from `PATH` and, when the current machine is authenticated, answers headless
prompts with zero additional setup — verified live: `agy -p "What is 2+2? Reply
with just the number."` returned `4` with no OAuth prompt, no TTY error. Use
this skill's direct-CLI pattern, mirroring `kimi-agent`, instead of routing
through OpenClaw's model/provider abstraction.

## Runtime Discovery

Do not hardcode host-local Antigravity binary or configuration paths in docs,
scripts, or examples. Discover the executable at runtime and print what the
current machine resolves:

```bash
AGY_BIN="$(command -v agy)" || {
  echo "agy not found on PATH" >&2
  exit 127
}
printf 'agy: %s\n' "$AGY_BIN"
```

Configuration and credential locations are host-specific. Inspect them only
when debugging a live machine, and avoid checking those paths into reusable
guidance.

## Provider Setup

**Status: WIRED when the current machine passes a smoke test.** Auth state is
host-specific. Before dispatching real work, run `agy -p "reply with exactly:
agy-ok"`; it should return `agy-ok` with no prompt or TTY requirement. If it
errors or asks for auth, stop and surface that state instead of assuming another
machine's configuration.

## Key Options (from `agy --help`, v1.1.1 — verified)

| Option | Purpose |
|--------|---------|
| `-p, --print` / `--prompt` | Headless single-turn — prints response to stdout (equivalent to `kimi -p`) |
| `--model <model>` | Override model for this session (see § Models below) |
| `--agent <agent>` | Select a named agent for the session (`agy agent`/`agy agents` lists them — empty by default: "Available agents:" with nothing after) |
| `-i, --prompt-interactive` | Run an initial prompt interactively, then continue the session |
| `-c, --continue` | Continue the most recent conversation |
| `--conversation <id>` | Resume a previous conversation by ID |
| `--mode <mode>` | `accept-edits` or `plan` |
| `--dangerously-skip-permissions` | Auto-approve all tool permission requests — trusted/CI only |
| `--sandbox` | Run in a sandbox with terminal restrictions enabled |
| `--add-dir <dir>` | Add an extra workspace directory (repeatable) |
| `--new-project` | Create a new project for this session |
| `--print-timeout <dur>` | Timeout for print mode wait (default `5m0s`) |
| `--log-file <path>` | Override CLI log file path |

Default to a sandboxed **plan/read-only pass** first. Do not let a background
worker modify files until a human approves the exact task, scope, and target
repository.

```bash
agy --mode plan --sandbox --add-dir "$PWD" \
  --model "Claude Sonnet 4.6 (Thinking)" \
  -p "Plan the requested edits. Do not modify files."
```

Approval gate: in an OpenClaw/Web Portal workflow, use the native
AskUserQuestion/HITL approval gate before switching to edit mode. In a plain
shell workflow, stop and ask the operator to approve the plan, diff scope, and
log directory before running `--mode accept-edits`:

```bash
printf 'Approve agy edit execution in %s? Type exactly YES: ' "$PWD" >&2
read -r APPROVED
[ "$APPROVED" = "YES" ] || { echo "agy edit execution not approved" >&2; exit 1; }
agy --mode accept-edits --sandbox --add-dir "$PWD" \
  --model "Claude Sonnet 4.6 (Thinking)" \
  -p "Execute only the approved edits."
```

Use `--add-dir` only for repository-scoped directories required by the task.
Avoid broad home-directory access. Reserve `--dangerously-skip-permissions` for
trusted or CI usage where the command, workspace, prompt, and approval record
are controlled. This matches Gemini CLI's documented safety model: sandboxing
reduces but does not eliminate risk, untrusted workspaces force tool prompts,
write/shell tools default to `ask_user`, and non-interactive plan workflows can
otherwise fall through into YOLO-style execution after approval-mode transitions.

## Models (from `agy models`, verified 2026-07-11)

```
Gemini 3.5 Flash (Medium)
Gemini 3.5 Flash (High)
Gemini 3.5 Flash (Low)
Gemini 3.1 Pro (Low)
Gemini 3.1 Pro (High)
Claude Sonnet 4.6 (Thinking)
Claude Opus 4.6 (Thinking)
GPT-OSS 120B (Medium)
```

**User-stated preference order (2026-07-11):** 1) `Claude Sonnet 4.6
(Thinking)`, 2) `Gemini 3.1 Pro (Low)`, 3) whatever other agent templates
use as their fallback defaults. Pass the exact string from `agy models`
via `--model`:

```bash
agy --model "Claude Sonnet 4.6 (Thinking)" -p "..."
```

**No automatic fallback chain** — same limitation class as every other
fan-out CLI in this stack (kimi, cursor-agent): if the primary model errors,
retry the same prompt with `--model "Gemini 3.1 Pro (Low)"` explicitly. Do
not assume `agy` retries across models on its own.

## Output Shape (verified live, v1.1.1)

**Clean answer-only stdout in print mode** — unlike `kimi -p`, which prepends
a `•`-prefixed narration line and appends a `To resume this session:`
footer. `agy -p "What is 2+2? Reply with just the number."` returned
exactly `4`, nothing else. Simpler to parse in scripts; still verify this
holds for longer/tool-using prompts before building a strict parser around
it — the smoke tests here used trivial no-tool prompts.

## Light Task Fanout Pattern

Same shape as the `kimi-agent`/`cursor-agent` pattern — headless,
backgrounded, `wait` to collect:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOG_PARENT="$REPO_ROOT/.agent/logs/agy"

# Fail closed if any reusable log parent is a symlink. This prevents predictable
# log paths from being redirected through attacker-created links.
for path in "$REPO_ROOT/.agent" "$REPO_ROOT/.agent/logs" "$LOG_PARENT"; do
  [ -L "$path" ] && { echo "refusing symlinked log path: $path" >&2; exit 1; }
done
mkdir -p "$LOG_PARENT"
chmod 700 "$REPO_ROOT/.agent" "$REPO_ROOT/.agent/logs" "$LOG_PARENT" 2>/dev/null || true

printf 'Approve background agy edit fan-out in %s? Type exactly YES: ' "$REPO_ROOT" >&2
read -r APPROVED
[ "$APPROVED" = "YES" ] || { echo "background agy fan-out not approved" >&2; exit 1; }

run_agy_task() {
  local name="$1"
  local prompt="$2"
  local log_dir out err
  log_dir="$(mktemp -d "$LOG_PARENT/${name}.XXXXXXXX")" || return 1
  out="$log_dir/stdout.txt"
  err="$log_dir/stderr.txt"

  if agy --mode accept-edits --sandbox --add-dir "$REPO_ROOT" \
    --model "Claude Sonnet 4.6 (Thinking)" \
    -p "$prompt" >"$out" 2>"$err"; then
    if [ ! -s "$out" ]; then
      echo "$name: agy exited 0 but produced empty stdout; inspect $err" >&2
      return 2
    fi
    echo "$name: success; output saved to $out"
  else
    local status=$?
    echo "$name: agy failed with exit $status; stderr saved to $err" >&2
    return "$status"
  fi
}

run_agy_task agy-task-a \
  "Add type annotations to scripts/discover.py; only functions, no variables" &
pid_a=$!

run_agy_task agy-task-b \
  "Rename all snake_case variables in tests/test_foo.py to camelCase" &
pid_b=$!

fail=0
wait "$pid_a" || fail=1
wait "$pid_b" || fail=1
exit "$fail"
```

Preserve every task's stdout/stderr log before parsing. Treat `exit 0` with
empty stdout as a per-task failure until the log proves the task intentionally
made only file edits and emitted no summary. The log guard above protects
against local path-hijack/symlink attacks; it is not a network MITM control.
Network trust still depends on the provider's TLS/auth path, and prompts/logs
must not include secrets.

**Division of labour (matches the kimi-agent/cursor-agent table — Antigravity
slots into the same "mechanical fan-out" tier, not the orchestrator tier):**

| Main session (orchestrator) | `agy` (fan-out worker) |
|------------------------------|--------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & policy review | Test scaffolding |
| Final crystallisation | Format / lint fixes |

## Commands Summary (v1.1.1, verified)

| Command | Purpose |
|---------|---------|
| `agy -p "<prompt>"` | Headless single-turn (see § Light Task Fanout Pattern) |
| `agy models` | List available models |
| `agy agent` / `agy agents` | List available named agents (empty by default) |
| `agy plugin list` \| `install` \| `uninstall` \| `enable` \| `disable` | Manage plugins |
| `agy install` | Configure environment paths and shell settings |
| `agy update` | Update CLI |
| `agy changelog` | Show changelog and release notes |
| `agy help` | Show help for subcommands |

## References

- Sibling fan-out agent (structural precedent for this skill):
  [`../kimi-agent/SKILL.md`](../kimi-agent/SKILL.md)
- `gemini-coder` OpenClaw agent identity, if configured in the current repo or
  operator environment (secondary path, real `google` provider — not the
  primary Antigravity pathway).
- Local-first fallback doctrine: [`../../SKILL.md § Local API Fallback`](../../SKILL.md)
- orama-system Stage 4 dispatch pattern: [`../../SKILL.md § MODE 2 Stage 4`](../../SKILL.md)

## Open Items (do not silently resolve — surface to user)

1. **`agy agent`/`agy agents` returns an empty list** ("Available agents:"
   with nothing after) — unclear if this means no named agents are
   configured, or if named agents are a feature this install hasn't set up.
   Not investigated further; `--model` selection works fine without it.
2. **Output-shape claim (clean stdout, no narration) only verified on
   trivial no-tool prompts** — re-verify before building a strict parser
   around real fan-out tasks that use tools/file edits, and treat exit-0 empty
   stdout as a per-task failure unless the preserved log proves otherwise.
3. **Per-task failure accounting** — parallel fan-out must collect each task's
   exit status independently; do not let one successful `wait` mask another
   task's failure or empty-success case.
4. **`agy plugin list` shows "No imported plugins."** — no plugins have
   been evaluated for this stack; treat as a fresh surface if a future need
   arises.
5. **Windows path unverified** — no PowerShell/Windows executable discovery
   checked for `agy`; do not assume parity with macOS `command -v` behavior.
