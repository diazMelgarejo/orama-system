"""Tests for lan_peer_inbox_check: did a drop from the Mac arrive, and is it intact."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"))

import lan_peer_inbox_check as chk  # noqa: E402


@pytest.fixture()
def inbox(tmp_path, monkeypatch) -> Path:
    """Point HOME at a temp dir and return the (created) LAN peer inbox directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".openclaw" / "state" / "lan_peer" / "inbox"
    path.mkdir(parents=True)
    return path


def _drop(inbox: Path, name: str, body: bytes = b"hello", source: str = "mac-agent", sha: str | None = None) -> None:
    """Write an inbox file and its sidecar; *sha* overrides the recorded hash to simulate corruption."""
    (inbox / name).write_bytes(body)
    meta = {"filename": name, "source": source, "received_at": 1_700_000_000, "sha256": sha or hashlib.sha256(body).hexdigest()}
    (inbox / f"{name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _run(capsys, *argv: str) -> tuple[int, str]:
    """Run main() with *argv* and return its exit code and stdout."""
    code = chk.main(list(argv))
    return code, capsys.readouterr().out


def test_mac_token_matching_is_standalone() -> None:
    """The token must stand alone, so machine or macro are not Mac drops."""
    assert chk.is_mac_drop("mac-canary-1.md", {})
    assert chk.is_mac_drop("note.md", {"source": "Mac"})
    assert not chk.is_mac_drop("machine-report.md", {"source": "macro-bot"})
    assert not chk.is_mac_drop("win-note.md", {"source": "win"})
    assert not chk.is_mac_drop("mac-named-by-windows.md", {"source": "win"})
    assert chk.is_mac_drop("mac-no-source.md", {})


def test_empty_inbox_reports_none(inbox, capsys) -> None:
    """With no Mac drop the status is none and the exit code is 0."""
    code, out = _run(capsys, "--json")
    assert code == 0
    assert json.loads(out)["status"] == "none"


def test_first_check_is_a_baseline_then_a_new_drop_is_reported(inbox, capsys) -> None:
    """First check records a baseline; a later drop is reported new; an unchanged inbox is quiet."""
    _drop(inbox, "mac-a.md")
    assert json.loads(_run(capsys, "--json")[1])["status"] == "baseline"
    assert json.loads(_run(capsys, "--json")[1])["status"] == "quiet"
    _drop(inbox, "mac-b.md", body=b"second")
    result = json.loads(_run(capsys, "--json")[1])
    assert result["status"] == "new"
    assert result["new"] == ["mac-b.md"]
    assert result["newest"]["integrity"] == "ok"


def test_non_mac_drops_are_ignored(inbox, capsys) -> None:
    """A drop from another source never counts as a Mac drop."""
    _drop(inbox, "win-note.md", source="win")
    assert json.loads(_run(capsys, "--json")[1])["status"] == "none"


def test_hash_mismatch_fails_with_exit_code_2_and_is_not_recorded(inbox, capsys) -> None:
    """A body that does not match its recorded sha256 is an integrity failure and is not marked seen."""
    _drop(inbox, "mac-bad.md", sha="0" * 64)
    code, out = _run(capsys, "--json")
    assert code == 2
    assert json.loads(out)["status"] == "integrity-fail"
    assert not (inbox.parent / chk.STATE_NAME).exists()


def test_changed_content_under_the_same_name_is_new_again(inbox, capsys) -> None:
    """Replacing a file with different bytes is reported as new, not hidden by the name."""
    _drop(inbox, "mac-a.md")
    _run(capsys, "--json")
    _drop(inbox, "mac-a.md", body=b"changed")
    assert json.loads(_run(capsys, "--json")[1])["status"] == "new"


def test_no_record_leaves_no_state(inbox, capsys) -> None:
    """--no-record never writes the already-seen file."""
    _drop(inbox, "mac-a.md")
    _run(capsys, "--json", "--no-record")
    assert not (inbox.parent / chk.STATE_NAME).exists()


def test_human_output_names_the_newest_drop(inbox, capsys) -> None:
    """The plain-text line carries the count, the newest name and the integrity result."""
    _drop(inbox, "mac-a.md")
    out = _run(capsys)[1]
    assert "mac-a.md" in out and "integrity ok" in out


def test_unreadable_or_missing_drop_is_skipped_without_crashing(inbox, capsys, monkeypatch) -> None:
    """An unreadable or removed drop raises OSError on read_bytes/stat and is safely skipped."""
    _drop(inbox, "mac-good.md")
    _drop(inbox, "mac-broken.md")

    real_read_bytes = Path.read_bytes

    def flaky_read(self):
        if self.name == "mac-broken.md":
            raise OSError("simulated permission denied or disappearing file")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read)
    code, out = _run(capsys, "--json")
    assert code == 0
    data = json.loads(out)
    assert data["status"] == "baseline"
    assert data["mac_drops"] == 1
    assert data["newest"]["name"] == "mac-good.md"
