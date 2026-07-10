---
name: openclaw-new-agent
description: Create a fully wired OpenClaw agent with required directives, directories, and openclaw.json registration.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Create a new OpenClaw agent consistently without configuration drift. This skill enforces required files, directories, and `openclaw.json` updates in one pass. It also handles standalone versus sub-agent wiring so parent-child execution is explicit.

## When to Use

- Creating any new OpenClaw agent profile
- Splitting responsibilities into specialized sub-agents
- Standardizing agent scaffolding across contributors

## Inputs

- Required:
  - `agent_id` (lowercase, hyphens)
  - `display_name` (human-readable)
  - `mode` (`standalone` or `sub-agent`)
- Optional:
  - `parent_agent_id` (required when `mode=sub-agent`)
  - `model_primary` (defaults to `ollama/qwen3.5:9b-nvfp4`)
  - `channel` (`telegram|slack|whatsapp|none`)

## Procedure

**Live-verified 2026-07-11 against openclaw 2026.7.1-beta.2** — the
jq-hand-edit procedure this skill documented previously is DEPRECATED. Do
NOT hand-edit `~/.openclaw/openclaw.json` for agent creation: the live
schema (`agentDir`, `workspace`, `model` as a plain string, `tools.profile`)
does not match a `model:{primary:...}` shape a naive jq template might
produce, and this repo already has a hard-learned invariant against
hand-editing `openclaw.json` for exactly this reason (see the
`openclaw cron add` lesson in `docs/how-to/openclaw-hermes-cross-harness-wiring.md`
§11 — an invalid shape passes `jq` cleanly but fails `openclaw config
validate` and can silently break the live gateway). A real CLI command
already exists and does this correctly:

1. Validate inputs.

```bash
set -euo pipefail
printf '%s' "$agent_id" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'
```
2. Create the agent via the CLI (writes `openclaw.json` correctly, scaffolds
   the workspace directory, and auto-generates most of the six directive
   files in one pass — verified: `openclaw agents add` already creates
   `SOUL.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, and a template `IDENTITY.md`;
   only `SECURITY.md` and a filled-in `IDENTITY.md` typically need writing
   by hand afterward).

```bash
openclaw agents add "$agent_id" \
  --model "${model_primary:-ollama/qwen3.5:9b-nvfp4}" \
  --workspace "$HOME/.openclaw/agents/$agent_id" \
  --non-interactive --json
```
3. Fill in `IDENTITY.md` with real content (the CLI's auto-generated one is
   a blank "who am I?" template, not a working default — see
   `~/.openclaw/agents/codex-agent/IDENTITY.md` for the concrete pattern to
   match: Name, Role, Primary model, Reasoning, Invocation, Scope).
4. Add `SECURITY.md` if the CLI didn't create one (copy `codex-agent`'s as
   a template — Credentials / Change Control / Data Handling sections).
5. If `mode=sub-agent`, wire parent allow-list/binding via the CLI, not jq:

```bash
if [ "$mode" = "sub-agent" ]; then
  openclaw agents bind "$parent_agent_id" --allow "$agent_id"
fi
```
   (Verify the exact `agents bind` flag shape with `openclaw agents bind --help`
   before relying on `--allow` — not independently re-verified in this pass;
   the `agents add`/`agents list` commands above ARE live-verified.)
6. If channel requested, delegate to `openclaw-add-channel` after create.

```bash
if [ "${channel:-none}" != "none" ]; then
  echo "Run: openclaw-add-channel for $channel and bind to $agent_id" >&2
fi
```
7. **Auth is per-agent, not per-provider.** `openclaw models list` showing a
   provider as `configured` in the catalog does NOT mean any given agent can
   use it — each agent has an ISOLATED auth store
   (`~/.openclaw/agents/<id>/agent/openclaw-agent.sqlite`); check the
   `Auth` column specifically, or run
   `openclaw models auth list --provider <id>` scoped correctly, before
   assuming a new agent is ready to call. If the provider needs an
   interactive OAuth flow (`openclaw models auth login --provider <id>`,
   or `--device-code` if supported), it requires the user's own terminal/
   browser — cannot be completed headlessly by an agent. Verified 2026-07-11:
   a freshly created agent bound to `google-antigravity/*` had zero
   antigravity credentials in its own auth store even though the model
   catalog listed antigravity as `configured`.

## Output Contract

```json
{
  "status": "ok|error",
  "files_modified": ["openclaw.json", "agents/<agent_id>/SOUL.md", "agents/<agent_id>/IDENTITY.md", "agents/<agent_id>/USER.md", "agents/<agent_id>/AGENTS.md", "agents/<agent_id>/TOOLS.md", "agents/<agent_id>/SECURITY.md"],
  "follow_up_actions": ["optional-next-step"]
}
```

## Naming Enforcement

- `agent_id` must be lowercase and hyphenated: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Sub-agent IDs must still follow the same format as standalone agents
- Keep file names exact: `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, `SECURITY.md`

## Gotchas

- Manual agent creation often misses one or more of the six directive files.
  `openclaw agents add` auto-creates SOUL/USER/AGENTS/TOOLS.md and a blank
  IDENTITY.md template — SECURITY.md and a filled-in IDENTITY.md still need
  writing by hand (verified 2026-07-11, see § Procedure above).
- Sub-agents without parent `allowAgents` wiring will not be callable.
- If `jq` is missing, JSON edits become unsafe — moot now that `openclaw
  agents add`/`bind` exist; prefer the CLI over jq entirely (see § Procedure).
- **`openclaw agent --session-key agent:<id>:<key>` requires `<id>` to be a
  REAL, already-registered agent** — verified live: `--session-key
  agent:review:...` failed with `Agent "review" no longer exists in
  configuration` because no agent named "review" was ever created. To make
  a one-off ad-hoc model call without a persistent agent, borrow an
  EXISTING agent's session slot (e.g. `agent:main:<ephemeral-key>`) with
  `--model` as the override — but note its auth store may not have the
  target provider's credentials either (see next gotcha). For anything
  recurring, create a real persistent agent instead (§ Procedure) —
  ephemeral session-key borrowing is a one-shot workaround, not a pattern.
- **Auth-provider preference order, when a provider supports both web OAuth
  and an API key: ALWAYS prefer web/OAuth login
  (`openclaw models auth login --provider <id>`) over API-key auth.** An
  API key is backup/fallback only — never set one up preferentially or skip
  the interactive login step just because a key is available (user-stated
  policy, 2026-07-11, in the context of `google-antigravity`/Gemini access
  where a Gemini API key exists as a fallback path).

## See Also

- `../openclaw-add-channel/SKILL.md`
- `../openclaw-restart/SKILL.md`
- `../openclaw-status/SKILL.md`

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
