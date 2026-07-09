# WhatsApp QR Gateway Operations Runbook

Use this reference for operator-facing QR access, read-only health checks,
WhatsApp command patterns, and notification examples.

## Current Runtime Claim

Prior operator note: gateway was live on port `8555` under an OpenClaw process.
Treat that as volatile. Re-check before acting.

## Quick Start

### Access the QR Gateway

```bash
# Visit in browser to generate or view the QR code.
open http://localhost:8555/qr

# Or check JSON health status.
curl http://localhost:8555/health
```

### Authenticate via WhatsApp

- Scan the QR code from the gateway.
- Auth method: one-time token plus user identity.
- Session persistence: bearer token in the `Authorization` header.
- Never print bearer tokens or QR payloads in chat or logs.

### Send Commands via WhatsApp

Supported command shapes:

| Command | Purpose | Risk |
|---|---|---|
| `health` | Check PT, orama, and Portal health | read-only |
| `restart <service>` | Restart `pt`, `orama`, or `portal` | HITL required |
| `task <spec>` | Queue a task for processing | HITL required |
| `status <job-id>` | Check queued or running job status | read-only |

Example health message:

```text
Message: "health"
Response: "✅ All services UP: PT:8000 ✅ orama:8001 ✅ Portal:8002 ✅"
```

### Real-Time Notifications

Expected proactive WhatsApp notifications:

```text
Deployment started: <service> restarting...
Health check failed: <service> unreachable (tier fallback active)
Task completed: <job-id> — output: <snippet> [view full: <link>]
```

## Supported Message Formats

- Text commands: `health`, `restart orama`, `task <json-spec>`.
- Slash commands: `/health`, `/restart`, `/task`, `/status`.
- Voice transcription that falls back to text command parsing.
- Image OCR that extracts text and falls back to text request if parsing fails.

## Error Responses

| Condition | Expected response |
|---|---|
| Unrecognized command | `Sorry, I didn't understand. Try: health | restart <service> | task <spec> | status <id>` |
| Auth failure | `Authentication failed. Rescan QR code to reauthorize.` |
| Service timeout | `Service unavailable. Retrying via fallback tier (this may take up to 90s)...` |
| Queue full | `Command queued for later (job-id: <id>). Check status: /status <id>` |

## Usage Patterns

### Operational Monitoring

```text
Configure in the Portal dashboard:
Every 5min: "health"
Response: service status matrix
Alert on: any service DOWN -> escalate to paging path
```

### Emergency Restart

Restart is sensitive. Require HITL approval before sending the command.

```text
User sends via WhatsApp after approval:
"restart orama"
Response: "🔄 Restarting orama:8001... (estimated 30s)"
Notification: "✅ orama restarted successfully"
```

### Async Task Processing

Task submission is sensitive. Require HITL approval before sending the task.

```json
{"workflow": "audit", "scope": "full", "output": "report"}
```

Expected WhatsApp flow:

```text
Message: "task {\"workflow\": \"audit\", \"scope\": \"full\", \"output\": \"report\"}"
Response: "📋 Task queued (job-id: job_abc123). Estimated time: 5-10min"
Notification: "✅ Audit complete. Report: <link>"
```

## Operator Report Template

```text
STATUS: DONE / BLOCKED / NEEDS_APPROVAL
Action: <check|qr|health|restart|task|status>
Observed gateway: <up|down|unknown>
Command path: <read-only|HITL-required>
Evidence: <curl/ps/log check or user-provided observation>
Next safe action: <...>
```
