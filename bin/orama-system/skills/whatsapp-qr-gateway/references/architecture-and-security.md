# WhatsApp QR Gateway Architecture And Security

Use this reference for architecture, auth, routing, fallback, integration points,
implementation provenance, and security gates.

## Provenance Boundary

The WhatsApp gateway implementation is outside `orama-system`.

Operator-provided import chain:

```text
AlphaClaw feature/MacOS-post-install
  -> imported by Perpetua-Tools main
  -> consumed/referenced by orama-system skill documentation
```

Relevant external branch:

```text
https://github.com/diazMelgarejo/AlphaClaw/tree/feature/MacOS-post-install
```

This connector session could not verify the exact implementation file path by
repository search. Treat the branch/import chain above as operator-provided
provenance until re-verified against AlphaClaw and Perpetua-Tools. Do not edit
AlphaClaw directly from this skill; route implementation changes through
Perpetua-Tools as the controlling import surface.

## Components

| Component | Location | Port | Purpose |
|---|---|---:|---|
| QR Gateway | AlphaClaw/OpenClaw runtime surface, imported via Perpetua-Tools | 8555 | Auth QR generation and WhatsApp webhook receiver |
| Control Plane | orama-system | 8001 | Route commands to services |
| Tier Router | Perpetua-Tools | 8000 | Fallback routing across local/GPU/cloud tiers |
| Dashboard | Portal | 8002 | Real-time monitoring and WhatsApp integration |

Do not edit the AlphaClaw fork from this skill. Treat AlphaClaw/OpenClaw paths as
external implementation provenance unless the operator explicitly routes work
through Perpetua-Tools.

## Auth Flow

1. User scans QR code and receives user-bound bearer-token context.
2. WhatsApp message reaches the gateway webhook at `http://localhost:8555/webhook`.
3. Control Plane validates the bearer token against `ORAMA_CONTROL_PLANE_TOKEN`.
4. Command routes to PT, orama, or Portal according to the command type.
5. Response returns through WebSocket, SSE, or WhatsApp notification path.

## Command Processing Contract

```text
User WhatsApp Message
         ↓
Webhook receiver on gateway port 8555
         ↓
Auth validation with bearer token
         ↓
Command parser: health | restart | task | status
         ↓
Service route: PT -> orama -> Portal
         ↓
Tier-based execution: Ollama -> GLM -> OpenRouter
         ↓
Result aggregation
         ↓
WhatsApp response plus optional real-time notification
```

## Fallback Strategy

| Tier | Target | Budget | Fallback |
|---|---|---:|---|
| Tier 1 | local Ollama | 10s | Tier 2 |
| Tier 2 | Windows GPU / GLM | 10s | Tier 3 |
| Tier 3 | OpenRouter cloud | up to 90s | queue |
| Queue | async processing | job dependent | status tracking |

If all tiers fail, queue the command and return a job ID.

## Live Deployment Verification

Use read-only checks first:

```bash
# Check whether something is listening or running around the gateway port.
ps aux | grep 8555

# Check gateway health.
curl -s http://localhost:8555/health
```

Prior implementation path note, not proven by `orama-system` alone:

```text
AlphaClaw/lib/server/whatsapp-gateway.js
```

If that path is needed, verify it in AlphaClaw `feature/MacOS-post-install` and
then confirm how Perpetua-Tools `main` imports or vendors it.

## QR Generation Contract

- Type: standard QR, version 3 or higher when payload size requires it.
- Payload: bearer-token context, user ID, and service endpoints.
- Expiry: optional; prior MVP assumed persistent portal use.
- Regeneration endpoint: `POST http://localhost:8555/api/qr/refresh`.

Do not expose the QR payload or bearer token in logs, chat, screenshots, or review
artifacts.

## Integration Points

### Portal

- Sync WhatsApp command history.
- Visualize WhatsApp-triggered operations.
- Subscribe to real-time notifications via WebSocket.
- Regenerate QR code from dashboard UI.

### orama-system Control Plane

- Validate bearer tokens.
- Enforce token scopes.
- Log command audits.
- Bind user context to the command.

### Perpetua-Tools Tier Router

- Route command execution.
- Escalate through fallback tiers.
- Track cost per command.
- Enforce timeout budgets.
- Own the gateway import/update path before any AlphaClaw-sourced change reaches orama documentation.

## Security Gates

### Read-Only Actions

These may proceed after verification:

- `health`
- `status <job-id>`
- QR page availability check
- health endpoint check
- log inspection without token disclosure

### HITL Actions

These require explicit operator approval:

- `restart <service>`
- `task <spec>`
- scheduled commands
- QR refresh if it invalidates existing sessions
- notification delivery to external recipients
- any command with credentials, secrets, cost, or deployment impact

### Disallowed From This Skill

- Editing AlphaClaw/OpenClaw source directly.
- Printing bearer tokens or QR payloads.
- Running local kill/restart commands as a substitute for gateway contracts.
- Expanding to Slack/email integrations without a separate plan.

## Audit Note Template

```text
AUDIT: <yyyy-mm-ddThh:mm:ssZ> whatsapp-qr-gateway <action>
Approver: <operator>
Service: <pt|orama|portal|gateway|n/a>
Risk: <read-only|HITL|blocked>
Evidence: <health/status/log check>
Result: <observed result>
```
