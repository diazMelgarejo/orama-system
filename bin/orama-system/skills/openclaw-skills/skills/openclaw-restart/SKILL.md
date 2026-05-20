---
name: openclaw-restart
description: Perform the safe five-step OpenClaw gateway restart with cron conflict cleanup and channel verification.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
---

## Purpose
Restart OpenClaw using the canonical sequence rather than raw `launchctl`. This prevents cron symlink conflicts and verifies runtime channel recovery after startup. Use this as the default restart operation after config changes.

## When to Use
- After editing `openclaw.json`, secrets, or channel configs
- After stow deploys to ensure runtime picks up changes
- During incident recovery when service state is stale

## Inputs
- Required: none
- Optional:
  - `wait_seconds` (default `5`)
  - `health_url` (default `http://127.0.0.1:7331/health`)

## Procedure
1. Remove transient cron state file.
```bash
set -euo pipefail
rm -f ~/.openclaw/cron/jobs.json
```
2. Re-apply symlinks with GNU stow.
```bash
stow --no-folding -t "$HOME" .
```
3. Kickstart launchd service.
```bash
launchctl kickstart -k "gui/$(id -u)/com.openclaw.gateway"
```
4. Wait for initialization.
```bash
sleep "${wait_seconds:-5}"
```
5. Verify channel reconnect and service health.
```bash
curl -fsS "${health_url:-http://127.0.0.1:7331/health}" >/dev/null
log show --style syslog --last 5m --predicate 'eventMessage CONTAINS[c] "telegram" OR eventMessage CONTAINS[c] "slack" OR eventMessage CONTAINS[c] "whatsapp"' | tail -n 100
```
6. Verify launchd state transitioned out of crash-loop mode.
```bash
launchctl print "gui/$(id -u)/com.openclaw.gateway" | tail -n 40
```
7. Emit summary JSON for callers.
```bash
jq -n '{status:"ok", step:"restart-complete"}'
```

## Output Contract
```json
{
  "status": "ok|error",
  "files_modified": [],
  "follow_up_actions": ["openclaw-status"]
}
```

## Naming Enforcement
- Launchd label is fixed: `com.openclaw.gateway`.
- Always use `stow --no-folding` before restart.
- Cron transient cleanup path is fixed: `~/.openclaw/cron/jobs.json`.

## Gotchas
- Running `launchctl kickstart` alone can leave broken cron symlinks unresolved.
- Skipping wait causes false-negative verification checks.
- Channel reconnection can lag if credentials are missing or mismatched.
- A healthy process without channel log events can still indicate partial startup failure.
- If the service label differs in local overrides, update command labels consistently in all restart probes.

## See Also
- `../openclaw-stow/SKILL.md`
- `../openclaw-status/SKILL.md`
- `../openclaw-add-channel/SKILL.md`

## Notes
- Use this sequence after any config mutation, especially secrets or channel bindings.
- Avoid parallel restarts from multiple terminals to prevent noisy diagnosis.
- If health probe fails, run `openclaw-status` immediately to capture short-lived startup logs.
