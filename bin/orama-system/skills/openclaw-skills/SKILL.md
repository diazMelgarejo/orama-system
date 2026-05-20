---
name: openclaw-skills
description: Canonical master skill for The Nine Skills that configure OpenClaw instances deterministically across Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, and 8gent.dev.
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
---

# OpenClaw Skills

This folder is the canonical home for The Nine Skills used to operate OpenClaw configuration. These skills are executable standards, not passive docs: every supported agent must use the relevant skill instead of reconstructing OpenClaw procedures from memory.

The skills are designed for deterministic use through direct skill loading, MCP middleware, CLI wrappers, editor rules, or Perpetua-Tools dispatch. They must produce the same files, naming, model routing, stow behavior, and restart flow regardless of the invoking agent.

## The Nine Skills

| Skill ID | Purpose | Skill File |
|----------|---------|------------|
| `openclaw-new-agent` | Creates a complete agent entry, directory tree, required directive files, script folders, and optional parent/child wiring. | [skills/openclaw-new-agent/SKILL.md](skills/openclaw-new-agent/SKILL.md) |
| `openclaw-add-channel` | Adds Telegram, Slack, or WhatsApp channels and runs the full secrets, config, stow, restart, and verification pipeline. | [skills/openclaw-add-channel/SKILL.md](skills/openclaw-add-channel/SKILL.md) |
| `openclaw-add-cron` | Adds recurring, interval, or one-shot scheduled jobs while handling transient `jobs.json` safely. | [skills/openclaw-add-cron/SKILL.md](skills/openclaw-add-cron/SKILL.md) |
| `openclaw-dream-setup` | Configures nightly memory distillation, memory files, archives, cron, QMD indexes, and startup sequence updates. | [skills/openclaw-dream-setup/SKILL.md](skills/openclaw-dream-setup/SKILL.md) |
| `openclaw-add-script` | Scaffolds deterministic shell scripts with JSON-only stdout, stderr logging, strict shell flags, and tool docs. | [skills/openclaw-add-script/SKILL.md](skills/openclaw-add-script/SKILL.md) |
| `openclaw-add-secret` | Stores credentials through macOS Keychain and updates all required shell/provisioning secret files. | [skills/openclaw-add-secret/SKILL.md](skills/openclaw-add-secret/SKILL.md) |
| `openclaw-status` | Runs the standard health check for gateway, launchd, channels, agents, cron jobs, and recent errors. | [skills/openclaw-status/SKILL.md](skills/openclaw-status/SKILL.md) |
| `openclaw-restart` | Performs the canonical restart sequence: remove transient cron state, stow, kickstart, wait, and verify channels. | [skills/openclaw-restart/SKILL.md](skills/openclaw-restart/SKILL.md) |
| `openclaw-stow` | Deploys OpenClaw config through GNU Stow with `jobs.json` conflict handling baked in. | [skills/openclaw-stow/SKILL.md](skills/openclaw-stow/SKILL.md) |

## Universal Invocation Protocol

All agents must follow [references/universal-skill-protocol.md](references/universal-skill-protocol.md).

The required invocation envelope is:

```json
{
  "skill_id": "openclaw-add-secret",
  "args": {
    "secret_name": "telegram-bot-token"
  },
  "agent_id": "codex",
  "openclaw_home": "/absolute/path/to/openclaw-home"
}
```

The required result shape is:

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": []
}
```

Wrappers may add transport metadata, but they must preserve the envelope fields and the result fields. Skill chaining is allowed only when the parent skill declares the internal call and preserves the same `openclaw_home`.

## Default Model Routing

Use [references/openrouter-defaults.md](references/openrouter-defaults.md) as the source of truth for default model routing.

Local-first on Mac:

1. `ollama/qwen3.5:9b-nvfp4`
2. `qwen3-coder:480b-cloud` when loaded for heavy code work
3. OpenRouter fallback stack

OpenRouter fallback stack:

| Tier | Model ID | Role |
|------|----------|------|
| A | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | Default agent brain |
| B | `openrouter/minimax/minimax-m2.5:free` | Coding fallback |
| C | `openrouter/deepseek/deepseek-v4-flash:free` | Fast triage |
| D | `openrouter/openai/gpt-oss-120b:free` | Reasoning and tool use |
| E | `openrouter/z-ai/glm-4.5-air:free` | Agentic backup |
| F | `openrouter/inclusionai/ling-2.6-flash:free` | Lightweight tasks |
| Z | `openrouter/openrouter/free` | Last-resort auto-router |

Gemini is specialized only and is not the default fallback. Reserve it for visual diff, screenshot comparison, whole-repo architecture mapping, stale-doc detection, or explicit second-opinion review.

## PT-Orama Recursive Spawn

OpenClaw deployment is recursive across three layers:

| Layer | Role | Responsibility |
|-------|------|----------------|
| L3 | `orama-system` | Owns these canonical skill definitions and routing policy. |
| L2 | Perpetua-Tools middleware | Receives agent-neutral skill envelopes, resolves `openclaw_home`, runs tools, and returns normalized results. |
| L1 | OpenClaw instance | Applies config changes, starts agents, routes messages, schedules jobs, and may spawn child OpenClaw instances. |

Standard L3 to L1 dispatch:

```text
orama-system
  -> Perpetua-Tools skill dispatcher
  -> openclaw-skills/{skill_id}
  -> target OpenClaw home
  -> files changed, stowed, restarted, verified
