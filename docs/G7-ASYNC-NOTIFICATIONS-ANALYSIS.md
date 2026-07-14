# G7: Async Notifications — Analysis & MVP Recommendation

> **Date:** 2026-07-11  
> **Status:** Analysis Complete — Recommendation: Implement MVP  
> **Blocker Risk:** None — can be built on existing infrastructure

---

## Executive Summary

G7 addresses a **coordination gap**: agents, operators, and integrations need **push notifications** for system state changes without polling. Current portal uses pull-based status polling (10s refresh). This gap blocks multi-agent awareness, operator alerting, and webhook integrations.

**Recommendation:** Implement **Portal Notification Hub** — a minimal MVP extending existing LAN peer channel infrastructure, wired into portal's existing service monitors. Keep it local to the portal for the MVP, but shape the envelope and filters so planned GossipBus/GossipMesh v2.1 can consume or replicate the events later.

---

## Current State Analysis

### ✓ Existing Infrastructure (Reusable)

| Component | Location | Status | Capability |
|-----------|----------|--------|-----------|
| **LAN Peer Channel** | `lan_peer_channel.py` | Shipped v1 | WebSocket + SSE outbound queue, async envelope emission |
| **Event Envelope** | `lan_peer_channel.py` §`make_envelope()` | Shipped v1 | Versioned JSON: `type`, `source`, `ts`, `data` |
| **Portal SSE** | `portal_server.py` §`/events/peer-stream` | Shipped v1 | Text/event-stream response, async generator |
| **Service Monitors** | `portal_server.py` §`_probe_*` | Shipped v1 | Agents, routing, hardware, activity feeds already tracked |
| **GossipBus/GossipMesh v2.1** | `docs/v2/43-gossipbus-mesh-transport.md` | Planned mesh transport | Event-envelope conventions: versioned, redacted, interest-filtered deltas; MVP should stay compatible without implementing mesh replication |

### ✗ Gaps (To Implement)

1. **Portal doesn't emit events** — monitors only pull state; no push to subscribers
2. **No event subscription filter** — SSE broadcasts all peers; no topic/capability scoping  
3. **No durable event queue** — SSE clients miss events during disconnect (best-effort only)
4. **No webhook/email integration** — notifications live in WebSocket/SSE only
5. **No v2.1-compatible portal notification envelope yet** — portal event types and payload shape need a versioned local contract before implementation begins

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
- Interest-filtered mesh tail/ingest by `event_type`, `session_id`, `particle_id`, or `topic`
- Durable replication between particles; G7 MVP remains portal-local SSE only

---

## Scope Analysis: Transport Options

| Option | Pros | Cons | Fit |
|--------|------|------|-----|
| **WebSocket (extend `/ws/portal-peer`)** | Low latency, bidirectional, auth-bearable | Single connection per client, no queue after disconnect | Good for dashboard |
| **Server-Sent Events (extend `/events/peer-stream`)** | Browser-native, one-way simple, REST-compatible | No client→server, stateless (no subscriptions), best-effort | Good for operator alerts |
| **Polling `/api/notifications/latest` (query param: `since_ts`)** | Simplest, cacheable, discoverable | Inefficient, scales poorly at # clients | Fallback only |
| **Redis PubSub** | Reliable, scalable, multi-instance | New infra dependency, breaks loopback-only policy | Reject for MVP |

**MVP choice:** Add `/api/notifications/stream` with event **filters** (query param: `?types=agent_state_changed,job_completed`); use per-session in-memory queues for the MVP, optionally backed by SQLite later, behind `PORTAL_NOTIFICATIONS=1`.

---

## MVP Design Recommendation

### Layer 1: Portal Notification Service

**File:** `src/orama_system/portal_notifications.py`

