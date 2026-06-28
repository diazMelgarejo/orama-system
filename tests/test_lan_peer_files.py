"""Tests for lan_peer_files.py."""
from __future__ import annotations

import pytest

from orama_system.lan_peer_files import (
    inbox_dir,
    list_inbox,
    read_inbox_file,
    sanitize_filename,
    write_inbox_file,
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
