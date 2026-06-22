---
name: openclaw-status
description: Run a full OpenClaw health audit across gateway, launchd, channels, agents, cron, and recent errors.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-status/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-status/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-status/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Provide a one-command operational snapshot before changes or during incidents. This skill checks control-plane and channel connectivity together with scheduler health signals. It returns a compact machine-readable summary with follow-up actions.

## When to Use

- First step in troubleshooting any OpenClaw issue
- Post-change verification after restart or stow
- Routine health checks in operational workflows

## Inputs

- Required: none
- Optional:
  - `lookback_minutes` (default `15`)
  - `health_url` (default `http://127.0.0.1:7331/health`)
  - `include_log_excerpt` (`true|false`, default `true`)

## Procedure

1. Set defaults.

```bash
set -euo pipefail
lookback_minutes="${lookback_minutes:-15}"
health_url="${health_url:-http://127.0.0.1:7331/health}"
```
1. Probe gateway health endpoint.

```bash
gateway_json="$(curl -fsS "$health_url" || true)"
```
1. Check launchd service status.

```bash
launchctl print "gui/$(id -u)/com.openclaw.gateway" >/tmp/openclaw-launchd.txt 2>&1 || true
```
1. Check channel indicators (Telegram/Slack/WhatsApp) from logs.

```bash
log show --style syslog --last "${lookback_minutes}m" --predicate 'eventMessage CONTAINS[c] "telegram" OR eventMessage CONTAINS[c] "slack" OR eventMessage CONTAINS[c] "whatsapp"' > /tmp/openclaw-channels.log || true
```
1. Check configured agent count.

```bash
agent_count="$(jq '.agents.list | length' openclaw.json 2>/dev/null || echo 0)"
```
1. Check cron run/error signals.

```bash
log show --style syslog --last "${lookback_minutes}m" --predicate 'eventMessage CONTAINS[c] "cron" OR eventMessage CONTAINS[c] "scheduler" OR eventMessage CONTAINS[c] "error"' > /tmp/openclaw-cron.log || true
```
1. Emit JSON status summary.

```bash
jq -n --arg gateway "$gateway_json" --arg launchd "$(tail -n 20 /tmp/openclaw-launchd.txt | tr '\n' ' ')" --argjson agents "$agent_count" '{status:"ok",gateway:$gateway,launchd:$launchd,agent_count:$agents}'
```
1. Print actionable tail snippets for operators.

```bash
tail -n 40 /tmp/openclaw-channels.log || true
tail -n 40 /tmp/openclaw-cron.log || true
```

## Output Contract

```json
{
  "status": "ok|degraded|error",
  "files_modified": [],
  "follow_up_actions": ["openclaw-restart", "openclaw-add-secret", "openclaw-add-channel"]
}
```

## Naming Enforcement

- Service identifier must remain `com.openclaw.gateway` for launchd checks.
- Channel names are fixed probes: `telegram`, `slack`, `whatsapp`.
- Health endpoint path must remain `/health` unless the deployment explicitly overrides it.

## Gotchas

- Health endpoint may pass while one channel is disconnected; always inspect channel logs.
- `jobs.json` is not a reliable source of intended cron config.
- Log retention settings can hide older failures; increase lookback when needed.
- Empty channel logs can indicate either no traffic or failed initialization; correlate with launchd output.
- If `jq` is unavailable, JSON summary generation must be replaced before automation use.

## See Also

- `../openclaw-restart/SKILL.md`
- `../openclaw-stow/SKILL.md`
- `../openclaw-add-channel/SKILL.md`

## Notes

- Use this skill before any mutation to establish a baseline.
- Store output JSON with incident tickets to track before/after state.

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
