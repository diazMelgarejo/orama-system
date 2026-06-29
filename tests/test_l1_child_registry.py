"""Unit tests for l1_child_registry (ingredients, no portal wire)."""
from orama_system.l1_child_registry import (
    get_session,
    list_pids,
    mark_stopped,
    register_child,
    reset_registry,
)


def setup_function() -> None:
    reset_registry()


def test_register_and_list_pids() -> None:
    register_child("sess-1", 1001, "codex")
    register_child("sess-1", 1002, "cursor")
    assert list_pids("sess-1") == [1001, 1002]
    session = get_session("sess-1")
    assert session is not None
    assert session.status == "running"


def test_mark_stopped() -> None:
    register_child("sess-2", 2001, "hermes")
    assert mark_stopped("sess-2") is True
    session = get_session("sess-2")
    assert session is not None
    assert session.status == "stopped"
    assert session.stopped_at is not None


def test_unknown_session() -> None:
    assert list_pids("missing") == []
    assert mark_stopped("missing") is False
