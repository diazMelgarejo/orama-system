# API Reference

## Scripts

### verify_before_done.py
```
python verify_before_done.py [OPTIONS]

Options:
  --task NAME       Task name for the report (default: "Unnamed Task")
  --dir PATH        Project directory to verify (default: ".")
  --no-interact     Skip interactive staff engineer check
  --check TYPE      Run specific check: all|tests|lint|debug|plan|se

Exit codes: 0 = PASS, 1 = FAIL
Output: tasks/verification-report.json
```

### capture_lesson.py
```
python capture_lesson.py [OPTIONS]

Options:
  --pattern NAME    Mistake pattern name (skips category selection)
  --quick           Minimal prompts
  --review          Show all existing lessons
  --stats           Show mistake category statistics
  --dir PATH        Project directory (default: ".")
```

### create_task_plan.sh
```
./create_task_plan.sh [TASK_NAME] [OPTIONS]

Options:
  --optimize TYPE   reliability|creativity|speed (default: reliability)
  --dir PATH        Project directory (default: ".")
  --interactive     Guided prompt mode

Creates: tasks/todo.md. It does not create a legacy lesson log.
```

## MCP Tools (Multi-Agent)

### oramasys_solve
```json
{
  "task": "string (required)",
  "optimize_for": "reliability|creativity|speed",
  "context": {}
}
→ { "task_id": "uuid", "status": "started" }
```

### oramasys_delegate
```json
{
  "stage": "context|architecture|refinement|execution|verification|crystallization",
  "task_id": "uuid",
  "input": {}
}
→ { "delegated_to": "agent-id", "status": "queued" }
```

### oramasys_status
```json
{ "task_id": "uuid" }
→ TaskState object
```

### oramasys_lessons
```json
{ "domain": "optional filter", "limit": 10 }
→ { "lessons": [...], "total": N }
```

## Data Types

### TaskState
```typescript
{
  task_id: string
  task_description: string
  optimize_for: "reliability" | "creativity" | "speed"
  current_stage: "context_immersion" | "architecture" | "refinement" | "execution" | "verification" | "crystallization" | "done"
  iteration_count: number
  elegance_score: number (0.0–1.0)
  stage_outputs: Record<string, any>
  lessons_learned: Lesson[]
}
```

### ValidationReport
```typescript
{
  symbol: string
  status: "PASS" | "WARNING" | "FAIL"
  checks: ValidationCheck[]
  timestamp: string
}
```

---

## REST API (`api_server.py`)

The ὅραμα System exposes a stateless HTTP API.

```bash
# Start (requires: pip install fastapi uvicorn pydantic)
python api_server.py

# POST /oramasys
curl -X POST http://localhost:8001/oramasys \
  -H "Content-Type: application/json" \
  -d '{"task_description": "Build auth system", "optimize_for": "reliability"}'

# GET /health
curl http://localhost:8001/health
```

`POST /ultrathink` remains as a deprecated compatibility shim for one v1.x
release. New clients should use `/oramasys`.

### Request Body
```json
{
  "task_description": "string (required, max 10000 chars)",
  "optimize_for": "reliability | creativity | speed",
  "model_hint": "haiku | sonnet | opus | fast | balanced | powerful (optional)",
  "context": {},
  "request_id": "uuid (optional)"
}
```

### Response
```json
{
  "request_id": "uuid",
  "status": "accepted",
  "task_id": "uuid",
  "message": "Task accepted for mode2 execution.",
  "mode": "mode1 | mode2 | mode3",
  "elapsed_ms": 0.5
}
```

**Stateless**: no Redis dependency. Durable state owned by Perpetua-Tools (Repo #1).

## Portal Notification Stream (G7)

Default-off (`PORTAL_NOTIFICATIONS=1`), authenticated, portal-local SSE stream
of redacted state-change events. See
[the G7 implementation plan](superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md)
for full design rationale.

### POST /api/notifications/session

Creates a 15-minute host-only browser session for the notification stream. Send an existing Authorization bearer credential from the same origin. The response sets an HttpOnly, SameSite=Strict cookie scoped to /api/notifications. A cross-origin request receives 403. Never put the token in a URL.

Why this step exists: native browser `EventSource` cannot set custom headers, so a
bearer credential can't reach the stream directly. This endpoint exchanges an
already-held bearer for a narrowly-scoped, short-lived cookie the browser will
attach automatically.

### GET /api/notifications/stream?types=job_completed,agent_state_changed

The endpoint is disabled until PORTAL_NOTIFICATIONS=1 (404 while disabled). It
returns 401 without a valid session cookie or bearer — call `POST
/api/notifications/session` first — and 400 for an unknown event type (response
body lists the valid types: `agent_state_changed`, `fleet_topology_changed`,
`hardware_status_changed`, `job_completed`, `phase_transition`).

Delivery is bounded and best-effort; a slow subscriber loses its oldest queued
event. The current aggregate drop count is visible at `GET /api/status` under
`notification_delivery.dropped_events`. On reconnect, fetch `/api/status` for a
new redacted snapshot before resuming the stream — Last-Event-ID is not replayed
in this MVP. The session cookie expires after 15 minutes; `EventSource` will
auto-reconnect on drop but cannot re-authenticate itself, so a client must detect
a stalled/erroring stream and re-POST `/api/notifications/session` before
recreating the `EventSource`, not rely on automatic reconnect alone.

**Copy-paste client example** (the two most common SSE integration mistakes —
missing the session bootstrap, and listening on the default `message` event
instead of the typed `event:` name — are both handled below):

```javascript
async function connectNotifications(bearerToken) {
  await fetch("/api/notifications/session", {
    method: "POST",
    headers: { Authorization: `Bearer ${bearerToken}` },
    credentials: "include",
  });

  const source = new EventSource("/api/notifications/stream", { withCredentials: true });
  // Events are framed with `event: <type>`, e.g. `event: job_completed` — the
  // default 'message' listener never fires. Register one listener per type.
  for (const type of ["agent_state_changed", "hardware_status_changed", "job_completed"]) {
    source.addEventListener(type, (event) => {
      const notification = JSON.parse(event.data);
      console.log(type, notification);
    });
  }
  source.onerror = () => {
    // No error code is exposed here; a 401 after cookie expiry looks
    // identical to a network drop. Re-run the session bootstrap before
    // assuming this is a transient network issue.
  };
  return source;
}
```

`type`/`event_type` and `data`/`payload` are duplicate keys by design — stable
aliases kept for GossipBus v2.1 mesh compatibility (docs/v2/43). Either name is
safe to read today; they carry identical values.

**Residual risk, disclosed here (not just in the plan file):** the notification
stream inherits this codebase's existing single-operator-LAN trust posture —
any local process on an allow-listed CORS origin (localhost:3000, :8002) can
read this stream once the session cookie is bootstrapped, same as every other
authenticated portal route. See `docs/v2/45-single-operator-lan-threat-model-descope.md`.
