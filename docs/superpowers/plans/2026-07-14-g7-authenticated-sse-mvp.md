<!-- /autoplan restore point: ~/.gstack/projects/diazMelgarejo-orama-system/main-autoplan-restore-20260715-185254.md -->
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
- Start later implementation from a fresh branch based on this integrated `main` head. Preserve the existing Perpetua-Tools vendor/ecc-tools and packages/agentic-stack changes.

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
4. The active [fleet-mesh index](../../next/fleet-mesh/README.md) owns the
   SOLO / PAIR / FLEET lineage and points to the root plans.
5. This plan, the [G7 analysis](../../next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md), and
   the [SSE production research](../references/2026-07-14-g7-sse-production-patterns.md)
   turn that authority into a narrow portal-local MVP.
6. Completed reports and historical ledgers are evidence only. They never
   override active documentation or live code.

### Node Map and Direct Edges

| Node | Direct links | Role in this implementation |
|---|---|---|
| Canonical architecture | [`docs/v2/`](../../v2/), [`43 GossipBus`](../../v2/43-gossipbus-mesh-transport.md) | Defines future event/mesh compatibility boundaries; records what stays deferred. |
| Canonical security | [`39 MAESTRO/OWASP`](../../v2/39-maestro-owasp-genai-reference.md) | Governs control-plane auth, redaction, browser exposure, and verification sources. |
| Fleet-mesh root | [active index](../../next/fleet-mesh/README.md), [mother plan](../../next/fleet-mesh/2026-07-08-self-healing-mesh-degradation-modes.md), [integration map](../../next/fleet-mesh/2026-07-10-phase-integration-map.md) | Explains why G7 follows the mesh lineage and how it relates to Phase 1-10+ work. |
| Mesh research | [OASN research](../../next/fleet-mesh/2026-07-10-oasn-p2p-architecture-research.md), [PT Phase 2 spec](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/PHASE-2-SPEC.md) | Supplies topology and membership context. It is not a mandate to implement P2P transport in G7. |
| G7 product scope | [G7 analysis](../../next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | Defines the Portal Notification Hub scope, default-off flag, and initial checklist. |
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
| docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md | Keep analysis aligned with shipped behavior. |

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

    await hub.emit(Notification(EventType.JOB_COMPLETED, {"sequence": "setup"}))
    assert (await stream.__anext__()).data == {"sequence": "setup"}

    for sequence in (1, 2, 3):
        await hub.emit(Notification(EventType.JOB_COMPLETED, {"sequence": sequence}))

    assert hub.dropped_events == 1
    assert (await stream.__anext__()).data == {"sequence": 2}
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

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

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
    # Route through the REAL redact_portal_status_payload(), not a hand-rolled
    # dict — a synthetic fixture using the wrong field name ("state" instead
    # of the real "status") or the wrong shape (a bare list instead of
    # redact_agents_payload()'s {"agents": [...], "count": n} dict wrapper)
    # would pass this test while the real diff loop silently no-ops in
    # production. This exact gap is why AGENT_STATE_CHANGED shipped dead.
    hub = NotificationHub()
    publisher = PortalNotificationPublisher(hub)
    first = redact_portal_status_payload({
        "services": {"perplexity_tools": {"ok": True}},
        "agents": [{"agent_id": "a1", "status": "running", "path": "/secret"}],
        "supervisor_jobs": [],
        "hardware_policy": {"ok": True},
    })
    second = redact_portal_status_payload({
        "services": {"perplexity_tools": {"ok": False}},
        "agents": [{"agent_id": "a1", "status": "done", "path": "/secret"}],
        "supervisor_jobs": [{"id": "j1", "status": "completed", "prompt": "secret"}],
        "hardware_policy": {"ok": False},
    })

    assert await publisher.publish(first) == []
    emitted = await publisher.publish(second)

    assert {item.type for item in emitted} == {
        EventType.AGENT_STATE_CHANGED,
        EventType.HARDWARE_STATUS_CHANGED,
        EventType.JOB_COMPLETED,
    }
    assert all("path" not in item.data and "prompt" not in item.data for item in emitted)
    assert await publisher.publish(second) == []


@pytest.mark.asyncio
async def test_api_status_publishes_only_the_redacted_payload(monkeypatch):
    raw_status = {
        "agents": [{"agent_id": "a1", "status": "done", "path": "/secret"}],
        "supervisor_jobs": [{"id": "j1", "status": "completed", "prompt": "secret"}],
    }
    redacted_status = redact_portal_status_payload(raw_status)
    seen_by_redactor = []
    seen_by_publisher = []

    class PublisherSpy:
        async def publish(self, status):
            seen_by_publisher.append(status)
            return []

    monkeypatch.setenv("PORTAL_NOTIFICATIONS", "1")
    monkeypatch.setattr(portal_server, "_build_portal_status_payload", lambda: raw_status)
    monkeypatch.setattr(
        portal_server,
        "redact_portal_status_payload",
        lambda status: seen_by_redactor.append(status) or redacted_status,
    )
    monkeypatch.setattr(portal_server, "_notification_publisher", PublisherSpy())

    result = await portal_server.api_status()

    assert seen_by_redactor == [raw_status]
    assert seen_by_publisher == [redacted_status]
    assert result == redacted_status
    # redact_agents_payload() wraps agents as {"agents": [...], "count": n} —
    # redact_portal_status_payload keeps that wrapper for "agents" but
    # unwraps "supervisor_jobs" back to a plain list before assignment
    # (redact_jobs_payload(...)["jobs"]). Index accordingly, or this
    # assertion raises KeyError: 0 on the dict.
    assert "path" not in seen_by_publisher[0]["agents"]["agents"][0]
    assert "prompt" not in seen_by_publisher[0]["supervisor_jobs"][0]
~~~

- [ ] **Step 2: Run the test and verify it fails**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'status_publisher or api_status_publishes' -q

Expected: FAIL because PortalNotificationPublisher is undefined.

- [ ] **Step 3: Implement the publisher and call it after redaction**

~~~python
from collections.abc import Mapping


def _unwrap_redacted_list(payload: Any, key: str) -> list[Any]:
    """Unwrap list payloads after redact_portal_status_payload (dict wrapper).

    Mirrors portal_server._unwrap_redacted_list — duplicated here (not
    imported) to avoid a circular import: portal_server.py imports
    NotificationHub from this module, so this module cannot import back
    from portal_server.py.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get(key, [])
        return items if isinstance(items, list) else []
    return []


class PortalNotificationPublisher:
    def __init__(self, hub: NotificationHub) -> None:
        self._hub = hub
        self._previous: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    async def publish(self, status: Mapping[str, Any]) -> list[Notification]:
        # redact_agents_payload() returns {"agents": [...], "count": n} (a dict,
        # not a list) and keys entries by "status", never "state" — read the
        # real field name through the same unwrap pattern portal_server.py uses
        # elsewhere, or every agent-state diff silently no-ops against real data.
        agents = _unwrap_redacted_list(status.get("agents"), "agents")
        current = {
            "agents": {
                str(item.get("agent_id", item.get("role", ""))): str(item.get("status", ""))
                for item in agents
                if isinstance(item, Mapping)
            },
            "completed_jobs": {
                str(item.get("id", item.get("job_id", "")))
                for item in status.get("supervisor_jobs", [])
                if isinstance(item, Mapping) and str(item.get("status", "")).lower() == "completed"
            },
            "hardware_ok": bool(status.get("hardware_policy", {}).get("ok")),
        }

        # Guard the read-modify-write: api_status() is called from at least 6
        # route handlers plus the dashboard's own poll timers, so concurrent
        # publish() calls can otherwise diff against out-of-order snapshots.
        async with self._lock:
            previous = self._previous
            self._previous = current
        if previous is None:
            return []

        emitted: list[Notification] = []
        for agent_id, state in current["agents"].items():
            if previous["agents"].get(agent_id) != state:
                emitted.append(Notification(EventType.AGENT_STATE_CHANGED, {"agent_id": agent_id, "status": state}))
        if previous["hardware_ok"] != current["hardware_ok"]:
            emitted.append(Notification(EventType.HARDWARE_STATUS_CHANGED, {"ok": current["hardware_ok"]}))
        for job_id in current["completed_jobs"] - previous["completed_jobs"]:
            emitted.append(Notification(EventType.JOB_COMPLETED, {"job_id": job_id, "status": "completed"}))
        for notification in emitted:
            try:
                await self._hub.emit(notification)
            except Exception:
                # /api/status is the primary status endpoint and has zero
                # current stream consumers — a shape drift in future event
                # types must not 500 the dashboard's core API over a
                # best-effort notification side channel.
                logger.exception("notification publish failed for %s", notification.type)
        return emitted
~~~

Also add `import logging` and `logger = logging.getLogger(__name__)` near the top of `portal_notifications.py` if not already present, and update the corresponding test (`test_status_publisher_emits_only_redacted_edge_deltas` in Step 1 above) to build its `first`/`second` fixtures through the real `redact_agents_payload()`/`redact_portal_status_payload()` — not hand-rolled dicts — so the test would have caught this exact bug.

Extract the current raw-status construction into `_build_portal_status_payload()` so
the route can be tested without reimplementing its monitor mocks. In `api_status`,
replace the direct return with:

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
- Produces: format_notification_sse(notification: Notification) -> str, periodic SSE
  keepalive comments, bounded ASGI send time, and no-cache stream responses.

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


@pytest.mark.asyncio
async def test_notification_sse_generator_keeps_idle_clients_alive_and_cleans_up(monkeypatch):
    monkeypatch.setattr(portal_server, "NOTIFICATION_SSE_KEEPALIVE_SECONDS", 0)
    request = AsyncMock()
    request.is_disconnected.return_value = False
    hub = NotificationHub()
    stream = portal_server.iter_notification_sse(request, hub, filters=None)

    assert await anext(stream) == ": keepalive\n\n"
    await stream.aclose()
    assert hub.subscriber_count == 0


@pytest.mark.asyncio
async def test_notification_stream_send_timeout_releases_subscription(monkeypatch):
    # Uses the REAL iter_notification_sse generator against a REAL hub, not a
    # bare one_event() stand-in — a fixture with no subscription logic can
    # never prove a subscription was released, which is the whole point of
    # this test's name. This is the exact test-fidelity gap that hid the
    # AGENT_STATE_CHANGED bug: assert against the real thing, not a fixture
    # shaped like it.
    monkeypatch.setattr(portal_server, "NOTIFICATION_SSE_SEND_TIMEOUT_SECONDS", 0)

    hub = NotificationHub()
    request = AsyncMock()
    request.is_disconnected.return_value = False
    generator = portal_server.iter_notification_sse(request, hub, filters=None)

    async def slow_send(message):
        if message["type"] == "http.response.body" and message.get("more_body"):
            await asyncio.Event().wait()

    response = portal_server.NotificationStreamingResponse(generator)
    task = asyncio.create_task(response.stream_response(slow_send))

    # async generators are lazy — hub.subscribe() only runs once
    # stream_response starts iterating self.body_iterator, not at
    # iter_notification_sse(...) call time. Emitting before the subscriber
    # is actually registered silently drops the notification (found by an
    # independent Codex GPT-5.5 pass — the original version of this test
    # emitted too early and would have hit the 15s keepalive path instead
    # of exercising the timeout/aclose() path at all).
    for _ in range(100):
        if hub.subscriber_count == 1:
            break
        await asyncio.sleep(0.01)
    assert hub.subscriber_count == 1

    await hub.emit(Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"}))
    await asyncio.wait_for(task, timeout=1)

    assert hub.subscriber_count == 0
~~~

- [ ] **Step 2: Run the tests and verify they fail**

Run: uv run --extra test pytest tests/test_portal_notifications.py -k 'format_notification_sse or replay_out_of_scope or keepalive or send_timeout' -q

Expected: FAIL because the formatter, keepalive loop, and bounded send adapter are absent.

- [ ] **Step 3: Implement the formatter and headers**

~~~python
def format_notification_sse(notification: Notification) -> str:
    return (
        f"id: {notification.event_id}\n"
        f"event: {notification.type.value}\n"
        f"data: {json.dumps(notification.to_dict(), separators=(',', ':'))}\n\n"
    )

NOTIFICATION_SSE_KEEPALIVE_SECONDS = 15
NOTIFICATION_SSE_SEND_TIMEOUT_SECONDS = 10


class NotificationStreamingResponse(StreamingResponse):
    """StreamingResponse with a bounded ASGI send for this local SSE route."""

    async def stream_response(self, send):
        await send({"type": "http.response.start", "status": self.status_code, "headers": self.raw_headers})
        try:
            async for chunk in self.body_iterator:
                if not isinstance(chunk, bytes):
                    chunk = chunk.encode(self.charset)
                try:
                    await asyncio.wait_for(
                        send({"type": "http.response.body", "body": chunk, "more_body": True}),
                        timeout=NOTIFICATION_SSE_SEND_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    break
        finally:
            # Breaking out of `async for` does NOT close the underlying async
            # generator — its own finally (hub._subscribers.pop(...)) only
            # runs on explicit aclose(). Without this, a slow/stalled client
            # leaks a live subscription on exactly the case this timeout
            # exists to handle. GC-based cleanup can't reliably await, so this
            # must be explicit, not implicit.
            aclose = getattr(self.body_iterator, "aclose", None)
            if aclose is not None:
                await aclose()
        await send({"type": "http.response.body", "body": b"", "more_body": False})


async def iter_notification_sse(request: Request, hub: NotificationHub, filters):
    stream = hub.subscribe(filters)
    pending = asyncio.create_task(stream.__anext__())
    try:
        while not await request.is_disconnected():
            done, _ = await asyncio.wait({pending}, timeout=NOTIFICATION_SSE_KEEPALIVE_SECONDS)
            if not done:
                yield ": keepalive\n\n"
                continue
            notification = pending.result()
            pending = asyncio.create_task(stream.__anext__())
            yield format_notification_sse(notification)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await stream.aclose()

@app.get("/api/notifications/stream", response_class=StreamingResponse)
async def api_notifications_stream(request: Request, types: Optional[str] = None):
    if not notifications_enabled():
        raise HTTPException(status_code=404, detail="Notifications are disabled")
    auth_failure = control_plane_auth_failure(request)
    if auth_failure is not None:
        return auth_failure
    try:
        filters = parse_event_types(types)
    except ValueError as exc:
        valid = ", ".join(sorted(item.value for item in EventType))
        raise HTTPException(
            status_code=400,
            detail=f"{exc} — valid types: {valid}",
        ) from exc

    return NotificationStreamingResponse(
        iter_notification_sse(request, _notification_hub, filters),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
~~~

**Known, inherited (not new) residual risk — not fixed here:** `cors_allow_origins()`
defaults to `["localhost:8002", "localhost:3000"]` with `allow_credentials=True`, and
`lifecycle_origin_allowed()` deliberately treats all loopback ports as mutually
trusted by design ("portal :8002 may accept POSTs from pages served on PT :8000 or
orama :8001" — `verify_lifecycle_origin` would NOT reject `localhost:3000`, it's
allow-listed on purpose). A co-resident local process on an allow-listed port is
therefore a credentialed reader of this stream once the session cookie is bootstrapped.
This is the same trust model every other lifecycle route in this codebase already
accepts (`POST /api/stop`, `/api/restart/*`, etc.) — it is the project's established
single-operator-LAN posture (`docs/v2/45-single-operator-lan-threat-model-descope.md`
D23: real trust boundary = administrative identity, not port count), not a gap this
plan introduces or should special-case-fix. Flagged for awareness; not an accepted
scope item.

The keepalive is an SSE comment, not an event or replay marker. The bounded send
adapter is route-local because `StreamingResponse` does not expose a send timeout.
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
- Modify: docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md:38-42,89,283-305,321-330
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

- [ ] **Step 3: Expose the drop counter (Decision Audit Trail #3 — was accepted, never coded until now)**

~~~python
# In api_status(), alongside the existing redacted-payload assembly:
redacted_payload["notification_delivery"] = {"dropped_events": _notification_hub.dropped_events}
~~~

- [ ] **Step 4: Add the API-reference contract, with a real client example**

~~~markdown
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
~~~

Update the G7 analysis to remove stale wording that says there is no subscription filter, name event_id, and identify the session cookie as a narrow stream bootstrap rather than a portal login.

- [ ] **Step 5: Run the full targeted validation**

Run: uv run --extra test pytest tests/test_portal_notifications.py tests/test_portal_mutating_route_auth.py tests/test_portal_dashboard.py tests/test_fleet_topology_api.py -q

Expected: PASS.

Run: git diff --check

Expected: no output.

- [ ] **Step 6: Commit**

~~~bash
git add docs/api-reference.md docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md tests/test_portal_notifications.py
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

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------------|-----------|-----------|----------|
| 1 | CEO | Approach A (ship as specified) over B (mesh-ready rewrite) or C (auth-only, no producer) | Mechanical | P1+P2 | B violates the plan's own Global Constraints and fleet-mesh authority order; C ships a stream that's authenticated but permanently silent | B, C |
| 2 | CEO | Producer-state durability across restarts — NOT in scope | Mechanical | Global Constraints | Persisting `PortalNotificationPublisher._previous` across restarts requires durable storage, explicitly barred by "no Redis, NATS, durable storage" | — |
| 3 | CEO | Expose `dropped_events` count in `/api/status` payload — ADDED to Task 5 scope | Mechanical | P2 (boil lakes) | In blast radius (same `api_status()` Task 2 already touches), <1 day effort, matches Engineering Preference "observability is not optional" | — |
| 4 | CEO | Rate-limit `POST /api/notifications/session` — deferred to TODOS.md | Mechanical | P3 (pragmatic) | Outside current blast radius (no rate-limit infra exists yet); endpoint already requires a valid bearer, so abuse surface is small | — |
| 5 | CEO | Corrected fabricated-adjacent citation in G7 analysis (`SECURITY.md §C` does not mandate notification auth) | Mechanical | Prime Directive 2 (every claim verifiable) | Verified via full-repo + all-branch + git-history search: phrase only ever appears as this citation and as the workstream's own open TODO, never as real §C content | — |
| 6 | CEO | Wire notification stream into React Command Center — deferred to TODOS.md, corrected from initial "reconcile two frontends" mis-scope | Mechanical | P3 (pragmatic) + scope discipline | `docs/v2/16-web-app-orchestration-plan.md` (RESOLVED 2026-06-14) already shipped the React-primary migration; `portal_server.py:3245` serves `web/dist` with legacy HTML as fallback only, not a parallel surface. Real follow-up is S/M (add EventSource client to Command Center), not 1-2 weeks. Still outside G7 MVP's Global Constraints (no UI work in this PR) | — |
| 7 | Eng | Actually applied the 3 accepted CEO-phase fixes into the plan's own TDD code blocks (Task 2: `status` field + `_unwrap_redacted_list()` + `asyncio.Lock`; Task 4: `aclose()` in `stream_response`'s `finally`) | Mechanical | Prime Directive 1 (zero silent failures) | Eng-phase dual voices found the Decision Audit Trail had logged these as "accepted" but they were never actually edited into the plan's code — an agentic worker executing the plan verbatim would still ship both bugs. Also rewrote the 2 test fixtures that hid the original bug to call the real `redact_portal_status_payload()` instead of hand-rolled dicts, and rewrote the misleadingly-named timeout-leak test to actually assert `subscriber_count == 0` | — |
| 8 | Eng | Added try/except around `hub.emit()` inside `PortalNotificationPublisher.publish()` | Mechanical | Prime Directive 1 + P5 (explicit) | `/api/status` is the primary status endpoint with zero current stream consumers — a future event-shape drift must not 500 the dashboard's core API over a best-effort notification side channel | — |
| 9 | Eng | Investigated then REJECTED a proposed origin-check fix for the CORS/session-cookie cross-origin-read finding | Mechanical (self-corrected) | Verify before applying | Initially proposed adding `verify_lifecycle_origin()` to the stream route, but that function deliberately treats all loopback ports as mutually trusted by design (documented: "portal :8002 may accept POSTs from pages served on PT :8000 or orama :8001") — it would NOT have rejected `localhost:3000`, and would have made the fix a no-op while claiming coverage. Reverted the route change and the test that would have asserted a 403 the real code can't produce. Documented as an inherited, accepted single-operator-LAN risk (matches `docs/v2/45` D23 precedent) instead of a fabricated fix | initial fix + its test |
| 10 | DX | Fixed Task 4's final route handler — was a comment (`# Retain the existing feature flag...`) referencing an undefined `filters` variable, not code | Mechanical | Prime Directive 1 + recurrence of Decision #7's pattern | Same failure class as the original `AGENT_STATE_CHANGED` bug: a decision/intent stated in prose instead of landed in code. An agentic worker executing the plan verbatim would hit a `NameError` on the first request. Now shows the literal `notifications_enabled()`/`control_plane_auth_failure()`/`parse_event_types()` calls inline | — |
| 11 | DX | Landed the `dropped_events` exposure (CEO Decision #3, accepted 2026-07-16, never coded until now) into Task 5 as a real code step | Mechanical | Prime Directive 1 + recurrence of Decision #7's pattern | Same recurring gap caught a 3rd time this review: a decision logged as "accepted into scope" in the audit trail is not the same as it landing in the plan's code. Added a real code snippet (`redacted_payload["notification_delivery"] = {"dropped_events": ...}`) instead of leaving it as a table row | — |
| 12 | DX | Rewrote Task 5's docs section with a copy-paste JS client example and explicit gotcha documentation (EventSource header limitation, named-event-listener requirement, cookie-expiry-has-no-renewal) | Mechanical | P1 (completeness) + this review's own stated bar ("wouldn't need to read the source") | Original docs draft was server-contract prose only, zero client code — broke `docs/api-reference.md`'s own established curl-example convention and left the two most common real-world SSE integration bugs (missing session bootstrap, listening on default `message` instead of typed `event:` name) completely undocumented | — |
| 13 | DX | Escape hatches for `queue_size`/keepalive/send-timeout/session-TTL constants — NOT added, left as hardcoded module constants | Mechanical | P3 (pragmatic) + acceptable MVP scope cut | Reasonable for a default-off MVP; noted as a stated exclusion rather than a silent gap so a future operator doesn't discover "no override exists" only by reading source | — |
| 14 | DX | React SPA wiring (Decision #6) — noted the "S/M effort" estimate is optimistic, no change to scope | Taste (informational) | — | DX review found `AppState`/`Shell.tsx` has no existing seam for push-based updates (poll-based cache shape only) — real effort is closer to a small design decision plus implementation, not just "add an EventSource client." Correctly stays deferred/out of scope; estimate revised at the final gate, not the code | — |
| 15 | Post-approval | Fixed Task 2's `test_api_status_publishes_only_the_redacted_payload` — `seen_by_publisher[0]["agents"][0]` raises `KeyError: 0` against the real (dict-wrapped) shape after routing through `redact_portal_status_payload()` per Decision #7 | Mechanical | Prime Directive 1 | Independent Codex GPT-5.5 (medium effort) final pass caught this: fixing the fixture's *input* to use the real redaction function (Decision #7) without also fixing the assertion's *indexing* left a broken test. `supervisor_jobs` doesn't need the same fix — `redact_portal_status_payload` explicitly unwraps it back to a plain list before assignment; only `agents` stays wrapped | — |
| 16 | Post-approval | Fixed Task 4's timeout test — it emitted before the async generator's subscriber had actually registered (lazy generator, `hub.subscribe()` doesn't run until first iteration), so the notification was silently dropped and the test would hit the 15s keepalive path instead of the timeout/`aclose()` path it claims to test | Mechanical | Prime Directive 1 | Same Codex GPT-5.5 pass. Fixed by starting `stream_response()` as a background task, polling `hub.subscriber_count == 1` before emitting, then awaiting the task with a timeout — the generator is now genuinely subscribed before the notification it's supposed to receive is sent | — |
| 17 | Post-approval | Clarified "5 real code/doc defects fixed" language — landed in the plan's own code blocks, NOT yet in repo source files | Mechanical | Precision | Same Codex pass correctly noted the plan is still a plan — `src/orama_system/portal_notifications.py` doesn't yet have `event_id`/`dropped_events`/`PortalNotificationPublisher` because Tasks 1-5 haven't been executed against real files. Expected and correct for a plan review; language in the Final Approval Gate section updated to say so explicitly | — |
| 18 | Post-approval | Noted (not fixed): `PortalNotificationPublisher`'s lock only guards the `_previous` swap, not the full diff-and-emit sequence — concurrent `api_status()` callers can still emit in a different order than they occurred | Taste (accepted tradeoff) | Global Constraints (best-effort delivery) | Fair architectural nuance from the same Codex pass. Holding the lock through emit would serialize notification delivery order but adds contention on the hot `/api/status` path for a feature the plan's own Global Constraints already describe as best-effort, not ordering-guaranteed. Left as documented, not fixed — revisit if a future consumer actually needs strict ordering | — |

## CEO Dual Voices — Consensus Table

```
CEO DUAL VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════
  Dimension                           Claude  Codex  Consensus
  ──────────────────────────────────── ─────── ─────── ─────────
  1. Premises valid?                   No      No     CONFIRMED (both: no proven need)
  2. Right problem to solve?           No      No     CONFIRMED (no consumer / wrong event source)
  3. Scope calibration correct?        Partial No     DISAGREE → TASTE DECISION
  4. Alternatives sufficiently explored?No     No     CONFIRMED (fetch-SSE, ETag-poll, webhooks, outbox all missed)
  5. Competitive/market risks covered? Yes     N/A    CONFIRMED (low external risk; real cost is opportunity cost)
  6. 6-month trajectory sound?         No      No     CONFIRMED (concrete regret scenarios named by both)
═══════════════════════════════════════════════════════════════
```

**Claude subagent (168K tokens, 31 tool uses, ground-truthed against source):** No client anywhere in the repo consumes this stream (grepped `web/src` for `EventSource`, zero hits). Two concrete, code-verified production bugs hidden by unfaithful test doubles: (a) `AGENT_STATE_CHANGED` is dead — `PortalNotificationPublisher` reads `item.get("state")` but real redacted data uses `"status"`, and `redact_agents_payload()` returns a dict not a list, so the diff loop silently skips everything; (b) the SSE send-timeout path abandons the generator without `aclose()`, leaking hub subscriptions on exactly the slow-client case it exists to handle. Plus a race in `_previous` (no lock across concurrent `/api/status` callers) and the now-corrected citation issue.

**Codex (gpt-5.6-terra, 36.6K tokens):** The producer is polling-triggered (fires only when `/api/status` is called), not push-triggered from real state-change sources — so the plan cannot actually deliver its own "2-second" latency claim regardless of implementation quality; the acceptance test only proves an in-memory queue can hand itself an object, not source-to-user latency. The browser-auth bootstrap is internally unresolved (if a safe authenticated browser session already exists, use it; if not, this invents a bespoke credential-transfer protocol). "v2-compatible" is asserted, not earned (random UUIDs, no ordering, no producer identity). Process-local fan-out is a hidden single-process commitment. Alternatives list (WebSocket/SSE/poll/Redis) omits ETag-polling, webhooks-to-existing-channels, and a domain-event/outbox boundary.

**Cross-model convergence:** Both independently concluded the plan ships real engineering effort (auth, framing, redaction-wiring) around a feature with no demonstrated consumer or need — this is not two models nitpicking style, it's the same structural critique from different entry points (Claude via "grep found zero callers," Codex via "the event-source design can't deliver its own SLA"). Neither model's finding depends on the other having found it first (dual voices ran independently). **This is the dominant finding for the Final Approval Gate** — flagged there as the plan's central open question, equivalent in weight to a User Challenge even though it targets a pre-existing plan rather than an in-conversation user directive.

## Eng Dual/Triple Voices — Consensus Table

```
ENG VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════
  Dimension                           Claude  Secondary  Consensus
  ──────────────────────────────────── ─────── ────────── ─────────
  1. Architecture sound?               Yes*    Yes*       CONFIRMED (*conditional on the 3 fixes actually landing)
  2. Test coverage sufficient?         No      No         CONFIRMED (fixture fidelity gaps found independently)
  3. Performance risks addressed?      Partial Partial    CONFIRMED (SPOF risk on /api/status found independently)
  4. Security threats covered?         Yes     No         DISAGREE → investigated, secondary's finding correct but pre-existing/inherited, not new
  5. Error paths handled?              No      —          Claude only: missing try/except around hub.emit()
  6. Deployment risk manageable?       Yes     Yes        CONFIRMED
═══════════════════════════════════════════════════════════════
```

**Claude subagent (primary, foreground, source-verified):** Confirmed the 4 CEO-accepted fixes need to land — and found the accepted fixes existed only in the Decision Audit Trail's prose, never in the plan's own TDD code blocks. Also found: `/api/status` has no error boundary around the new `publish()` call (SPOF risk for a zero-consumer feature), and the paired regression tests for the leak/lock fixes don't actually assert what their names claim.

**Secondary critic (cline CLI, `glm-5.2` — GPT-5.5 not resolvable under this provider, see note below):** Independently arrived at the same "accepted fixes never landed in the code" finding, plus flagged the CORS/session-cookie cross-origin-read surface (`allow_credentials=True` + `localhost:3000` allow-listed). Investigated and applied Decision #7-#8 fixes; investigated Decision #9's proposed fix and found it wouldn't work against this codebase's actual (deliberately permissive, documented) loopback-trust design — corrected rather than shipped.

**Model note:** the user requested this third voice run GPT-5.5 via the `cline` CLI; `cline-pass/gpt-5.5` and bare `gpt-5.5` both returned "model not found" (no models-listing tool available in this session to find the exact registered ID) — fell back to the tool's actual default (`cline-pass/glm-5.2`), which still surfaced 2 independently-confirmed findings plus 1 the primary voice hadn't named.

## DX Review — Findings

Single Claude subagent voice (source-verified against `portal_notifications.py`, `portal_server.py`, `control_plane_auth.py`, `web/src/api/client.ts`, `web/src/api/appState.ts`, `web/src/components/Shell.tsx`; confirmed zero `EventSource` references anywhere in `web/src` — this is from-scratch client integration, not wiring an existing stub).

**Time to hello-world: 7-8 non-trivial steps, 3 undocumented gotchas** — the two-step session-cookie-then-stream flow's rationale was never explained, named-event-listener requirement (`event: job_completed`, not the default `message` listener) was undocumented, and 15-minute cookie expiry has no renewal pattern. All three fixed in Decision #12's rewritten docs section with a full client example.

**Two recurrences of Decision #7's exact failure pattern**, caught independently: Task 4's final route handler was a comment referencing an undefined variable (Decision #10), and the `dropped_events` fix (accepted in CEO Decision #3) was never actually coded anywhere (Decision #11) — both landed as real code fixes, not just audit-trail rows this time.

**Correctly-scoped-out confirmed:** Decision #6 (React SPA wiring) — DX review found no existing seam in `AppState`/`Shell.tsx` for push-based updates (poll-based cache shape only), confirming this belongs in its own follow-up, though the "S/M effort" estimate is now understood to be optimistic (Decision #14).

**DX Scorecard (informal — single voice, no dual-critic split for this phase):**

| Dimension | Before this review | After fixes |
|---|---|---|
| Getting started (TTHW) | Undocumented, source-reading required | Documented, copy-paste client example |
| API/CLI naming | Dual-naming unexplained | One-line rationale added |
| Error messages | 2 of 4 paths dead-end | All 4 paths actionable |
| Documentation | Server-contract prose only | Contract + full client example + gotchas |
| Escape hatches | None, undocumented | None, explicitly scoped out (stated exclusion) |

## Final Approval Gate — APPROVED (2026-07-16, confirmed after independent Codex GPT-5.5 pass)

`/autoplan` review complete: CEO (dual voices) → Eng (triple voices) → DX (single voice)
→ independent Codex GPT-5.5 (medium effort) final pass, which caught 2 more real bugs
(both in tests this review itself introduced) after the plan was already marked
approved — fixed as Decisions #15-16. 18 decisions logged total.

**Precision note (Decision #17):** "defects fixed" throughout this review means
**landed in this plan document's own TDD code blocks**, not yet applied to the
actual repository source files — `src/orama_system/portal_notifications.py` and
`src/orama_system/portal_server.py` do not yet contain `event_id`,
`PortalNotificationPublisher`, the session route, or typed SSE framing, because
Tasks 1-5 have not been executed against real files. That is expected and correct
for a plan review, not a discrepancy — flagged explicitly per Decision #17 so
"fixed" isn't misread as "already shipped."

The dominant strategic finding — this plan ships real infrastructure with no wired
consumer yet — was steelmanned and accepted as a defensible backend-first
sequencing choice, not a blocker. User approved as-is.

**Ready for implementation** (`superpowers:subagent-driven-development` or
`superpowers:executing-plans` per the plan's header). All Decision Audit Trail
fixes are now present in the plan's own TDD code blocks — an agentic worker
executing Tasks 1-5 verbatim against this plan will ship the corrected version,
not the original bugs, subject to the one accepted tradeoff in Decision #18.

NO UNRESOLVED DECISIONS
