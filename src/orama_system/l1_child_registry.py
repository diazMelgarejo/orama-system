"""In-memory registry of L1 child processes for tiered killswitch (ingredients / pre-P5).

Portal /api/l1/stop uses this to SIGTERM children before optional full /api/stop NUCLEAR.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

_REGISTRY: dict[str, "L1Session"] = {}


@dataclass
class L1Child:
    pid: int
    executor_id: str
    started_at: float = field(default_factory=time.time)


@dataclass
class L1Session:
    session_id: str
    children: list[L1Child] = field(default_factory=list)
    status: str = "running"
    stopped_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "children": [
                {
                    "pid": c.pid,
                    "executor_id": c.executor_id,
                    "started_at": c.started_at,
                }
                for c in self.children
            ],
            "stopped_at": self.stopped_at,
        }


def register_child(session_id: str, pid: int, executor_id: str) -> None:
    session = _REGISTRY.setdefault(session_id, L1Session(session_id=session_id))
    session.children.append(L1Child(pid=pid, executor_id=executor_id))


def get_session(session_id: str) -> L1Session | None:
    return _REGISTRY.get(session_id)


def list_pids(session_id: str) -> list[int]:
    session = _REGISTRY.get(session_id)
    if not session:
        return []
    return [c.pid for c in session.children]


def mark_stopped(session_id: str) -> bool:
    session = _REGISTRY.get(session_id)
    if not session:
        return False
    session.status = "stopped"
    session.stopped_at = time.time()
    return True


def clear_session(session_id: str) -> None:
    _REGISTRY.pop(session_id, None)


def reset_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
