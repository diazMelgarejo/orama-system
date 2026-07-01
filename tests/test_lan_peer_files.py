"""Tests for lan_peer_files.py."""
from __future__ import annotations

import pytest

from orama_system.lan_peer_files import (
    inbox_dir,
    list_inbox,
    list_outbox,
    read_outbox_file,
    remove_outbox_file,
    read_inbox_file,
    sanitize_filename,
    write_inbox_file,
    write_outbox_file,
)


@pytest.fixture
def inbox_root(monkeypatch, tmp_path):
    root = tmp_path / "lan_peer"
    monkeypatch.setattr("orama_system.lan_peer_files.lan_peer_state_dir", lambda: root)
    return root


def test_sanitize_rejects_path_traversal():
    with pytest.raises(ValueError):
        sanitize_filename("../evil.md")


def test_write_list_read_roundtrip(inbox_root):
    record = write_inbox_file(
        "2026-06-28-mac-hypothesis.md",
        "# Hypothesis\n\nMac reviews literature.\n",
        assignee="mac",
        topic="autoresearch/hypothesis",
        source="win",
        fanout_id="batch-001",
    )
    assert record["filename"] == "2026-06-28-mac-hypothesis.md"
    files = list_inbox()
    assert len(files) == 1
    assert files[0]["topic"] == "autoresearch/hypothesis"
    body, meta = read_inbox_file("2026-06-28-mac-hypothesis.md")
    assert "Hypothesis" in body
    assert meta["assignee"] == "mac"
    assert (inbox_root / "inbox" / "2026-06-28-mac-hypothesis.md").is_file()


def test_write_outbox_records_delivery_failure(inbox_root):
    record = write_outbox_file(
        "win-task.md",
        "# Win task\n",
        assignee="win",
        topic="smoke",
        source="mac",
        fanout_id="batch-002",
        peer_ip="10.0.0.50",
        portal_port=8002,
        error="HTTP 500",
    )

    assert record["filename"] == "win-task.md"
    assert record["peer_ip"] == "10.0.0.50"
    assert record["portal_port"] == "8002"
    assert record["last_error"] == "HTTP 500"
    assert (inbox_root / "outbox" / "win-task.md").is_file()
    assert (inbox_root / "outbox" / "win-task.md.meta.json").is_file()
    assert list_outbox()[0]["filename"] == "win-task.md"
    body, meta = read_outbox_file("win-task.md")
    assert "Win task" in body
    assert meta["peer_ip"] == "10.0.0.50"
    remove_outbox_file("win-task.md")
    assert list_outbox() == []
