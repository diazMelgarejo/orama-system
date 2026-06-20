---
name: codex-openclaw-agent
description: Creates and wires a named OpenClaw sub-agent (id=codex-agent) backed exclusively by OpenAI Codex CLI + GPT-5.5. Invoked explicitly as `openclaw run codex-agent`. Does NOT touch the default agent, the main orchestrator (ollama/qwen3.5:9b-nvfp4), the LaunchAgent plist, or the coder agent (lmstudio-win). Use when you need a GPT-5.5/Codex-native sub-agent for tasks that require OpenAI Codex execution, not for general coding tasks (those stay on lmstudio-win/coder). Do NOT use to change the default model routing.
version: "1.0"
agent_compatibility:
  - Claude
  - Hermes
  - Gemini
  - Codex
  - Cursor
  - WindSurf
  - Antigravity
  - OpenCode
  - 8gent.dev
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
---

# codex-openclaw-agent

Creates a named OpenClaw sub-agent (`codex-agent`) that always uses OpenAI
Codex CLI with GPT-5.5 as its backend. Invoked explicitly via
`openclaw run codex-agent`; never becomes the default backend.

## Preserved defaults (DO NOT TOUCH)

| Setting | Value | Owner |
| --- | --- | --- |
| Global `agents.defaults.model.primary` | `ollama/qwen3.5:9b-nvfp4` | LaunchAgent |
| `main` agent primary | `lmstudio-mac/qwen3.5-9b-mlx` | Existing config |
| `coder` agent primary | `lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` | Existing config |
| Ollama LaunchAgent plist | `com.orama.network-watch.plist` + `ai.openclaw.gateway` | System — never modified here |

## What this skill does

1. Probes Codex CLI auth and the real native `codex-supervisor` plugin.
2. Registers a new `codex` provider block through `openclaw config patch`
   pointing to Codex's local OpenAI-compatible app-server endpoint when the
   native plugin path is unavailable.
3. Creates the `codex-agent` agent entry in `openclaw.json` with
   `model.primary = "codex/gpt-5.5"` and `model_reasoning_effort = "medium"`
   unless the operator explicitly opts into `high` or `xhigh`.
4. Writes or merges generated sections for the agent runtime files under
   `$OPENCLAW_HOME/.openclaw/agents/codex-agent/`.
5. Generates `CODEX.md` plus a redacted binding record that references auth by
   location only.
6. Verifies backend identity is Codex/GPT-5.5, not Ollama.

## When to Use

- You need to route a specific task to `openclaw run codex-agent`.
- You want a Codex/GPT-5.5 execution path that coexists with existing routing.
- You are wiring a new cross-harness sub-agent from the ECC harness pattern.

## When NOT to Use

- General coding tasks → use the existing `coder` agent
  (`lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`).
- Changing the default model → never do this from this skill.
- Research or orchestration tasks → use `main`, `mac-researcher`, or
  `win-researcher`.

## Inputs

- Required: none (all paths are derived from `$OPENCLAW_ROOT` and `~/.codex`)
- Optional:
  - `effort` (`medium` | `high` | `xhigh`, default `medium`;
    `high` and `xhigh` are opt-in)
  - `dry_run` (`true` | `false`, default `false`)
  - `force` (`true` | `false`, default `false` — skip probe assertions)

## Procedure

Run `scripts/bind_codex_backend.sh` (see references for the full resolver
ladder). The steps in order:

1. **Probe** — read-only checks, no mutation.
2. **Provider registration** — add `codex` provider through `openclaw config patch`.
3. **Agent creation** — `openclaw-new-agent` overlay for `codex-agent`.
4. **Profile generation** — merge marked generated sections and write redacted refs.
5. **Verify** — assert backend identity.

Full data flow and edge cases: [`references/codex-backend-binding.md`](references/codex-backend-binding.md)

## Output Contract

```json
{
  "status": "ok|error",
  "agent_id": "codex-agent",
  "backend": "codex/gpt-5.5",
  "effort": "medium",
  "binding_path": "primary|idempotent-install|fallback",
  "verify_result": "ok|fail",
  "files_modified": [],
  "follow_up_actions": []
}
```

## Security

- Auth for Codex is referenced by path (`~/.codex/config.toml`) only.
- **No bearer token is ever copied into any generated file.**
- Paths in generated files use `~` or `${HOME}` — never literal `/Users/`.
- The `SECURITY.md` for `codex-agent` is operator-owned; this skill writes
  a scaffold only.

## Invariants (enforced by oramaclaw contract)

**Delegation path:** Sub-agent delegation is always written to
`agents.defaults.subagents.allowAgents` or `agents.list[id].subagents.allowAgents`.
The key `agents.bindings.*.allowAgents` is **rejected** by the oramaclaw control
plane — do not use it in any binder, bootstrap, or manifest.

**macOS `timeout`:** Never use bare `timeout N <cmd>` in shell scripts.
Use the gtimeout→timeout→unwrapped pattern:

```bash
_TIMEOUT_BIN=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || echo "")
if [ -n "$_TIMEOUT_BIN" ]; then "$_TIMEOUT_BIN" N <cmd>; else <cmd>; fi
```

**`codex review` invocation:** Always pass `< /dev/null`. Without it the process
blocks on stdin and hangs silently. Canonical form:

```bash
codex review "<prompt>" -c 'model_reasoning_effort="high"' < /dev/null
```

## See Also

- [`references/codex-backend-binding.md`](references/codex-backend-binding.md)
- [`scripts/bind_codex_backend.sh`](scripts/bind_codex_backend.sh)
- [`scripts/generate_codex_openclaw_profile.py`](scripts/generate_codex_openclaw_profile.py)
- [`../skills/openclaw-new-agent/SKILL.md`](../skills/openclaw-new-agent/SKILL.md)
- [`../skills/openclaw-stow/SKILL.md`](../skills/openclaw-stow/SKILL.md)
- [`../../hermes-harness/SKILL.md`](../../hermes-harness/SKILL.md)
