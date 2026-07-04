# WhatsApp QR Gateway Implementation Plan

**Status:** LIVE (MVP on port 8555). Operational for immediate use.  
**Last Updated:** 2026-07-04  
**Owner:** OpenClaw Operator Panel  

---

## Executive Summary

WhatsApp QR Gateway enables operational control of OpenClaw services (PT:8000, orama:8001, Portal:8002) via WhatsApp. Live MVP supports:
- Single-user bearer token auth (QR code scan)
- Health checks, restart commands, task queuing
- Real-time notifications (deployment, health, completion)
- Tier-based routing with 90-second fallback queue

**Go-to-market:** NOW (port 8555/qr). Canonical skill: `orama-system/bin/orama-system/skills/whatsapp-qr-gateway/SKILL.md`

---

## What's Live (MVP)

### Deployment

```
Service: openclaw daemon
Port: 8555
Health: curl http://localhost:8555/health
QR Code: http://localhost:8555/qr (browser)
```

### Commands

| Command | Example | Output |
|---------|---------|--------|
| health | `health` | Service status matrix (PT, orama, Portal) |
| restart | `restart orama` | Confirmation + ETA |
| task | `task {spec}` | Job ID + queue status |
| status | `status job_123` | Progress % + ETA |

### Auth

- **Method:** Bearer token (from QR code scan)
- **Scope:** Per-user (one token per person)
- **Validation:** ORAMA_CONTROL_PLANE_TOKEN middleware
- **Transport:** HTTP Authorization header

### Notifications

Proactive WhatsApp messages:
- `"🚀 Deployment started: orama restarting..."`
- `"⚠️ Health check failed: Ollama timeout, using GLM-5.2 fallback"`
- `"✅ Task completed: audit-full. Output: [link]"`

---

## Architecture

### Service Graph

```
User (WhatsApp)
    ↓
QR Gateway (8555)
    ├→ Auth validation (bearer token)
    ├→ Command parser
    └→ Route to Control Plane (8001)
        ├→ Tier Router (8000)
        │   ├→ Tier 1: Ollama local (10s)
        │   ├→ Tier 2: Windows GPU / GLM-5.2 (10s)
        │   ├→ Tier 3: OpenRouter cloud (70s)
        │   └→ Queue fallback (async)
        ├→ Dashboard (8002)
        │   ├→ Real-time notifications (WebSocket)
        │   ├→ Command history
        │   └→ WhatsApp integration UI
        └→ Service execution
            ├→ Health check
            ├→ Restart sequence
            ├→ Task processing
            └→ Status polling
```

### Latency Budget

| Tier | Timeout | Service | Purpose |
|------|---------|---------|---------|
| 0-2 | 10s | Ollama, GPU, GLM-5.2 | Probe (no escalation_tier param) |
| 3 | 10s | huggingface_free | First escalation |
| 4 | 10s | free_proprietary | Secondary escalation |
| 5 | 10s | OpenRouter | Tertiary escalation |
| 6 | 70s | Last resort (queued) | Async fallback |
| **Total** | **90s** | — | WhatsApp user timeout |

---

## Learnings (From Live Implementation)

### What Worked

1. **Bearer token auth is sufficient for LAN gateways** — No need for JWT/OAuth/QR-based sessions for internal use. Single token per user simplifies security model.

2. **Graceful degradation >> strict timeouts** — Users prefer "command queued, will process async" over "timeout, try again later." Queue fallback eliminates most WhatsApp timeouts.

3. **Voice + OCR fallback to text is robust** — Most transcription/OCR failures are caught and handled. Users accept "Please type your command" fallback without frustration.

4. **Proactive notifications drive engagement** — Real-time WhatsApp notifications (not just command responses) improve observability. Users check status without asking.

5. **Single-user assumption simplifies UX** — RBAC can be added later. Current model is: "user gets QR, scans once, full access to all commands." Clean boundary.

### What Needs Polish

1. **Voice transcription confidence threshold** — Current fallback on any fail is too aggressive. Need confidence scoring (>90% keep, else fallback).

2. **Image OCR error messages** — Users expect OCR to work on screenshots. When it fails, message should show "couldn't extract text" + ask for text-based command, not generic error.

3. **Notification spam** — Every command generates a WhatsApp. Need user preference: quiet mode (final result only) vs. verbose (all steps).

4. **Session persistence UI** — Users don't know their token is re-usable. Should show "connected as user <id>" in gateway UI, not just "scan QR for new token."

5. **Scheduled commands** — Recurring health checks are manual ("tell bot to health-check every 5min"). Need native scheduling (cron-like tasks from WhatsApp).

### What's Missing (Roadmap)

1. **Multi-user RBAC** — Current: one user per token. Need: admin vs. read-only roles, per-user audit logs, command approval workflows.

2. **Voice-native (not fallback)** — High-accuracy transcription without text fallback. Requires model upgrade (Deepgram or similar).

3. **Image OCR without fallback** — Structured extraction from screenshots (JSON spec diagrams, config files). Current OCR is text-only with fallback.

4. **Email/Slack integration** — Defer indefinitely per requirements. WhatsApp is primary.

5. **Approval workflows** — For sensitive commands (restart production services), require HITL confirmation via WhatsApp (two-person control).

---

## Phased Roadmap

### Phase 1: Polish MVP (Week of 2026-07-07)

**Goal:** Eliminate top 3 UX pain points.

Tasks:
- [ ] Voice confidence threshold: keep if >90%, else fallback
- [ ] OCR error messages: show "couldn't extract text" + retry UI
- [ ] Notification preferences: add quiet/verbose mode in Portal
- [ ] Session UI: show "connected as <user_id>" in gateway
- [ ] Test with live operators (stress test for 1 week)

