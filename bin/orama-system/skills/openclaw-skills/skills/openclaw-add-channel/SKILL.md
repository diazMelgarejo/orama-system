---
name: openclaw-add-channel
description: Add Telegram, Slack, or WhatsApp channel using the full secret, config, stow, restart, and verification pipeline.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-add-channel/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-add-channel/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-add-channel/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Attach a messaging channel to OpenClaw safely and repeatably. This skill enforces the full seven-step secret propagation pipeline across runtime, shell, and recovery scripts. It then deploys and verifies connectivity so partial channel setup is avoided.

## When to Use

- Adding a new Telegram, Slack, or WhatsApp integration
- Repairing a channel configured in `openclaw.json` but missing credentials
- Standardizing channel onboarding across environments

## Inputs

- Required:
  - `channel_type` (`telegram|slack|whatsapp`)
  - `agent_id` (target agent binding)
- Optional:
  - `bot_token` (telegram/slack)
  - `app_token` (slack socket mode)
  - `phone_allowlist` (whatsapp)

## Procedure

1. Save credentials in macOS Keychain.

```bash
set -euo pipefail
case "$channel_type" in
  telegram)
    security add-generic-password -a "$USER" -s openclaw.telegram-bot-token -w "$bot_token" -U ;;
  slack)
    security add-generic-password -a "$USER" -s openclaw.slack-bot-token -w "$bot_token" -U
    security add-generic-password -a "$USER" -s openclaw.slack-app-token -w "$app_token" -U ;;
  whatsapp)
    security add-generic-password -a "$USER" -s openclaw.whatsapp-session-secret -w "${bot_token:-placeholder}" -U ;;
  *) echo "unsupported channel_type" >&2; exit 1 ;;
esac
```
1. Update `openclaw-secrets.sh` for launchd/gateway startup.

```bash
# Add export lines that read from keychain service names above.
```
1. Update `openclaw-env.sh` for CLI/shell sessions.

```bash
# Mirror launchd exports so terminal commands do not fail with MissingEnvVarError.
```
1. Update provisioning `secrets.sh` for disaster recovery.

```bash
# Ensure new keychain service is recreated on fresh machines.
```
1. Add channel config and agent binding in `openclaw.json`.

```bash
jq --arg c "$channel_type" --arg a "$agent_id" '
  (.channels //= {}) |
  (.channels[$c] //= {enabled:true}) |
  (.agents.bindings //= {}) |
  (.agents.bindings[$a] //= {}) |
  (.agents.bindings[$a].channels //= []) |
  if (.agents.bindings[$a].channels | index($c)) then .
  else .agents.bindings[$a].channels += [$c] end
' openclaw.json > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json
```
1. Deploy and restart.

```bash
rm -f ~/.openclaw/cron/jobs.json
stow --no-folding -t "$HOME" .
launchctl kickstart -k "gui/$(id -u)/com.openclaw.gateway"
sleep 5
```
1. Verify channel connectivity in logs.

```bash
log show --style syslog --last 5m --predicate 'eventMessage CONTAINS[c] "telegram" OR eventMessage CONTAINS[c] "slack" OR eventMessage CONTAINS[c] "whatsapp"' | tail -n 80
```

## Output Contract

```json
{
  "status": "ok|error",
  "files_modified": ["openclaw-secrets.sh", "openclaw-env.sh", "secrets.sh", "openclaw.json"],
  "follow_up_actions": ["openclaw-status", "channel-smoke-test"]
}
```

## Naming Enforcement

- Keychain services must be `openclaw.<name>` in lowercase-hyphen form.
- Environment variables must be `OPENCLAW_<NAME>` uppercase underscore form.
- Channel IDs in JSON must be exactly `telegram`, `slack`, or `whatsapp`.

## Gotchas

- Missing `openclaw-env.sh` update causes terminal `MissingEnvVarError` even if gateway works.
- Missing `secrets.sh` update breaks recovery on a fresh machine.
- Slack requires both bot token and app token for socket mode.

## See Also

- `../openclaw-add-secret/SKILL.md`
- `../openclaw-stow/SKILL.md`
- `../openclaw-restart/SKILL.md`

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
