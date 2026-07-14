# G7 Authenticated SSE Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Ship a default-off, authenticated, portal-local SSE notification stream with bounded best-effort delivery, redacted edge-triggered updates, and a stable v2-compatible envelope.

**Architecture:** NotificationHub remains process-local and producer-agnostic. A snapshot-diff publisher turns already-redacted portal status into typed Notification values. The stream route projects each value into standard SSE id, event, and data fields. Native EventSource uses a short-lived, same-origin, path-scoped control-plane cookie; no bearer is accepted in a URL.

**Tech Stack:** Python 3.10+, FastAPI, Starlette StreamingResponse, asyncio, pytest, pytest-asyncio, browser EventSource/SSE.

## Global Constraints

- docs/v2/* is authoritative; this plan is subordinate to it.
- PORTAL_NOTIFICATIONS remains disabled unless its value is 1, true, yes, or on.
- The MVP adds no Redis, NATS, durable storage, replay window, mesh replication, webhooks, or v2.5 safety enforcement.
- Enqueue only redacted deltas. Never stream raw prompts, transcripts, paths, tokens, model endpoints, or job records.
- Never accept a control-plane bearer in a query parameter or emit one into HTML, JavaScript, logs, or an envelope.
- On overflow, drop the oldest queued event, retain the newest, and expose the aggregate loss count in process.
- Reconnection is snapshot then live stream. Last-Event-ID does not imply replay.
- Work only in the G7-Async-notifications-mvp worktree. Preserve the existing Perpetua-Tools vendor/ecc-tools and packages/agentic-stack changes.

## Placement in the Fleet-Mesh System

This plan is a Phase-7-adjacent implementation handoff, not an autonomous
architecture. Use the graph below to recover the governing constraints and the
evidence behind each decision. A direct edge exists from this plan to every
necessary active, canonical, historical, research, and cross-repository node;
following the directed paths keeps any relevant context within a few hops without
turning an MVP plan into an all-to-all document dump.

### Authority Order

1. [`docs/v2/`](../../v2/) is canonical and supersedes this plan when they
   conflict.
2. [`39-maestro-owasp-genai-reference.md`](../../v2/39-maestro-owasp-genai-reference.md)
   is the security-verification hub for browser authentication, secrets,
   control-plane exposure, and related changes.
3. [`43-gossipbus-mesh-transport.md`](../../v2/43-gossipbus-mesh-transport.md)
   is the canonical future mesh direction. It constrains compatibility but does
   not authorize G7 to add replication, durable delivery, or Byzantine logic.
4. The active [fleet-mesh index](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/README.md)
   owns the SOLO / PAIR / FLEET lineage and points to the root plans. This link
   becomes canonical after the documentation-reorganization commit lands on
   `main`; before then, use the repository's current root and `docs/plans/`
   locations as the same source material.
5. This plan, the [G7 analysis](../../G7-ASYNC-NOTIFICATIONS-ANALYSIS.md), and
   the [SSE production research](../references/2026-07-14-g7-sse-production-patterns.md)
   turn that authority into a narrow portal-local MVP.
6. Completed reports and historical ledgers are evidence only. They never
   override active documentation or live code.

### Node Map and Direct Edges

| Node | Direct links | Role in this implementation |
|---|---|---|
| Canonical architecture | [`docs/v2/`](../../v2/), [`43 GossipBus`](../../v2/43-gossipbus-mesh-transport.md) | Defines future event/mesh compatibility boundaries; records what stays deferred. |
| Canonical security | [`39 MAESTRO/OWASP`](../../v2/39-maestro-owasp-genai-reference.md) | Governs control-plane auth, redaction, browser exposure, and verification sources. |
| Fleet-mesh root | [active index](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/README.md), [mother plan](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/2026-07-08-self-healing-mesh-degradation-modes.md), [integration map](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/2026-07-10-phase-integration-map.md) | Explains why G7 follows the mesh lineage and how it relates to Phase 1-10+ work. |
| Mesh research | [OASN research](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/2026-07-10-oasn-p2p-architecture-research.md), [PT Phase 2 spec](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/PHASE-2-SPEC.md) | Supplies topology and membership context. It is not a mandate to implement P2P transport in G7. |
| G7 product scope | [local G7 analysis](../../G7-ASYNC-NOTIFICATIONS-ANALYSIS.md), [future active location](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | Defines the Portal Notification Hub scope, default-off flag, and initial checklist. |
| G7 research evidence | [SSE production patterns](../references/2026-07-14-g7-sse-production-patterns.md) | Justifies EventSource auth constraints, bounded queues, event envelopes, overflow behavior, and no-replay semantics. |
| This handoff | [authenticated SSE MVP plan](2026-07-14-g7-authenticated-sse-mvp.md) | Gives the file-by-file TDD sequence; it must be revised if higher authority changes. |
| PT security companions | [pattern synthesis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PATTERN-SYNTHESIS.md), [swarm security analysis](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md) | Provides later-mesh threat and pattern context. Do not alter threat-model claims while implementing G7 unless separately tasked. |
| Completed evidence | [fleet-mesh archive](https://github.com/diazMelgarejo/orama-system/blob/main/docs/archive/fleet-mesh/README.md), [Phase 7-10 roadmap](https://github.com/diazMelgarejo/orama-system/blob/main/docs/next/fleet-mesh/phase-7-to-10-roadmap.md) | Explains the Phase 5-6 completion clue and where G7 sits in the continuation. |

### Directed Context Paths

```text
docs/v2 security and GossipBus authority
  -> active fleet-mesh index
  -> mother plan / integration map / OASN research
  -> G7 async-notification analysis
  -> SSE production research
  -> this TDD implementation plan
  -> portal-local, feature-flagged code and tests

completed Phase 5-6 report + historical review ledger
  -> fleet-mesh archive
  -> active index and Phase 7-10 roadmap
  -> G7 analysis and this plan

PT Phase 2 runtime + PT threat and pattern evidence
  -> active fleet-mesh index
  -> docs/v2 authority
  -> G7 compatibility and security boundaries
```

The direction matters. Implementation starts here, but decision authority flows
back through G7 research to the active fleet-mesh index and `docs/v2/`. New
requirements that would add replay, retention, cross-process fan-out, mesh
replication, or safety enforcement must branch into their own approved plan
instead of being smuggled into this MVP.

---

## File Structure

| File | Responsibility |
| --- | --- |
| src/orama_system/portal_notifications.py | Immutable envelope, bounded hub, and redacted status-diff publisher. |
| src/orama_system/portal_server.py | Session-cookie endpoint, SSE response, and publisher invocation. |
| src/utils/control_plane_auth.py | Existing token, origin, and cookie primitives; do not add another credential store. |
| tests/test_portal_notifications.py | Contract, auth, overflow, stream-framing, and delta tests. |
| docs/api-reference.md | Operator setup, filtering, overflow, and recovery contract. |
| docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md | Keep analysis aligned with shipped behavior. |

### Task 1: Version the Envelope and Bound Slow Consumers

**Files:**
- Modify: src/orama_system/portal_notifications.py:11-99
- Test: tests/test_portal_notifications.py:50-95

**Interfaces:**
- Consumes: EventType, Notification, NotificationHub.
- Produces: Notification.event_id: str and NotificationHub.dropped_events: int.

- [ ] **Step 1: Write failing contract tests**

~~~python
@pytest.mark.asyncio
async def test_notification_envelope_has_opaque_event_id():
    notification = Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"})
    payload = notification.to_dict()

    assert payload["event_id"] == notification.event_id
    assert payload["type"] == payload["event_type"] == "job_completed"
    assert payload["data"] == payload["payload"] == {"job_id": "redacted-job"}


@pytest.mark.asyncio
async def test_notification_hub_drops_oldest_and_retains_newest():
    hub = NotificationHub(queue_size=2)
    stream = hub.subscribe()
    waiter = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)

    for sequence in (1, 2, 3):
        await hub.emit(Notification(EventType.JOB_COMPLETED, {"sequence": sequence}))

    assert hub.dropped_events == 1
    assert (await asyncio.wait_for(waiter, timeout=2)).data == {"sequence": 2}
    assert (await stream.__anext__()).data == {"sequence": 3}
    await stream.aclose()
~~~

- [ ] **Step 2: Run the tests and verify they fail**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'opaque_event_id or drops_oldest' -q

Expected: FAIL because event_id and dropped_events are absent.

- [ ] **Step 3: Implement the smallest contract change**

~~~python
import uuid

@dataclass(frozen=True)
class Notification:
    type: EventType
    data: dict[str, Any]
    source: str = NOTIFICATION_SOURCE
    ts: int = field(default_factory=lambda: int(time.time()))
    version: int = NOTIFICATION_ENVELOPE_VERSION
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.data)
        return {
            "version": self.version,
            "event_id": self.event_id,
            "type": self.type.value,
            "event_type": self.type.value,
            "ts": self.ts,
            "source": self.source,
            "data": payload,
            "payload": payload,
        }


class NotificationHub:
    def __init__(self, *, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._subscribers = {}
        self._next_id = 0
        self._dropped_events = 0
        self._lock = asyncio.Lock()

    @property
    def dropped_events(self) -> int:
        return self._dropped_events

    async def emit(self, notification: Notification) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.values())
        for filters, queue in subscribers:
            if filters and notification.type not in filters:
                continue
            if queue.full():
                queue.get_nowait()
                self._dropped_events += 1
            queue.put_nowait(notification)
~~~

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'opaque_event_id or drops_oldest' -q

Expected: 2 passed.

- [ ] **Step 5: Commit**

~~~bash
git add src/orama_system/portal_notifications.py tests/test_portal_notifications.py
git commit -m "feat(g7): version notification event identities"
~~~

### Task 2: Publish Redacted Edge-Triggered Deltas

**Files:**
- Modify: src/orama_system/portal_notifications.py
- Modify: src/orama_system/portal_server.py:2608-2627
- Test: tests/test_portal_notifications.py

**Interfaces:**
- Consumes: NotificationHub.emit(notification) and the result of redact_portal_status_payload.
- Produces: PortalNotificationPublisher.publish(status: Mapping[str, Any]) -> list[Notification].

- [ ] **Step 1: Write the failing publisher test**

~~~python
@pytest.mark.asyncio
async def test_status_publisher_emits_only_redacted_edge_deltas():
    hub = NotificationHub()
    publisher = PortalNotificationPublisher(hub)
    first = {
        "services": {"perplexity_tools": {"ok": True}},
        "agents": [{"agent_id": "a1", "state": "running", "path": "/secret"}],
        "supervisor_jobs": [],
        "hardware_policy": {"ok": True},
    }
    second = {
        "services": {"perplexity_tools": {"ok": False}},
        "agents": [{"agent_id": "a1", "state": "done", "path": "/secret"}],
        "supervisor_jobs": [{"id": "j1", "status": "completed", "prompt": "secret"}],
        "hardware_policy": {"ok": False},
    }

    assert await publisher.publish(first) == []
    emitted = await publisher.publish(second)

    assert {item.type for item in emitted} == {
        EventType.AGENT_STATE_CHANGED,
        EventType.HARDWARE_STATUS_CHANGED,
        EventType.JOB_COMPLETED,
    }
    assert all("path" not in item.data and "prompt" not in item.data for item in emitted)
    assert await publisher.publish(second) == []
~~~

- [ ] **Step 2: Run the test and verify it fails**

Run: uv run --extra test pytest tests/test_portal_notifications.py::test_status_publisher_emits_only_redacted_edge_deltas -q

Expected: FAIL because PortalNotificationPublisher is undefined.

- [ ] **Step 3: Implement the publisher and call it after redaction**

~~~python
from collections.abc import Mapping

class PortalNotificationPublisher:
    def __init__(self, hub: NotificationHub) -> None:
        self._hub = hub
        self._previous: dict[str, Any] | None = None

    async def publish(self, status: Mapping[str, Any]) -> list[Notification]:
        current = {
            "agents": {
                str(item.get("agent_id", item.get("role", ""))): str(item.get("state", ""))
                for item in status.get("agents", [])
                if isinstance(item, Mapping)
            },
            "completed_jobs": {
                str(item.get("id", item.get("job_id", "")))
                for item in status.get("supervisor_jobs", [])
                if isinstance(item, Mapping) and str(item.get("status", "")).lower() == "completed"
            },
            "hardware_ok": bool(status.get("hardware_policy", {}).get("ok")),
        }
        previous = self._previous
        self._previous = current
        if previous is None:
            return []

        emitted: list[Notification] = []
        for agent_id, state in current["agents"].items():
            if previous["agents"].get(agent_id) != state:
                emitted.append(Notification(EventType.AGENT_STATE_CHANGED, {"agent_id": agent_id, "state": state}))
        if previous["hardware_ok"] != current["hardware_ok"]:
            emitted.append(Notification(EventType.HARDWARE_STATUS_CHANGED, {"ok": current["hardware_ok"]}))
        for job_id in current["completed_jobs"] - previous["completed_jobs"]:
            emitted.append(Notification(EventType.JOB_COMPLETED, {"job_id": job_id, "status": "completed"}))
        for notification in emitted:
            await self._hub.emit(notification)
        return emitted
~~~

In api_status, replace the direct return with:

~~~python
redacted_payload = redact_portal_status_payload(payload)
if notifications_enabled():
    await _notification_publisher.publish(redacted_payload)
return redacted_payload
~~~

- [ ] **Step 4: Run publisher and existing notification tests**

Run: uv run --extra test pytest tests/test_portal_notifications.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/orama_system/portal_notifications.py src/orama_system/portal_server.py tests/test_portal_notifications.py
git commit -m "feat(g7): emit redacted portal state deltas"
~~~

### Task 3: Add the Same-Origin Browser Session

**Files:**
- Modify: src/orama_system/portal_server.py:41-70,1421-1483
- Test: tests/test_portal_notifications.py

**Interfaces:**
- Consumes: CONTROL_PLANE_COOKIE, bearer_token_from_request, request_is_loopback, verify_control_plane_auth, and verify_lifecycle_origin.
- Produces: POST /api/notifications/session, a 15-minute host-only cookie bootstrap for a client that already has a bearer.

- [ ] **Step 1: Write failing session tests**

~~~python
def test_notification_session_requires_bearer_and_sets_scoped_cookie(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-notification-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    with TestClient(portal_server.app) as client:
        denied = client.post("/api/notifications/session")
        granted = client.post(
            "/api/notifications/session",
            headers={"Authorization": "Bearer test-notification-token"},
        )

    assert denied.status_code == 401
    assert granted.status_code == 204
    assert "orama_control_plane_token=" in granted.headers["set-cookie"]
    assert "HttpOnly" in granted.headers["set-cookie"]
    assert "SameSite=strict" in granted.headers["set-cookie"]
    assert "Path=/api/notifications" in granted.headers["set-cookie"]


def test_notification_session_rejects_cross_origin_bootstrap(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-notification-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    with TestClient(portal_server.app) as client:
        response = client.post(
            "/api/notifications/session",
            headers={
                "Authorization": "Bearer test-notification-token",
                "Origin": "https://attacker.invalid",
            },
        )
    assert response.status_code == 403
~~~

- [ ] **Step 2: Run the session tests and verify they fail**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k notification_session -q

Expected: FAIL with 404 because the session route does not exist.

- [ ] **Step 3: Implement the path-scoped cookie endpoint**

~~~python
from fastapi import Response
from utils.control_plane_auth import (
    CONTROL_PLANE_COOKIE,
    bearer_token_from_request,
    request_is_loopback,
    verify_control_plane_auth,
    verify_lifecycle_origin,
)

NOTIFICATION_SESSION_MAX_AGE_SECONDS = 900

@app.post("/api/notifications/session", status_code=204)
async def create_notification_session(request: Request, response: Response) -> None:
    verify_lifecycle_origin(request)
    if not request.headers.get("authorization", "").startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer authentication required")
    verify_control_plane_auth(request)
    response.set_cookie(
        key=CONTROL_PLANE_COOKIE,
        value=bearer_token_from_request(request),
        max_age=NOTIFICATION_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=not request_is_loopback(request),
        samesite="strict",
        path="/api/notifications",
    )
~~~

Do not inject this token into an HTML page or cpFetch. This endpoint is not a general login route.

- [ ] **Step 4: Prove the cookie can authenticate the stream**

~~~python
def test_cookie_authenticated_notification_stream(monkeypatch):
    monkeypatch.setenv("PORTAL_NOTIFICATIONS", "1")
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-notification-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    with TestClient(portal_server.app, base_url="http://localhost") as client:
        client.post(
            "/api/notifications/session",
            headers={"Authorization": "Bearer test-notification-token"},
        )
        with client.stream("GET", "/api/notifications/stream") as response:
            assert response.status_code == 200
~~~

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'notification_session or cookie_authenticated' -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/orama_system/portal_server.py tests/test_portal_notifications.py
git commit -m "feat(g7): add same-origin notification session"
~~~

### Task 4: Frame Typed SSE Events and Keep Replay Deferred

**Files:**
- Modify: src/orama_system/portal_server.py:1464-1483
- Test: tests/test_portal_notifications.py

**Interfaces:**
- Consumes: Notification.event_id, Notification.type.value, Notification.to_dict().
- Produces: format_notification_sse(notification: Notification) -> str and no-cache stream responses.

- [ ] **Step 1: Write failing stream-frame tests**

~~~python
def test_format_notification_sse_has_matching_id_event_and_json_payload():
    notification = Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"})
    frame = portal_server.format_notification_sse(notification)

    assert f"id: {notification.event_id}\n" in frame
    assert "event: job_completed\n" in frame
    assert f'"event_id":"{notification.event_id}"' in frame
    assert frame.endswith("\n\n")


def test_notification_stream_keeps_replay_out_of_scope(monkeypatch):
    monkeypatch.setenv("PORTAL_NOTIFICATIONS", "1")
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    with TestClient(portal_server.app) as client:
        with client.stream(
            "GET",
            "/api/notifications/stream",
            headers={"Last-Event-ID": "old-event"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-cache"
~~~

- [ ] **Step 2: Run the tests and verify they fail**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'format_notification_sse or replay_out_of_scope' -q

Expected: FAIL because the formatter and cache header are absent.

- [ ] **Step 3: Implement the formatter and headers**

~~~python
def format_notification_sse(notification: Notification) -> str:
    return (
        f"id: {notification.event_id}\n"
        f"event: {notification.type.value}\n"
        f"data: {json.dumps(notification.to_dict(), separators=(',', ':'))}\n\n"
    )

@app.get("/api/notifications/stream", response_class=StreamingResponse)
async def api_notifications_stream(request: Request, types: Optional[str] = None):
    # Retain the existing feature flag, auth check, and filter validation.
    async def generator():
        async for notification in _notification_hub.subscribe(filters):
            if await request.is_disconnected():
                break
            yield format_notification_sse(notification)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
~~~

Do not parse Last-Event-ID, emit retry, or persist events.

- [ ] **Step 4: Run all notification tests**

Run: uv run --extra test pytest tests/test_portal_notifications.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/orama_system/portal_server.py tests/test_portal_notifications.py
git commit -m "feat(g7): frame typed portal SSE events"
~~~

### Task 5: Document the Operator Contract and Run Acceptance Coverage

**Files:**
- Modify: docs/api-reference.md
- Modify: docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md:38-42,89,283-305,321-330
- Test: tests/test_portal_notifications.py

**Interfaces:**
- Consumes: the session route and stream behavior from Tasks 1-4.
- Produces: one discoverable operator contract and a complete MVP regression command.

- [ ] **Step 1: Write the two-second delivery acceptance test**

~~~python
@pytest.mark.asyncio
async def test_notification_delivery_is_typed_and_arrives_within_two_seconds():
    hub = NotificationHub()
    stream = hub.subscribe({EventType.JOB_COMPLETED})
    receive = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)

    notification = Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"})
    await hub.emit(notification)
    received = await asyncio.wait_for(receive, timeout=2)
    frame = portal_server.format_notification_sse(received)

    assert "event: job_completed" in frame
    assert f'"event_id":"{notification.event_id}"' in frame
    assert '"job_id":"redacted-job"' in frame
    await stream.aclose()
~~~

- [ ] **Step 2: Run the acceptance test**

Run: uv run --extra test pytest tests/test_portal_notifications.py::test_notification_delivery_is_typed_and_arrives_within_two_seconds -q

Expected: PASS after Tasks 1-4.

- [ ] **Step 3: Add the API-reference contract**

~~~markdown
### POST /api/notifications/session

Creates a 15-minute host-only browser session for the notification stream. Send an existing Authorization bearer credential from the same origin. The response sets an HttpOnly, SameSite=Strict cookie scoped to /api/notifications. A cross-origin request receives 403. Never put the token in a URL.

### GET /api/notifications/stream?types=job_completed,agent_state_changed

The endpoint is disabled until PORTAL_NOTIFICATIONS=1. It returns 404 while disabled, 401 without valid control-plane authentication, and 400 for an unknown event type. Each event has id, event, and versioned JSON data. Delivery is bounded and best effort; a slow subscriber loses its oldest queued event. On reconnect, fetch /api/status for a new redacted snapshot before resuming the stream. Last-Event-ID is not replayed in this MVP.
~~~

Update the G7 analysis to remove stale wording that says there is no subscription filter, name event_id, and identify the session cookie as a narrow stream bootstrap rather than a portal login.

- [ ] **Step 4: Run the full targeted validation**

Run: uv run --extra test pytest tests/test_portal_notifications.py tests/test_portal_mutating_route_auth.py tests/test_portal_dashboard.py tests/test_fleet_topology_api.py -q

Expected: PASS.

Run: git diff --check

Expected: no output.

- [ ] **Step 5: Commit**

~~~bash
git add docs/api-reference.md docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md tests/test_portal_notifications.py
git commit -m "docs(g7): document authenticated SSE operations"
~~~

## Plan Self-Review

### Spec coverage

| Requirement | Task |
| --- | --- |
| Standards-compliant FastAPI SSE framing | Task 4 |
| Browser auth and CSRF defaults | Task 3 |
| Bounded queue and backpressure semantics | Task 1 |
| Stable envelope conventions | Tasks 1 and 4 |
| Redacted production-style state deltas | Task 2 |
| Default-off, filter, auth, cleanup, and two-second acceptance | Tasks 1, 3, 4, and 5 |
| Future mesh compatibility without mesh or replay implementation | Tasks 1, 4, and 5 |

### Placeholder scan

Every task names exact files, interfaces, failing tests, commands, expected results, implementation code, and a commit boundary. The durable replay and mesh features are intentional exclusions, not incomplete implementation markers.

### Type consistency

Notification.event_id, NotificationHub.dropped_events, PortalNotificationPublisher.publish, and format_notification_sse are each defined before later tasks consume them. Notification.to_dict remains the only JSON-envelope constructor.
