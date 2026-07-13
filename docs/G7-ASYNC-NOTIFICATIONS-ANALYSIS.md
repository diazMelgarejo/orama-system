# G7: Async Notifications — Analysis & MVP Recommendation

> **Date:** 2026-07-11  
> **Status:** Analysis Complete — Recommendation: Implement MVP  
> **Blocker Risk:** None — can be built on existing infrastructure

---

## Executive Summary

G7 addresses a **coordination gap**: agents, operators, and integrations need **push notifications** for system state changes without polling. Current portal uses pull-based status polling (10s refresh). This gap blocks multi-agent awareness, operator alerting, and webhook integrations.

**Recommendation:** Implement **Portal Notification Hub** — a minimal MVP extending existing LAN peer channel infrastructure, wired into portal's existing service monitors. Ships as Phase 2.1 (post-portal dashboard hardening, pre-GossipMesh v2.1).

---

## Current State Analysis

### ✓ Existing Infrastructure (Reusable)

| Component | Location | Status | Capability |
|-----------|----------|--------|-----------|
| **LAN Peer Channel** | `lan_peer_channel.py` | Shipped v1 | WebSocket + SSE outbound queue, async envelope emission |
| **Event Envelope** | `lan_peer_channel.py` §`make_envelope()` | Shipped v1 | Versioned JSON: `type`, `source`, `ts`, `data` |
| **Portal SSE** | `portal_server.py` §`/events/peer-stream` | Shipped v1 | Text/event-stream response, async generator |
| **Service Monitors** | `portal_server.py` §`_probe_*` | Shipped v1 | Agents, routing, hardware, activity feeds already tracked |
| **GossipBus Kernel** | `perpetua_core/gossip.py` (planned v2) | Not yet integrated | Event log + append-only redaction; PT already has `orchestrator/gossip_bus.py` |

### ✗ Gaps (To Implement)

1. **Portal doesn't emit events** — monitors only pull state; no push to subscribers
2. **No event subscription filter** — SSE broadcasts all peers; no topic/capability scoping  
3. **No durable event queue** — SSE clients miss events during disconnect (best-effort only)
4. **No webhook/email integration** — notifications live in WebSocket/SSE only
5. **No event schema versioning** — portal event types undefined; may collide with v2.1 GossipBus

---

## Events That Should Trigger Notifications

### Critical (Phase 2 MVP)

- **Agent state changed** — running → idle | error | waiting → running
- **Fleet topology changed** — peer connected | peer disconnected | peer stale
- **Hardware affinity violation** — model/tier mismatch detected
- **Job completed** — V1 supervisor job done/failed
- **Phase transition** — new L1 phase dispatched (blocks swarm awareness)

### Important (Phase 2.1+)

- Security events (auth failure, policy violation, secret rotation)
- Model/backend unavailable → fallback activated
- Manual control-plane actions (stop/restart/policy recheck)

### Deferred to v2.1 GossipMesh

- Cross-particle gossip (PT ↔ orama shared event stream)
- Interest-filtered subscriptions by `session_id`/`topic`

---

## Scope Analysis: Transport Options

| Option | Pros | Cons | Fit |
|--------|------|------|-----|
| **WebSocket (extend `/ws/portal-peer`)** | Low latency, bidirectional, auth-bearable | Single connection per client, no queue after disconnect | Good for dashboard |
| **Server-Sent Events (extend `/events/peer-stream`)** | Browser-native, one-way simple, REST-compatible | No client→server, stateless (no subscriptions), best-effort | Good for operator alerts |
| **Polling `/api/notifications/latest` (query param: `since_ts`)** | Simplest, cacheable, discoverable | Inefficient, scales poorly at # clients | Fallback only |
| **Redis PubSub** | Reliable, scalable, multi-instance | New infra dependency, breaks loopback-only policy | Reject for MVP |

**MVP choice:** Extend existing `/events/peer-stream` with event **filters** (query param: `?types=agent_state,job_complete`); add optional durable queue (SQLite, 100-event cap per client session) behind feature flag.

---

## MVP Design Recommendation

### Layer 1: Portal Notification Service

**File:** `src/orama_system/portal_notifications.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any
import asyncio
from datetime import datetime

class EventType(Enum):
    AGENT_STATE_CHANGED = "agent_state_changed"
    TOPOLOGY_CHANGED = "topology_changed"
    HARDWARE_VIOLATION = "hardware_violation"
    JOB_COMPLETED = "job_completed"
    PHASE_TRANSITION = "phase_transition"

@dataclass
class Notification:
    type: EventType
    timestamp: float
    source: str  # "portal" | "peer" | "supervisor"
    data: dict[str, Any]
    
    def to_sse(self) -> str:
        """SSE-format: data: {json}\n\n"""
        import json
        return f"data: {json.dumps({
            'type': self.type.value,
            'ts': self.timestamp,
            'source': self.source,
            'data': self.data
        })}\n\n"

class NotificationHub:
    def __init__(self, max_queue=100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        self._subscriptions: dict[str, set[EventType]] = {}  # session_id → event types
    
    async def emit(self, event: EventType, data: dict[str, Any], source: str = "portal"):
        """Emit event to all subscribers."""
        notif = Notification(event, time.time(), source, data)
        try:
            self._queue.put_nowait(notif)
        except asyncio.QueueFull:
            # Drop oldest on overflow; retain latest alerts
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(notif)
            except asyncio.QueueEmpty:
                pass
    
    async def subscribe(self, session_id: str, types: list[str]):
        """Register interest filter."""
        self._subscriptions[session_id] = {
            EventType[t.upper()] for t in types 
            if t.upper() in [e.name for e in EventType]
        }
    
    async def stream(self, session_id: str):
        """AsyncGenerator: yield notifications matching session interest."""
        subscribed = self._subscriptions.get(session_id, set(EventType))
        while True:
            notif = await self._queue.get()
            if subscribed and notif.type not in subscribed:
                continue
            yield notif.to_sse()
```

