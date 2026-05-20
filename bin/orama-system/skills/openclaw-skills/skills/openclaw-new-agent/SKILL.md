---
name: openclaw-new-agent
description: Create a fully wired OpenClaw agent with required directives, directories, and openclaw.json registration.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
---

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
1. Validate inputs and repo context.
```bash
set -euo pipefail
[ -f openclaw.json ] || { echo "openclaw.json not found" >&2; exit 1; }
printf '%s' "$agent_id" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'
[ "$mode" = "standalone" ] || [ "$mode" = "sub-agent" ]
if [ "$mode" = "sub-agent" ]; then [ -n "${parent_agent_id:-}" ]; fi
```
2. Create required directory tree.
```bash
mkdir -p "agents/$agent_id/memory/archives" "agents/$agent_id/scripts/lib"
```
3. Create six directive files if missing.
```bash
for f in SOUL.md IDENTITY.md USER.md AGENTS.md TOOLS.md SECURITY.md; do
  path="agents/$agent_id/$f"
  [ -f "$path" ] || cat > "$path" <<EOT
# ${f%.md}

## Pending
Populate this file for agent: $agent_id
EOT
done
```
4. Set identity and default model in `IDENTITY.md`.
```bash
cat > "agents/$agent_id/IDENTITY.md" <<EOT
# IDENTITY

- Agent ID: $agent_id
- Display Name: $display_name
- Primary Model: ${model_primary:-ollama/qwen3.5:9b-nvfp4}
EOT
```
5. Add agent entry in `openclaw.json` under `agents.list`.
```bash
jq --arg id "$agent_id" --arg name "$display_name" --arg model "${model_primary:-ollama/qwen3.5:9b-nvfp4}" '
  .agents.list = (.agents.list // []) |
  if (.agents.list[]?.id == $id) then .
  else .agents.list += [{id:$id,name:$name,model:{primary:$model}}] end
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```
6. If `mode=sub-agent`, wire parent allow-list/binding.
```bash
if [ "$mode" = "sub-agent" ]; then
  jq --arg parent "$parent_agent_id" --arg child "$agent_id" '
    (.agents.bindings //= {}) |
    (.agents.bindings[$parent] //= {}) |
    (.agents.bindings[$parent].allowAgents //= []) |
    if (.agents.bindings[$parent].allowAgents | index($child)) then .
    else .agents.bindings[$parent].allowAgents += [$child] end
  ' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
fi
```
7. If channel requested, delegate to `openclaw-add-channel` after create.
```bash
if [ "${channel:-none}" != "none" ]; then
  echo "Run: openclaw-add-channel for $channel and bind to $agent_id" >&2
fi
```

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
- Sub-agents without parent `allowAgents` wiring will not be callable.
- If `jq` is missing, JSON edits become unsafe; install `jq` before running.

## See Also
- `../openclaw-add-channel/SKILL.md`
- `../openclaw-restart/SKILL.md`
- `../openclaw-status/SKILL.md`

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
