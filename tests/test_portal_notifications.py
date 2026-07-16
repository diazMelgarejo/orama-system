#!/usr/bin/env python3
"""G7 notification hub and SSE route security invariants."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server
from orama_system.portal_notifications import (
    NOTIFICATION_SOURCE,
    NOTIFICATION_V2_ALIGNMENT,
    EventType,
    Notification,
    NotificationHub,
    PortalNotificationPublisher,
    parse_event_types,
)
from utils.control_plane_auth import redact_portal_status_payload


def test_notifications_stream_is_default_off(monkeypatch):
    monkeypatch.delenv("PORTAL_NOTIFICATIONS", raising=False)
    with TestClient(portal_server.app) as client:
        response = client.get("/api/notifications/stream")
    assert response.status_code == 404


def test_notifications_stream_requires_auth_when_enforced(monkeypatch):
    monkeypatch.setenv("PORTAL_NOTIFICATIONS", "1")
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-notification-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        response = client.get("/api/notifications/stream")
    assert response.status_code == 401


def test_parse_event_types_rejects_unknown_type():
    with pytest.raises(ValueError):
        parse_event_types("job_completed,unknown")


def test_parse_event_types_accepts_comma_separated_values():
    assert parse_event_types("job_completed, agent_state_changed") == {
        EventType.JOB_COMPLETED,
        EventType.AGENT_STATE_CHANGED,
    }


@pytest.mark.asyncio
async def test_notification_hub_filters_and_cleans_up_subscriber():
    hub = NotificationHub(queue_size=2)
    received: list[Notification] = []

    async def collect_one() -> None:
        async for item in hub.subscribe({EventType.JOB_COMPLETED}):
            received.append(item)
            break

    task = asyncio.create_task(collect_one())
    await asyncio.sleep(0)
    assert hub.subscriber_count == 1

    await hub.emit(Notification(EventType.AGENT_STATE_CHANGED, {"state": "ignored"}))
    await asyncio.sleep(0)
    assert received == []

    expected = Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"})
    await hub.emit(expected)
    await asyncio.wait_for(task, timeout=2)

    assert received == [expected]
    await asyncio.sleep(0)
    assert hub.subscriber_count == 0


@pytest.mark.asyncio
async def test_notification_envelope_has_adapter_aliases():
    notification = Notification(EventType.JOB_COMPLETED, {"job_id": "redacted-job"})
    payload = notification.to_dict()
    assert payload["version"] == 1
    assert payload["type"] == "job_completed"
    assert payload["event_type"] == "job_completed"
    assert payload["source"] == NOTIFICATION_SOURCE
    assert payload["data"] == {"job_id": "redacted-job"}
    assert payload["payload"] == {"job_id": "redacted-job"}


def test_notification_scaffold_declares_future_v2_alignment_without_enabling_mesh():
    """Keep G7 MVP compatible with v2 plans without silently growing scope."""
    assert NOTIFICATION_V2_ALIGNMENT == {
        "v2_kernel": "docs/v2/01-kernel-spec.md#perpetuastate-pydantic-v2",
        "v2_1_mesh": "docs/v2/43-gossipbus-mesh-transport.md",
        "v2_5_safety": "docs/v2/03-safety-v2.5.md",
    }


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

    # subscribe() is an async generator -- the queue/subscriber registration
    # only runs once it's first iterated, not at hub.subscribe() call time.
    # Emitting before that point is a silent no-op (no subscriber exists
    # yet), and the later __anext__() then blocks forever on an empty
    # queue. Found by actually running this test during implementation --
    # no prior review phase (CEO/Eng/DX/independent Codex pass) executed
    # pytest against this file, only read the plan's source. Kick off the
    # first receive as a background task and yield once so the generator
    # runs up to `await queue.get()` (which registers the subscriber)
    # before the first emit.
    first = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)

    await hub.emit(Notification(EventType.JOB_COMPLETED, {"sequence": "setup"}))
    assert (await first).data == {"sequence": "setup"}

    for sequence in (1, 2, 3):
        await hub.emit(Notification(EventType.JOB_COMPLETED, {"sequence": sequence}))

    assert hub.dropped_events == 1
    assert (await stream.__anext__()).data == {"sequence": 2}
    assert (await stream.__anext__()).data == {"sequence": 3}
    await stream.aclose()


@pytest.mark.asyncio
async def test_status_publisher_emits_only_redacted_edge_deltas():
    # Route through the REAL redact_portal_status_payload(), not a hand-rolled
    # dict — a synthetic fixture using the wrong field name ("state" instead
    # of the real "status") or the wrong shape (a bare list instead of
    # redact_agents_payload()'s {"agents": [...], "count": n} dict wrapper)
    # would pass this test while the real diff loop silently no-ops in
    # production.
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

    async def _fake_build_payload():
        # _build_portal_status_payload() is async in the real implementation
        # (it awaits network probes) -- the replacement must be too, or
        # `await portal_server._build_portal_status_payload()` inside
        # api_status() raises TypeError on a plain value.
        return raw_status

    monkeypatch.setenv("PORTAL_NOTIFICATIONS", "1")
    monkeypatch.setattr(portal_server, "_build_portal_status_payload", _fake_build_payload)
    monkeypatch.setattr(
        portal_server,
        "redact_portal_status_payload",
        lambda status: seen_by_redactor.append(status) or redacted_status,
    )
    monkeypatch.setattr(portal_server, "_notification_publisher", PublisherSpy())

    result = await portal_server.api_status()

    assert seen_by_redactor == [raw_status]
    assert seen_by_publisher == [redacted_status]
    # notification_delivery is added to the returned payload AFTER the
    # publisher sees it, so the publisher's view stays exactly the redacted
    # snapshot while the HTTP response carries the drop counter too.
    assert result == {**redacted_status, "notification_delivery": {"dropped_events": 0}}
    # redact_agents_payload() wraps agents as {"agents": [...], "count": n} —
    # redact_portal_status_payload keeps that wrapper for "agents" but
    # unwraps "supervisor_jobs" back to a plain list before assignment
    # (redact_jobs_payload(...)["jobs"]). Index accordingly, or this
    # assertion raises KeyError: 0 on the dict.
    assert "path" not in seen_by_publisher[0]["agents"]["agents"][0]
    assert "prompt" not in seen_by_publisher[0]["supervisor_jobs"][0]