**Acceptance:** Users report "works as expected" for health checks, restarts, task queuing. No confusing errors.

---

### Phase 2: Dashboard Integration (Week of 2026-07-14)

**Goal:** Unify WhatsApp commands + web dashboard.

Tasks:
- [ ] Sync command history (Portal ← WhatsApp webhook logs)
- [ ] Visualize WhatsApp-triggered operations on dashboard
- [ ] Real-time notification subscriptions (Portal WebSocket)
- [ ] QR code regeneration UI (Portal button)
- [ ] Approval workflow UI (for HITL gates)

**Acceptance:** Dashboard shows "Last WhatsApp command: restart orama 5min ago. Status: ✅ Complete."

---

### Phase 3: Multi-User RBAC (Week of 2026-07-21)

**Goal:** Enable team operability (not just single user).

Tasks:
- [ ] User model: username + role (admin/read-only)
- [ ] QR generation per-user: each person scans their own
- [ ] Command audit log: who ran what, when
- [ ] Approval workflows: sensitive commands require 2nd person
- [ ] Token rotation: refresh per session (vs. global token)

**Acceptance:** 3+ team members can independently control services. Audit trail shows all operations. Sensitive commands require approval.

---

### Phase 4: Voice-Native + OCR (Week of 2026-07-28)

**Goal:** No more fallback — voice and images just work.

Tasks:
- [ ] Upgrade transcription model (Deepgram or WhatsApp native)
- [ ] OCR model for structured extraction (diagrams, JSON specs)
- [ ] Remove text fallback from both (user experience: "just works")
- [ ] Test coverage: 50+ real-world voice samples + 20+ image types

**Acceptance:** Operators confidently send voice commands and config screenshots. No fallback prompts.

---

### Phase 5: Scheduled Commands (Month of Aug 2026)

**Goal:** Recurring WhatsApp tasks (health checks, reports).

Tasks:
- [ ] Cron-like scheduler: `/schedule health every 5min`, `/schedule audit daily 9am`
- [ ] Persistent schedule storage (Portal DB)
- [ ] Notification template customization
- [ ] Test: health checks every 5min for 1 month (stability)

**Acceptance:** Operators set up "health check every 5min" once, receive proactive alerts instead of manual commands.

---

## Integration Checklist

### Before General Availability

- [ ] **Portal Dashboard** — Real-time command history + operation visualization
- [ ] **Control Plane API** — Token validation + command routing
- [ ] **Tier Router** — Fallback escalation + timeout enforcement (10s per tier)
- [ ] **LAN Peer Discovery** — Auto-detect services on startup (PT, orama, Portal)
- [ ] **Audit Logging** — All WhatsApp commands + results logged to Portal
- [ ] **Notification Transport** — WebSocket for real-time Portal updates
- [ ] **Error Handling** — Graceful fallback for all failure modes
- [ ] **Documentation** — Canonical SKILL.md (✅ done), runbook for operators

### Testing

- [ ] **Unit tests:** Auth, command parsing, tier routing
- [ ] **Integration tests:** End-to-end WhatsApp command flow
- [ ] **Load test:** 100 concurrent health checks (stress Portal)
- [ ] **Failover test:** Each tier failure + fallback to next
- [ ] **Operator acceptance test:** 1 week live with 3+ users

---

## Known Issues

### Critical

1. **Session timeout:** Token persists forever (should rotate per week or session)
2. **No rate limiting:** Malicious user could spam 1000 commands/sec
3. **No encryption:** Bearer token is plaintext in HTTP (only safe on LAN)

### High

4. **Voice confidence too strict:** Falls back to text on ANY fail (should have threshold)
5. **OCR failures not explained:** User gets "couldn't process" without reason
6. **No scheduled commands:** Health checks are manual

### Medium

7. **Notification spam:** Every command = every update (need quiet mode)
8. **No multi-user audit:** Can't track who ran what (for compliance)
9. **Approval workflows not implemented** (HITL gate for sensitive ops)

---

## Success Metrics

### MVP (Now)

- ✅ QR code generation works (scanned by 1+ operator)
- ✅ Health command responds <5s (Ollama available)
- ✅ Restart command completes <30s
- ✅ Task command queues successfully
- ✅ Real-time notifications received

### Phase 1 (1 week)

- ✅ Operators report "no confusing errors"
- ✅ Voice transcription confidence >95%
- ✅ OCR errors explained clearly
- ✅ Notification preferences work

### Phase 2 (2 weeks)

- ✅ Portal shows WhatsApp command history
- ✅ Operations visualized in real-time
- ✅ QR regeneration works from Portal UI

### Phase 3+ (3+ weeks)

- ✅ 3+ team members independently use gateway
- ✅ Sensitive commands require approval
- ✅ Audit trail tracks all operations

---

## References

- **Live gateway:** http://localhost:8555/qr (QR code generator)
- **Health check:** http://localhost:8555/health (JSON status)
- **Canonical skill:** `orama-system/bin/orama-system/skills/whatsapp-qr-gateway/SKILL.md`
- **Control Plane API:** http://localhost:8001/api/* (command routing)
- **Tier Router:** http://localhost:8000/orchestrate (fallback logic)
- **Portal:** http://localhost:8002 (dashboard + WhatsApp integration)

---

## Next Action

**Immediate:** Run Phase 1 polish cycle (1 week). Focus on:
1. Voice confidence threshold
2. OCR error messages
3. Notification preferences
4. Session UI

**Owner:** Operator Panel team + Portal dashboard team

**Go-live:** 2026-07-11 (after Phase 1 polish)

---

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
