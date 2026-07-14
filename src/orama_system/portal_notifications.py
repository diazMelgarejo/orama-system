"""Default-off portal notification scaffolding for the G7 MVP.

The hub is intentionally local-process only: no durability, no LAN fan-out, no
webhooks. Producers must redact payloads before calling emit().
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    source: str = "orama-portal"
    ts: int = field(default_factory=lambda: int(time.time()))
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.data)
        event_type = self.type.value
        return {
            "version": self.version,
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
        self._lock = asyncio.Lock()

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