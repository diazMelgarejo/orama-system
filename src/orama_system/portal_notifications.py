"""Default-off portal notification scaffolding for the G7 MVP.

The hub is intentionally local-process only: no durability, no LAN fan-out, no
webhooks. Producers must redact payloads before calling emit(). The envelope is
shaped to be a future adapter source for docs/v2/43 GossipBus mesh transport,
but this module must not implement mesh replication, durable ingest, or v2.5
safety enforcement.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


NOTIFICATION_ENVELOPE_VERSION = 1
NOTIFICATION_SOURCE = "orama-portal"
NOTIFICATION_V2_ALIGNMENT = {
    "v2_kernel": "docs/v2/01-kernel-spec.md#perpetuastate-pydantic-v2",
    "v2_1_mesh": "docs/v2/43-gossipbus-mesh-transport.md",
    "v2_5_safety": "docs/v2/03-safety-v2.5.md",
}


class EventType(str, Enum):
    AGENT_STATE_CHANGED = "agent_state_changed"
    FLEET_TOPOLOGY_CHANGED = "fleet_topology_changed"
    HARDWARE_STATUS_CHANGED = "hardware_status_changed"
    JOB_COMPLETED = "job_completed"
    PHASE_TRANSITION = "phase_transition"


@dataclass(frozen=True)
class Notification:
    """Versioned SSE envelope. data/payload aliases are kept for adapters."""

    type: EventType
    data: dict[str, Any]
    source: str = NOTIFICATION_SOURCE
    ts: int = field(default_factory=lambda: int(time.time()))
    version: int = NOTIFICATION_ENVELOPE_VERSION
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.data)
        event_type = self.type.value
        return {
            "version": self.version,
            "event_id": self.event_id,
            "type": event_type,
            "event_type": event_type,
            "ts": self.ts,
            "source": self.source,
            "data": payload,
            "payload": payload,
        }


class NotificationHub:
    """Bounded per-subscriber FIFO hub with disconnect cleanup."""

    def __init__(self, *, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._subscribers: dict[int, tuple[set[EventType], asyncio.Queue[Notification]]] = {}
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
        """Best-effort emit. Slow subscribers drop oldest before receiving new."""
        async with self._lock:
            subscribers = list(self._subscribers.values())
        for filters, queue in subscribers:
            if filters and notification.type not in filters:
                continue
            if queue.full():
                try:
                    queue.get_nowait()
                    self._dropped_events += 1
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(notification)

    async def subscribe(self, filters: set[EventType] | None = None) -> AsyncIterator[Notification]:
        queue: asyncio.Queue[Notification] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            subscriber_id = self._next_id
            self._next_id += 1
            self._subscribers[subscriber_id] = (set(filters or set()), queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                self._subscribers.pop(subscriber_id, None)


def _unwrap_redacted_list(payload: Any, key: str) -> list[Any]:
    """Unwrap list payloads after redact_portal_status_payload (dict wrapper).

    Mirrors portal_server._unwrap_redacted_list — duplicated here (not
    imported) to avoid a circular import: portal_server.py imports
    NotificationHub/PortalNotificationPublisher from this module, so this
    module cannot import back from portal_server.py.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get(key, [])
        return items if isinstance(items, list) else []
    return []


class PortalNotificationPublisher:
    """Diffs successive redacted /api/status snapshots into typed Notifications."""

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


def notifications_enabled() -> bool:
    """Feature flag. Default off until G7 MVP wiring is fully verified."""
    import os

    return os.getenv("PORTAL_NOTIFICATIONS", "").strip().lower() in {"1", "true", "yes", "on"}


def parse_event_types(raw: str | None) -> set[EventType]:
    if not raw:
        return set()
    parsed: set[EventType] = set()
    valid = {item.value: item for item in EventType}
    for part in raw.split(","):
        name = part.strip()
        if not name:
            continue
        if name not in valid:
            raise ValueError(f"unknown notification type: {name}")
        parsed.add(valid[name])
    return parsed