```python
import asyncio
import json
import os
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

class EventType(Enum):
    AGENT_STATE_CHANGED = "agent_state_changed"
    TOPOLOGY_CHANGED = "topology_changed"
    HARDWARE_VIOLATION = "hardware_violation"
    JOB_COMPLETED = "job_completed"
    PHASE_TRANSITION = "phase_transition"

@dataclass
class Notification:
    version: int
    type: EventType
    timestamp: float
    source: str  # "portal" | "peer" | "supervisor"
    data: dict[str, Any]

    def to_sse(self) -> str:
        """SSE-format: data: {json}\n\n"""
        return "data: " + json.dumps({
            "version": self.version,
            "type": self.type.value,
            "event_type": self.type.value,  # v2.1 adapter-friendly alias
            "ts": self.timestamp,
            "source": self.source,
            "data": self.data,
            "payload": self.data,  # v2.1 adapter-friendly alias
        }) + "\n\n"

class NotificationHub:
    def __init__(self, max_queue=100):
        self._max_queue = max_queue
        self._subscriptions: dict[str, set[EventType]] = {}
        self._queues: dict[str, asyncio.Queue[Notification]] = {}

    async def emit(self, event: EventType, data: dict[str, Any], source: str = "portal"):
        """Fan out event to every subscribed session queue."""
        notif = Notification(1, event, time.time(), source, data)
        for session_id, subscribed in list(self._subscriptions.items()):
            if subscribed and event not in subscribed:
                continue
            queue = self._queues.get(session_id)
            if queue is None:
                continue
            if queue.full():
                try:
                    queue.get_nowait()  # drop oldest; retain latest alerts
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(notif)

    async def subscribe(self, session_id: str, types: list[str] | None):
        """Register interest filter using EventType.value strings."""
        by_value = {event.value: event for event in EventType}
        if not types:
            subscribed = set(EventType)
        else:
            subscribed: set[EventType] = set()
            invalid: list[str] = []
            for raw in types:
                value = raw.strip()
                if not value:
                    continue
                event = by_value.get(value)
                if event is None:
                    invalid.append(value)
                else:
                    subscribed.add(event)
            if invalid or not subscribed:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid notification type(s): {', '.join(invalid) or 'empty'}",
                )
        self._subscriptions[session_id] = subscribed
        self._queues[session_id] = asyncio.Queue(maxsize=self._max_queue)

    async def stream(self, session_id: str) -> AsyncIterator[str]:
        """Yield notifications for one subscribed session."""
        queue = self._queues[session_id]
        try:
            while True:
                yield (await queue.get()).to_sse()
        finally:
            self._subscriptions.pop(session_id, None)
            self._queues.pop(session_id, None)
```


### Layer 2: Portal Route Integration

**File:** `portal_server.py` (append to existing SSE route)

