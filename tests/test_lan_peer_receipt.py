"""Tests for the local, read-only lan_peer_assign receipt command."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"))

import lan_peer_assign as lpa  # noqa: E402


@pytest.fixture
def inbox(monkeypatch, tmp_path):
    """Point the LAN peer state directory at a temporary path and return its inbox directory."""
    root = tmp_path / "lan_peer"
    monkeypatch.setattr("orama_system.lan_peer_files.lan_peer_state_dir", lambda: root)
    return root / "inbox"


def _receipt(capsys, *argv):
    """Run the receipt command and return (exit code, stdout, stderr)."""
    rc = lpa.main(["receipt", *argv])
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def test_receipt_reports_exact_bytes_and_lf_hash(inbox, capsys):
    """Receipt reports the stored byte count, raw sha256 and LF-normalised sha256 of a CRLF file."""
    inbox.mkdir(parents=True)
    raw = b"# t\r\nline\r\n"
    (inbox / "canary.md").write_bytes(raw)
    rc, out, _ = _receipt(capsys, "canary.md", "--json")
    data = json.loads(out)
    assert rc == 0
    assert data["filename"] == "canary.md"
    assert data["bytes"] == len(raw)
    assert data["sha256"] == hashlib.sha256(raw).hexdigest()
    assert data["sha256_lf"] == hashlib.sha256(b"# t\nline\n").hexdigest()
    assert data["sha256"] != data["sha256_lf"]
    assert data["host"] == socket.gethostname()
    assert data["received_utc"].endswith("Z")


def test_receipt_uses_inbox_metadata_time(inbox, capsys):
    """Receipt takes received_utc from the inbox metadata when recorded."""
    from orama_system.lan_peer_files import write_inbox_file

    write_inbox_file("meta.md", "hello\n", assignee="win")
    meta = inbox / "meta.md.meta.json"
    rec = json.loads(meta.read_text(encoding="utf-8"))
    rec["received_at"] = 1700000000
    meta.write_text(json.dumps(rec), encoding="utf-8")
    rc, out, _ = _receipt(capsys, "meta.md", "--json")
    assert rc == 0
    assert json.loads(out)["received_utc"] == "2023-11-14T22:13:20Z"


def test_receipt_falls_back_to_mtime_without_metadata(inbox, capsys):
    """Receipt falls back to the file mtime when there is no metadata."""
    inbox.mkdir(parents=True)
    path = inbox / "bare.md"
    path.write_bytes(b"x")
    os.utime(path, (1700000000, 1700000000))
    rc, out, _ = _receipt(capsys, "bare.md", "--json")
    assert rc == 0
    assert json.loads(out)["received_utc"] == "2023-11-14T22:13:20Z"


def test_receipt_plain_output_lists_fields(inbox, capsys):
    """Plain output lists every receipt field."""
    inbox.mkdir(parents=True)
    (inbox / "p.md").write_bytes(b"abc")
    rc, out, _ = _receipt(capsys, "p.md")
    assert rc == 0
    for key in ("filename:", "bytes: 3", "sha256:", "sha256_lf:", "received_utc:", "host:"):
        assert key in out


def test_receipt_missing_file_exits_2(inbox, capsys):
    """A missing inbox file exits 2 with a not-found message and no output."""
    inbox.mkdir(parents=True)
    rc, out, err = _receipt(capsys, "nope.md")
    assert rc == 2
    assert out == ""
    assert "not found" in err


@pytest.mark.parametrize("bad", ["../evil.md", "a/b.md", "..\\evil.md","x.json"])
def test_receipt_rejects_unsafe_names(inbox, capsys, bad):
    """Unsafe names (traversal, separators, json) are rejected with exit 2."""
    inbox.mkdir(parents=True)
    rc, out, _ = _receipt(capsys, bad)
    assert rc == 2
    assert out == ""
