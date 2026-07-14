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
    parse_event_types,
)


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