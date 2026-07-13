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

**`agy`** (`~/.local/bin/agy`) is Google's Antigravity CLI — a standalone
agentic coding tool in the same category as `kimi`, `cursor-agent`, and
`codex`: a fan-out worker the main session can dispatch light/parallel tasks
to, NOT an internal oramasys stage worker (does not belong in
`bin/config/agent_registry.json`, which is reserved for SOUL-file-backed
OpenClaw/oramasys agents bound to a gateway provider).

| Command | Binary | What it is |
|---------|--------|------------|
| `agy` | `~/.local/bin/agy` | Google Antigravity CLI — use this |
| `kimi` | `~/.kimi-code/bin/kimi` | Moonshot Kimi Code CLI — see `../kimi-agent/SKILL.md` |
| `cursor-agent` | `~/.local/bin/cursor-agent` | Cursor's background agent — see `../cursor-agent/SKILL.md` |

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

**The actual Antigravity CLI (`agy`) needs none of that.** It is already
installed, already authenticated (its config symlinks into
`~/.gemini/config/projects/`), and answers headless prompts with zero
additional setup — verified live: `agy -p "What is 2+2? Reply with just the
number." ` returned `4` with no OAuth prompt, no TTY error. Use this skill's
direct-CLI pattern, mirroring `kimi-agent`, instead of routing through
OpenClaw's model/provider abstraction.

## Canonical Install Locations (binary tracking)

**Tracked so any session can call the binary without re-discovering it —
mirrors the `kimi-agent` canonical-paths table.**

| Item | Path |
|------|------|
| Binary | `~/.local/bin/agy` |
| Version | `1.1.1` (verified 2026-07-11, darwin) |
| Config (symlinked) | `~/.antigravitycli/<project-id>.json` → `~/.gemini/config/projects/<project-id>.json` |
| Other local state | `~/.antigravity/`, `~/.antigravity-ide/` |
| Plugins | `agy plugin list` → "No imported plugins." by default |

Quick binary-location check for any agent/script before invoking Antigravity:

```bash
command -v agy >/dev/null 2>&1 || { echo "agy not installed — see antigravity-agent/SKILL.md"; exit 1; }
```

## Provider Setup

**Status: WIRED (verified 2026-07-11).** No login step needed on this
machine — `agy`'s config already resolves through `~/.gemini/config/`.
Smoke test: `agy -p "reply with exactly: agy-ok"` → `agy-ok`, no prompts, no
TTY requirement. If a fresh machine ever shows an auth error instead, that's
a genuinely different state from what's documented here — do not assume
parity, verify live before dispatching real work.

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
agy --model "Claude Sonnet 4.6 (Thinking)" \
  -p "Add type annotations to scripts/discover.py; only functions, no variables" \
  > /tmp/agy-task-a.txt &

agy --model "Claude Sonnet 4.6 (Thinking)" \
  -p "Rename all snake_case variables in tests/test_foo.py to camelCase" \
  > /tmp/agy-task-b.txt &

wait   # collect when done
```

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
- `gemini-coder` OpenClaw agent identity (secondary path, real `google`
  provider — not the primary Antigravity pathway):
  `~/.openclaw/agents/gemini-coder/IDENTITY.md`
- Local-first fallback doctrine: [`../../SKILL.md § Local API Fallback`](../../SKILL.md)
- orama-system Stage 4 dispatch pattern: [`../../SKILL.md § MODE 2 Stage 4`](../../SKILL.md)

## Open Items (do not silently resolve — surface to user)

1. **`agy agent`/`agy agents` returns an empty list** ("Available agents:"
   with nothing after) — unclear if this means no named agents are
   configured, or if named agents are a feature this install hasn't set up.
   Not investigated further; `--model` selection works fine without it.
2. **Output-shape claim (clean stdout, no narration) only verified on
   trivial no-tool prompts** — re-verify before building a strict parser
   around real fan-out tasks that use tools/file edits.
3. **`agy plugin list` shows "No imported plugins."** — no plugins have
   been evaluated for this stack; treat as a fresh surface if a future need
   arises.
4. **Windows path unverified** — no PowerShell/Windows install path checked
   for `agy`; do not assume parity with the macOS binary path above.
