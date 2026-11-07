"""Tests for lan_peer_inbox_check --peer win: did a drop from the Windows peer arrive on the Mac, and is it intact."""
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


def _drop(inbox: Path, name: str, source: str, body: bytes = b"hello", sha: str | None = None) -> None:
    """Write an inbox file and its sidecar; *sha* overrides the recorded hash to simulate corruption."""
    (inbox / name).write_bytes(body)
    meta = {"filename": name, "source": source, "received_at": 1_700_000_000, "sha256": sha or hashlib.sha256(body).hexdigest()}
    (inbox / f"{name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _run(capsys, *argv: str) -> tuple[int, str]:
    """Run main() with *argv* and return its exit code and stdout."""
    code = chk.main(list(argv))
    return code, capsys.readouterr().out


def test_win_token_matching_is_standalone_and_source_decides() -> None:
    """The win token must stand alone (window is not Windows) and the sidecar source beats the file name."""
    assert chk.is_peer_drop("win-canary.md", {}, "win")
    assert chk.is_peer_drop("note.md", {"source": "Win"}, "win")
    assert not chk.is_peer_drop("window-report.md", {"source": "winter-bot"}, "win")
    assert not chk.is_peer_drop("win-named-but-mac-sent.md", {"source": "mac"}, "win")
    assert chk.is_peer_drop("mac-note.md", {}, "mac")


def test_mac_default_is_unchanged(inbox, capsys) -> None:
    """Without --peer the check still reports Mac drops, so the Windows launcher behaves as before."""
    _drop(inbox, "m1.md", "mac-agent")
    _drop(inbox, "w1.md", "win-agent")
    code, out = _run(capsys, "--no-record", "--json")
    data = json.loads(out)
    assert code == 0 and data["mac_drops"] == 1 and "win_drops" not in data


def test_peer_win_counts_only_windows_drops(inbox, capsys) -> None:
    """--peer win reports Windows drops only and words the line for Windows."""
    _drop(inbox, "m1.md", "mac-agent")
    _drop(inbox, "w1.md", "win-agent")
    _drop(inbox, "w2.md", "win-claude-code")
    code, out = _run(capsys, "--peer", "win", "--no-record", "--json")
    data = json.loads(out)
    assert code == 0 and data["win_drops"] == 2 and "mac_drops" not in data
    code, out = _run(capsys, "--peer", "win", "--no-record")
    assert code == 0 and "Windows drops: 2 total" in out and "Mac drops" not in out


def test_peer_win_flags_integrity_failure_only_for_windows_drops(inbox, capsys) -> None:
    """A corrupt Windows drop exits 2 and is never recorded; a corrupt Mac drop is not this peer's problem."""
    _drop(inbox, "m1.md", "mac-agent", sha="0" * 64)
    _drop(inbox, "w1.md", "win-agent")
    code, out = _run(capsys, "--peer", "win", "--no-record")
    assert code == 0, out
    _drop(inbox, "w2.md", "win-agent", sha="1" * 64)
    code, out = _run(capsys, "--peer", "win")
    assert code == 2 and "integrity FAIL" in out and "w2.md" in out
    state = inbox.parent / chk.state_name("win")
    assert not state.exists(), "an integrity failure must not be recorded as seen"


def test_state_files_are_separate_per_peer(inbox, capsys) -> None:
    """Each peer keeps its own already-seen file so one check never hides the other's new drops."""
    _drop(inbox, "m1.md", "mac-agent")
    _drop(inbox, "w1.md", "win-agent")
    _run(capsys, "--peer", "win")
    _run(capsys)
    assert chk.state_name("win") != chk.state_name("mac")
    assert (inbox.parent / chk.state_name("win")).is_file() and (inbox.parent / chk.state_name("mac")).is_file()
    _drop(inbox, "w2.md", "win-agent", body=b"second")
    _, out = _run(capsys, "--peer", "win", "--no-record")
    assert "1 new" in out


def test_unknown_peer_is_rejected() -> None:
    """Only mac and win are valid peers; anything else is an argument error, never a silent default."""
    with pytest.raises(SystemExit) as raised:
        chk.main(["--peer", "linux"])
    assert raised.value.code == 2
