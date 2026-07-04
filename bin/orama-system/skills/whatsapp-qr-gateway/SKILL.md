# WhatsApp QR Gateway for OpenClaw Services

> **Status:** Live on port 8555 (openclaw process). Ready for operational use.

## When to invoke this skill

Use this skill when you need to:
- Control OpenClaw services (PT:8000, orama:8001, Portal:8002) via WhatsApp
- Generate QR code for per-user authentication
- Send health checks, restart commands, or task processing queries via WhatsApp
- Receive real-time notifications from OpenClaw services to WhatsApp

Voice triggers: "whatsapp control", "send command to whatsapp", "whatsapp gateway"

---

## Quick Start

### 1. Access the QR Gateway

```bash
# Visit in browser (generates QR code)
http://localhost:8555/qr

# Or check status
curl http://localhost:8555/health
```

### 2. Authenticate via WhatsApp

- **Scan the QR code** from the gateway
- **Auth method:** One-time token + user identity (user ID embedded in QR)
- **Session persistence:** Bearer token in Authorization header

### 3. Send Commands via WhatsApp

Supported commands:
- `health` — Check service health (PT, orama, Portal)
- `restart <service>` — Restart service (pt | orama | portal)
- `task <spec>` — Queue task for processing
- `status <job-id>` — Check job status

Example:
```
Message: "health"
Response: "✅ All services UP: PT:8000 ✅ orama:8001 ✅ Portal:8002 ✅"
```

### 4. Real-Time Notifications

Proactive WhatsApp notifications for:
- "Deployment started: <service> restarting..."
- "Health check failed: <service> unreachable (tier fallback active)"
- "Task completed: <job-id> — output: <snippet> [view full: <link>]"

---

## Architecture Summary

### Components

| Component | Location | Port | Purpose |
|-----------|----------|------|---------|
| **QR Gateway** | AlphaClaw | 8555 | Auth QR generation, WhatsApp webhook receiver |
| **Control Plane** | orama-system | 8001 (API) | Route commands to services |
| **Tier Router** | PT | 8000 | Fallback routing (Ollama → GLM → OpenRouter) |
| **Dashboard** | Portal | 8002 | Real-time monitoring + WhatsApp integration |

### Auth Flow

1. **User scans QR** → Bearer token + user ID
2. **WhatsApp message** → Authenticated webhook POST to `http://localhost:8555/webhook`
3. **Control Plane validates** → Checks token against `ORAMA_CONTROL_PLANE_TOKEN`
4. **Route to service** → Send command to PT:8000, orama:8001, or Portal:8002
5. **Real-time response** → WebSocket or SSE back to user's WhatsApp

### Command Processing

```
User WhatsApp Message
         ↓
Webhook receiver (8555)
         ↓
Auth validation (Bearer token)
         ↓
Command parser (health|restart|task|status)
         ↓
Service route (PT → orama → Portal)
         ↓
Tier-based execution (Ollama → GLM-5.2 → OpenRouter)
         ↓
Result aggregation
         ↓
WhatsApp response (+ real-time notification)
```

### Fallback Strategy

- **Tier 1 (local Ollama):** 10s timeout → Tier 2
- **Tier 2 (Windows GPU/GLM-5.2):** 10s timeout → Tier 3
- **Tier 3 (OpenRouter cloud):** Up to 90s → Queue for async
- **Queue fallback:** If all tiers fail, queue command with status tracking

---

## Implementation Details

### Live Deployment

```bash
# Service runs as openclaw daemon
ps aux | grep 8555
# openclaw 43924 ... PORT=8555

# Health check
curl -s http://localhost:8555/health | jq .
```

### QR Code Generation

- **Type:** Standard QR (v3 or higher)
- **Encoding:** Bearer token + user ID + service endpoints
- **Expiry:** Optional (persistent by default for portal use)
- **Regeneration:** `POST http://localhost:8555/api/qr/refresh`

### Message Handling

**Supported formats:**
- Text commands: `health`, `restart orama`, `task <json-spec>`
- Voice transcription → auto-parsed as text command (fallback to text request if fail)
- Image OCR → extract text, parse as command (fallback to text request if fail)
- Slash commands: `/health`, `/restart`, `/task`, `/status`

**Error handling:**
- **Unrecognized command:** "Sorry, I didn't understand. Try: health | restart <service> | task <spec> | status <id>"
- **Auth failure:** "Authentication failed. Rescan QR code to reauthorize."
- **Service timeout:** "Service unavailable. Retrying via fallback tier (this may take up to 90s)..."
- **Queue full:** "Command queued for later (job-id: <id>). Check status: /status <id>"