### Layer 2: Portal Route Integration

**File:** `portal_server.py` (append to existing SSE route)

```python
_notification_hub = NotificationHub()

@app.get("/api/notifications/stream")
async def notifications_stream(request: Request, types: str | None = None):
    """
    SSE notifications: ?types=agent_state,job_complete
    Auth: inherited from middleware; portal auth enforced.
    """
    session_id = secrets.token_hex(8)
    if types:
        await _notification_hub.subscribe(session_id, types.split(","))
    
    async def generator():
        async for sse_line in _notification_hub.stream(session_id):
            yield sse_line
    
    return StreamingResponse(generator(), media_type="text/event-stream")
```

### Layer 3: Wire Into Existing Monitors

**File:** `portal_server.py` (modify `_render_html()` and probe tasks)

```python
# In probe/render pipeline, after state updates:

# Agent state changed
if old_agents != new_agents:
    await _notification_hub.emit(
        EventType.AGENT_STATE_CHANGED,
        {"agents": redact_agents_payload(new_agents)},
    )

# Topology changed (peer health monitor)
if old_routing.get("mac_reachable") != new_routing.get("mac_reachable"):
    await _notification_hub.emit(
        EventType.TOPOLOGY_CHANGED,
        {"mac_reachable": new_routing.get("mac_reachable")},
    )

# Hardware violation
if old_violations != policy_status.get("violations"):
    await _notification_hub.emit(
        EventType.HARDWARE_VIOLATION,
        {"violations": policy_status.get("violations", [])},
    )
```

---

## Dependencies & Blockers

| Item | Status | Impact |
|------|--------|--------|
| Existing WebSocket/SSE infra | ✓ Shipped | Zero blocker |
| Notification schema (EventType enum) | ⚠ New spec | Non-breaking; pure addition |
| Redaction policy (already exists) | ✓ Shipped | Reuse `redact_agents_payload()` etc. |
| Auth middleware integration | ✓ Shipped | Inherit from existing `/api/*` routes |
| PT GossipBus alignment | ⚠ Design debt | MVP uses local portal only; v2.1 GossipMesh replaces with shared schema |

**No external dependencies.** Uses asyncio, FastAPI, stdlib only.

---

## Risk Assessment

### Low Risk ✓
- Builds on proven LAN peer channel code
- Event emission is write-only (no state mutations)
- SSE clients are best-effort anyway (same contract as current polling)
- Feature-flaggable: `PORTAL_NOTIFICATIONS=0` disables

### Medium Risk ⚠
- **Design debt:** MVP event schema will be subsumed by GossipBus v2.1; recommend adding a `version` field now (`"version": 1`) so migration is cheap
- **Storage:** durable event queue (if added) needs SQLite table; runs in portal process (no new infra)

### Mitigation
- Make event schema versioned and redaction-scoped from start
- Ship with feature flag disabled by default; ops enable when ready
- Add acceptance test: "notifications received within 2s of state change" (same 10s refresh SLA as current polling)

---

## Implementation Checklist

- [ ] Define `EventType` enum and `Notification` dataclass
- [ ] Implement `NotificationHub` with FIFO queue + subscription filter
- [ ] Add `/api/notifications/stream?types=...` SSE route
- [ ] Wire hub into existing service monitors (agent state, topology, hardware, jobs)
- [ ] Add redaction: ensure agents/routing payloads use existing `redact_*` helpers
- [ ] Add auth regression test: unauthenticated clients get 401 on `/api/notifications/stream`
- [ ] Feature flag: `PORTAL_NOTIFICATIONS=1` (default: 0)
- [ ] Acceptance test: emit event, verify receipt within 2s on SSE client
- [ ] Document in portal `/api` reference (add to `GET /` response in v2 dashboard)

---

## Recommendation: Claim & Proceed

**Status:** Ready to claim.

**Command:**
```bash
python3 scripts/agent_coordination.py queue add "G7-async-notifications" "Security" --priority HIGH
python3 scripts/agent_coordination.py queue claim "G7-async-notifications" "agy-async-notif"
```

**Next step:** Proceed with implementation sprint (estimated 2–3 hours for MVP).

---

## Cross-References

- Kernel event design: `docs/v2/01-kernel-spec.md` §5 (GossipBus)
- v2.1 mesh transport: `docs/v2/43-gossipbus-mesh-transport.md`
- Security contracts: `SECURITY.md` Immediate TODO §C (unauthenticated notification blocking)
- Portal architecture: `src/orama_system/portal_server.py` §probes
