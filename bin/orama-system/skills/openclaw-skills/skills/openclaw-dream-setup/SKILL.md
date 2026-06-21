---
name: openclaw-dream-setup
description: Configure nightly dream-memory distillation with enforced token budgets, cron scheduling, and startup wiring.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-dream-setup/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-dream-setup/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-dream-setup/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Install a consistent nightly memory distillation pipeline for one agent. This skill creates the required memory docs and archive structure, schedules execution, and updates startup references. It enforces strict token budgets to preserve operational context for real tasks.

## When to Use

- Enabling long-term memory hygiene for an agent
- Rebuilding dream routine after migration
- Standardizing memory process across agents

## Inputs

- Required:
  - `agent_id`
  - `run_time` (cron-compatible local time)
- Optional:
  - `timezone` (defaults to system timezone)
  - `job_id` (defaults to `<agent_id>-dream-nightly`)

## Procedure

1. Validate agent path and create memory archives directory.

```bash
set -euo pipefail
agent_dir="agents/$agent_id"
[ -d "$agent_dir" ] || { echo "agent not found" >&2; exit 1; }
mkdir -p "$agent_dir/memory/archives"
```
1. Create `DREAM-ROUTINE.md` with fixed token budgets.

```bash
cat > "$agent_dir/DREAM-ROUTINE.md" <<'EOT'
# DREAM ROUTINE

- Daily distillation budget: 2500 tokens (hard cap)
- Rolling 3-day digest budget: 7500 tokens (hard cap)
- Never exceed caps; trim low-signal memory first.
EOT
```
1. Create `MEMORY.md` if missing.

```bash
[ -f "$agent_dir/MEMORY.md" ] || cat > "$agent_dir/MEMORY.md" <<'EOT'
# MEMORY

Curated long-term facts, preferences, and durable project decisions.
EOT
```
1. Add cron job in `openclaw.json` for dream routine.

```bash
job_id="${job_id:-$agent_id-dream-nightly}"
jq --arg id "$job_id" --arg aid "$agent_id" --arg rt "$run_time" '
  (.cron.jobs //= []) |
  .cron.jobs |= map(select(.id != $id)) + [{
    id:$id,
    agentId:$aid,
    schedule:{type:"cron",value:$rt},
    prompt:"Run DREAM-ROUTINE.md and update MEMORY.md from latest archives",
    isolated:true,
    enabled:true
  }]
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```
1. Add QMD index references in `openclaw.json`.

```bash
jq --arg aid "$agent_id" '
  (.agents.indexes //= {}) |
  (.agents.indexes[$aid] //= {}) |
  .agents.indexes[$aid].qmd = ["agents/"+$aid+"/MEMORY.md", "agents/"+$aid+"/memory/archives"]
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```
1. Update `AGENTS.md` startup sequence for memory preloads.

```bash
grep -q 'DREAM-ROUTINE.md' "$agent_dir/AGENTS.md" || cat >> "$agent_dir/AGENTS.md" <<'EOT'

## Session Startup Sequence
1. Read MEMORY.md
2. Check latest archive in memory/archives/
3. Respect DREAM-ROUTINE.md token caps
EOT
```
1. Deploy and verify.

```bash
rm -f ~/.openclaw/cron/jobs.json
stow --no-folding -t "$HOME" .
launchctl kickstart -k "gui/$(id -u)/com.openclaw.gateway"
sleep 5
```

## Output Contract

```json
{
  "status": "ok|error",
  "files_modified": ["agents/<agent_id>/DREAM-ROUTINE.md", "agents/<agent_id>/MEMORY.md", "agents/<agent_id>/AGENTS.md", "openclaw.json"],
  "follow_up_actions": ["openclaw-status", "validate-first-dream-run"]
}
```

## Naming Enforcement

- Dream job ID defaults to `<agent_id>-dream-nightly`.
- Agent ID must remain lowercase-hyphen style.
- Token budget values are fixed and must remain `2500` and `7500`.

## Gotchas

- Skipping budget enforcement causes memory retrieval to consume active context.
- Missing `memory/archives/` blocks rolling digest workflow.
- Omitting AGENTS startup steps leads to stale memory usage.

## See Also

- `../openclaw-add-cron/SKILL.md`
- `../openclaw-status/SKILL.md`
- `../openclaw-restart/SKILL.md`

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
