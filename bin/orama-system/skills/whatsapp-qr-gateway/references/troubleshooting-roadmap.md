# WhatsApp QR Gateway Troubleshooting And Roadmap

Use this reference for troubleshooting, current limitations, roadmap items,
lessons, and next-step planning.

## Known Limitations

Current MVP assumptions from the original skill:

- Single-user bearer-token flow scoped to one user ID.
- Health, restart, task processing, and status commands exist as command shapes.
- Text commands are primary.
- Voice and OCR fall back to text parsing.
- 90-second latency budget before async queue fallback.
- Tier-based routing with queue fallback.

Treat these as runtime claims. Re-verify before depending on them for delivery or
incident response.

## Roadmap Items

Not yet implemented unless separately verified:

- Multi-user support with RBAC: read-only vs. admin commands.
- Voice-native command mode without text fallback.
- Image OCR without fallback, with structured extraction.
- Scheduled commands, such as cron-like WhatsApp health tasks.
- Custom command pipelines with chained operations.
- HITL approval workflows for sensitive commands.
- Email/Slack integration remains deferred unless a new plan says otherwise.

## Troubleshooting

### QR Code Not Loading

Use read-only checks:

```bash
curl http://localhost:8555/health

tail -f ~/.openclaw/logs/whatsapp-gateway.log
```

Do not run local kill/restart commands without explicit operator approval. The
old all-in-one skill suggested a direct `pkill` restart path; this modularized
version treats local process restart as HITL-gated.

### WhatsApp Message Not Received

Check:

- Auth: rescan QR code if bearer context expired or was revoked.
- Connectivity: confirm the WhatsApp webhook points at the gateway endpoint.
- Logs: inspect webhook events without exposing secrets.

```bash
grep "webhook" ~/.openclaw/logs/whatsapp-gateway.log
```

### Command Timeout

Expected timeout ladder:

| Window | Expected path |
|---:|---|
| first 10s | local Ollama tier |
| next 10s | Windows GPU / GLM tier |
| next 70s | OpenRouter cloud tier |
| longer | queued async processing, check `/status <job-id>` |

If the task was queued, report the job ID and status-check command.

## Local Reference Endpoints

These endpoints are examples until verified in the current runtime:

| Surface | Endpoint |
|---|---|
| QR generator | `http://localhost:8555/qr` |
| Health endpoint | `http://localhost:8555/health` |
| Webhook receiver | `POST http://localhost:8555/webhook` |
| Control Plane API | `http://localhost:8001/api/*` |
| Tier Router | `http://localhost:8000/orchestrate` |
| Dashboard | `http://localhost:8002` |

Implementation path to verify through the controlling repo if needed:

```text
AlphaClaw/lib/server/whatsapp-gateway.js
```

## Lessons Learned

1. Bearer-token auth can be sufficient for a local single-user LAN gateway when
   tokens are protected and scope is narrow.
2. Graceful degradation beats hard failure; queued tasks are often better than
   immediate timeout.
3. Voice/OCR fallback to text keeps the command surface usable while advanced
   parsing matures.
4. Real-time notifications matter because operators want proactive updates.
5. Single-user assumptions simplify the MVP, but RBAC is required before
   multi-user or delegated administration.

## Next Steps

1. Integrate Portal command history and real-time operation display.
2. Add HITL approvals for restart and other sensitive commands.
3. Implement voice-native mode only after text fallback remains reliable.
4. Add multi-user support with per-user RBAC and command history isolation.
5. Add scheduled commands only after audit and approval flows exist.

## Re-Verification Checklist

```bash
# Confirm skill files.
find bin/orama-system/skills/whatsapp-qr-gateway -maxdepth 3 -type f | sort

# Confirm gateway health if runtime is available.
curl -s http://localhost:8555/health

# Inspect gateway logs without printing secrets.
grep "webhook\|health\|error" ~/.openclaw/logs/whatsapp-gateway.log | tail -40
```

## Agentic Worker Note

Invoke this skill as `/whatsapp-qr-gateway` for guided operation. If a Python
helper such as `whatsapp_gateway.invoke()` exists, verify its location and API
before using it; do not assume the helper exists from this reference alone.