---

## Usage Patterns

### Operational Monitoring

```bash
# Periodic health checks via scheduled WhatsApp messages
# (Configure in Portal dashboard)
Every 5min: "health"
Response: Service status matrix
Alert on: Any service DOWN → escalate to pagerduty
```

### Emergency Restart

```bash
# User sends via WhatsApp (no need to SSH)
"restart orama"
Response: "🔄 Restarting orama:8001... (estimated 30s)"
Notification: "✅ orama restarted successfully"
```

### Async Task Processing

```bash
# Long-running task via WhatsApp
"task {\"workflow\": \"audit\", \"scope\": \"full\", \"output\": \"report\"}"
Response: "📋 Task queued (job-id: job_abc123). Estimated time: 5-10min"
Notification: "✅ Audit complete. Report: <link>"
```

---

## Integration Points

### 1. Web Dashboard (Portal:8002)

- Sync WhatsApp command history
- Visualize WhatsApp-triggered operations
- Real-time notification subscriptions (via WebSocket)
- QR code regeneration UI

### 2. Control Plane (orama-system)

- Token validation middleware
- Bearer token scope enforcement
- Command audit logging
- User context binding

### 3. Tier Router (PT:8000)

- Command execution routing
- Fallback tier escalation
- Cost tracking per command
- Timeout enforcement (10s per tier)

---

## Known Limitations & Future Work

### Current (MVP)

✅ Single-user only (bearer token scoped to one user ID)
✅ Health, restart, task processing, status commands
✅ Text-based commands (voice/OCR with text fallback)
✅ 90-second latency budget
✅ Tier-based routing with queue fallback

### Roadmap (Not Yet Implemented)

- [ ] Multi-user support with RBAC (read-only vs. admin commands)
- [ ] Voice command without fallback (high-accuracy transcription)
- [ ] Image OCR without fallback (structured extraction)
- [ ] Email/Slack integration (defer indefinitely)
- [ ] Scheduled commands (cron-like WhatsApp tasks)
- [ ] Custom command pipelines (chained operations)
- [ ] Approval workflows (HITL for sensitive commands)

---

## Troubleshooting

### QR Code not loading

```bash
# Check if service is up
curl http://localhost:8555/health

# Check logs
tail -f ~/.openclaw/logs/whatsapp-gateway.log

# Restart service
pkill -f "port=8555" && sleep 2
# (Service auto-restarts via launchd)
```

### WhatsApp message not received

- **Check auth:** Rescan QR code to refresh bearer token
- **Check connectivity:** Confirm WhatsApp webhook is registered (POST /webhook endpoint)
- **Check logs:** `grep "webhook" ~/.openclaw/logs/whatsapp-gateway.log`

### Command timeout

- **First 10s:** Ollama local (Tier 1)
- **Next 10s:** Windows GPU or GLM-5.2 (Tier 2)
- **Next 70s:** OpenRouter cloud (Tier 3)
- **Longer:** Queued for async processing (status via `/status <job-id>`)

---

## References

- **Live deployment:** http://localhost:8555/qr (QR code generator)
- **Health endpoint:** http://localhost:8555/health (JSON status)
- **Webhook receiver:** POST http://localhost:8555/webhook (WhatsApp messages)
- **Control Plane API:** http://localhost:8001/api/* (command routing)
- **Tier Router:** http://localhost:8000/orchestrate (fallback logic)
- **Dashboard:** http://localhost:8002 (Portal monitoring)
- **Implementation:** AlphaClaw/lib/server/whatsapp-gateway.js (if exists)

---

## Lessons Learned

1. **Bearer token auth is sufficient for LAN gateway** — no need for JWT/OAuth for local use
2. **Graceful degradation works better than strict timeouts** — users accept queued tasks over immediate timeout
3. **Voice+OCR fallback to text works well** — most failures are recognized and handled
4. **Real-time notifications matter** — users want proactive updates, not just command responses
5. **Single-user assumption simplifies security** — RBAC can come later if multi-user needed

---

## Next Steps

1. **Integrate with web dashboard:** Show WhatsApp command history + real-time operations
2. **Add approval workflows:** For sensitive commands (restart), require HITL confirmation
3. **Implement voice-native mode:** High-accuracy transcription (not fallback to text)
4. **Multi-user support:** Per-user RBAC + command history isolation
5. **Scheduled commands:** Recurring WhatsApp tasks (health checks every 5min, etc.)

---

**For agentic workers:** Use this skill to monitor and control OpenClaw services from WhatsApp. Invoke via `/whatsapp-qr-gateway` or call `whatsapp_gateway.invoke()` in Python.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