```

Nested OpenClaw recursion:

```text
parent OpenClaw agent
  -> emits universal skill envelope
  -> Perpetua-Tools resolves child openclaw_home
  -> child OpenClaw invokes the same canonical skill
  -> child may later repeat the same pattern for its own sub-instance
```

Recursive spawn constraints:

1. Every invocation must carry an explicit `openclaw_home`.
2. A nested call must use the same skill IDs listed in this master file.
3. A sub-agent must be wired to its parent's `allowAgents` list in `openclaw.json`.
4. The parent may delegate, but the skill remains authoritative for naming, file layout, stow, restart, and verification.
5. Results must bubble upward in the universal output format so L3, L2, and L1 can audit the same record.

## Naming Conventions Enforced

| Item | Convention | Example |
|------|------------|---------|
| Keychain service | `openclaw.<name>`, lowercase, hyphens | `openclaw.telegram-bot-token` |
| Environment variable | `OPENCLAW_<NAME>`, uppercase, underscores | `OPENCLAW_TELEGRAM_BOT_TOKEN` |
| Agent ID | lowercase, hyphens | `insurance-agent` |
| Script output | stdout = JSON only | `{"status": "ok", "result": "..."}` |
| Script logging | stderr only | `echo "Processing..." >&2` |

Every generated agent requires:

| File or Directory | Purpose |
|-------------------|---------|
| `SOUL.md` | Identity, personality, operating principles |
| `IDENTITY.md` | Name, role, model assignment |
| `USER.md` | Relationship context and user preferences |
| `AGENTS.md` | Sub-agent wiring and session startup sequence |
| `TOOLS.md` | Available tools and script documentation |
| `SECURITY.md` | Credential handling policy |
| `memory/` | Agent memory root |
| `memory/archives/` | Long-term memory archive location |
| `scripts/` | Agent-local scripts |
| `scripts/lib/` | Shared script libraries |

Every secret touches all three files:

| File | Purpose | Consequence if missing |
|------|---------|------------------------|
| `openclaw-secrets.sh` | Loaded by launchd at gateway startup | Gateway cannot read the secret |
| `openclaw-env.sh` | Sourced by shell for CLI commands | Terminal can raise `MissingEnvVarError` while gateway works |
| `secrets.sh` | Provisioning script for fresh machines | Disaster recovery fails silently |

## Operational Rules

1. Never freestyle OpenClaw configuration. Use the relevant skill for every configuration change.
2. Run `openclaw-status` before changes to understand current gateway, launchd, channel, agent, cron, and error state.
3. Run `openclaw-restart` after config changes. Do not use raw `launchctl kickstart` as the operational restart path.
4. Treat `~/.openclaw/cron/jobs.json` as transient. The gateway regenerates it on startup; never treat it as source of truth.
5. Never echo secrets to terminal, files, logs, prompts, result envelopes, or git history.
6. When creating a sub-agent, wire it to the parent's `allowAgents` list in `openclaw.json`.
7. Use `stow --no-folding` for all stow operations so the symlink structure is preserved.
8. After updating the source skill distribution, re-run stow if new skills were added.

## Quick Reference

| Command | When to Use |
|---------|-------------|
| `openclaw-new-agent` | Creating any new agent |
| `openclaw-add-channel` | Adding Telegram, Slack, or WhatsApp integration |
| `openclaw-add-cron` | Scheduling any recurring or one-shot job |
| `openclaw-dream-setup` | Setting up nightly memory distillation for an agent |
| `openclaw-add-script` | Creating a new deterministic shell script |
| `openclaw-add-secret` | Storing any API key or credential |
| `openclaw-status` | Diagnosing any problem; run this first |
| `openclaw-restart` | After any config change |
| `openclaw-stow` | After manual file edits only |

## Agent Compatibility Notes

| Agent | Discovery | Invocation |
|-------|-----------|------------|
| Claude | Skill tool or local skill folder scan | Load this master `SKILL.md`, then the selected subskill |
| Hermes | MCP or local markdown skill registry | Send universal JSON envelope to the skill runner |
| Gemini | `gemini-mcp-tool` wrapper | Invoke through MCP with the universal envelope |
| Codex | `ai-cli-mcp` or local skill path | Invoke selected skill with explicit `openclaw_home` |
| Cursor | `.cursor/rules/` mirror or linked skill docs | Rule triggers should call the same skill IDs |
| WindSurf | Workspace rules or MCP adapter | Resolve skill ID and execute through the protocol |
| Antigravity | Agent rules or MCP adapter | Dispatch envelope to Perpetua-Tools |
| OpenCode | Local command, MCP, or rules adapter | Use skill ID plus args exactly as declared |
| 8gent.dev | Agent registry or MCP adapter | Dispatch normalized envelope and preserve output shape |

If an agent cannot load markdown skills directly, it must use Perpetua-Tools or an equivalent wrapper that reads this folder and executes the same procedures.