```python
PORTAL_NOTIFICATIONS_ENABLED = os.getenv("PORTAL_NOTIFICATIONS") == "1"
_notification_hub: NotificationHub | None = (
    NotificationHub() if PORTAL_NOTIFICATIONS_ENABLED else None
)

@app.get("/api/notifications/stream")
async def notifications_stream(request: Request, types: str | None = None):
    """
    SSE notifications: ?types=agent_state_changed,job_completed
    Auth: inherited from middleware; portal auth enforced.
    """
    if _notification_hub is None:
        raise HTTPException(status_code=404, detail="notifications disabled")

    session_id = secrets.token_hex(8)
    await _notification_hub.subscribe(
        session_id,
        types.split(",") if types is not None else None,
    )

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
| PT GossipBus/GossipMesh alignment | ⚠ Design debt | MVP uses local portal only; v2.1 GossipMesh may consume/replicate compatible versioned envelopes later |

**No external dependencies.** Uses asyncio, FastAPI, stdlib only.

---

## Alignment with `/docs/v2` Future Specs

G7 is a v1 portal MVP, but it must leave a clean seam for v2.0, v2.1, and v2.5. The rule is **compatible envelope now, no premature mesh or safety overlay now**.

| Future spec | G7 alignment decision | What G7 must not do yet |
|-------------|-----------------------|--------------------------|
| `docs/v2/01-kernel-spec.md` | Emit small state-change events that can later map to kernel `GossipBus` / `PerpetuaState` metadata. Keep the envelope versioned and source-tagged. | Do not import or depend on `perpetua-core`; v1 portal remains standalone. |
| `docs/v2/23-security-preconditions.md` + `docs/v2/24-security-first-platform.md` | Treat `/api/notifications/stream` as a control-plane read route: default off, server-side auth, loopback/dev behavior inherited from existing middleware, redaction before enqueue, auth-denial tests. | Do not rely on client-side hiding, query parameters, or UI state for authorization. Do not include raw bearer tokens, prompts, transcripts, or unredacted agent/job records in events. |
| `docs/v2/43-gossipbus-mesh-transport.md` (v2.1) | Preserve adapter fields: `version`, `type`, `event_type`, `ts`, `source`, `data`, and `payload`. Subscription filters should use `event_type`-compatible names. | Do not add mesh tail/ingest endpoints, Redis/NATS, cross-particle replication, durable replay, or peer-to-peer trust scoring in the MVP. |
| `docs/v2/03-safety-v2.5.md` | Keep events audit-friendly enough for future MAESTRO/SWARM observers: stable type names, redacted payloads, no destructive side effects from streaming. | Do not claim v2.5 enforcement. No risk scoring, kill switch, cryptographic agent attestation, quorum, or HITL auto-injection belongs in this G7 MVP. |
| `docs/v2/45-single-operator-lan-threat-model-descope.md` | Keep bounded queues and redaction because they help honest-but-flaky operation. Re-run the Q1-Q3 threat check before adding adversarial P2P controls. | Do not wire Sybil/quorum/reputation/equivocation controls for a single-operator LAN without a changed trust boundary. |

### v2 security design-gate answers for this MVP surface

1. **Attacker:** same-LAN client, malicious web page trying to open an EventSource, local process with no bearer, compromised browser tab, and accidental log/payload leakage.
2. **Trust boundary:** HTTP request to `/api/notifications/stream`, `types` query parameter, and producer payloads crossing from portal monitors into subscriber-visible JSON.
3. **Capability:** control-plane `read`. The route is not public. It must use existing portal auth behavior.
4. **Fail closed:** feature flag unset returns `404`; enforced auth without a valid bearer returns `401`; unknown event type returns `400`; producer failures must not mutate portal state.
5. **Logged/redacted:** only redacted notification payloads may be emitted. Future audit logs may record event type/source/subscriber count, never secrets, raw prompts, bearer tokens, or full transcripts.
6. **CI proof:** notification tests must cover default-off `404`, enforced-auth `401`, invalid filter `400`, envelope adapter aliases, bounded queue cleanup, and future v2 alignment constants.

---

## Risk Assessment

### Low Risk ✓
- Builds on proven LAN peer channel code
- Event emission is write-only (no state mutations)
- SSE clients are best-effort anyway (same contract as current polling)
- Feature-flaggable: `PORTAL_NOTIFICATIONS=0` skips hub initialization and leaves the SSE endpoint unavailable

### Medium Risk ⚠
- **Design debt:** MVP event schema must remain adapter-friendly for GossipBus/GossipMesh v2.1; include `version`, `event_type`, and `payload` aliases now so migration is cheap
- **Storage:** durable event queue (if added) needs SQLite table; runs in portal process (no new infra)
- **Future-spec drift:** agents may try to overbuild v2.1 mesh or v2.5 safety features inside the G7 branch. Guardrail: keep those as documented seams and tests only.

### Mitigation
- Make event schema versioned and redaction-scoped from start
- Ship with feature flag disabled by default; disabled means no hub initialization, no monitor emission wiring, and no active SSE stream
- Add acceptance test: "notifications received within 2s of state change" (same 10s refresh SLA as current polling)

---

## Implementation Checklist

- [ ] Define `EventType` enum and `Notification` dataclass
- [ ] Implement `NotificationHub` with per-session FIFO queues + subscription filters
- [ ] Add `/api/notifications/stream?types=...` SSE route gated by `PORTAL_NOTIFICATIONS=1`
- [ ] Wire hub into existing service monitors (agent state, topology, hardware, jobs)
- [ ] Add redaction: ensure agents/routing payloads use existing `redact_*` helpers
- [ ] Add auth regression test: unauthenticated clients get 401 on `/api/notifications/stream`
- [ ] Feature flag: `PORTAL_NOTIFICATIONS=1` (default: 0)
- [ ] Acceptance test: emit event, verify receipt within 2s on SSE client
- [ ] Document in portal `/api` reference (add to `GET /` response in v2 dashboard)
- [ ] Keep v2.1/v2.5 alignment additive: preserve envelope fields and security invariants, but defer mesh replication, durable replay, and safety overlays to `/docs/v2` milestones.

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
- v2 security preconditions: `docs/v2/23-security-preconditions.md`, `docs/v2/24-security-first-platform.md`
- v2.1 mesh transport: `docs/v2/43-gossipbus-mesh-transport.md`
- v2.5 safety overlays: `docs/v2/03-safety-v2.5.md`
- single-operator LAN descope: `docs/v2/45-single-operator-lan-threat-model-descope.md`
- Security contracts: `SECURITY.md` Immediate TODO §C (unauthenticated notification blocking)
- Portal architecture: `src/orama_system/portal_server.py` §probes
