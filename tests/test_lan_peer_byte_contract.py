"""Cross-platform byte preservation for peer-file persistence and dispatch."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, IO

import pytest

from orama_system import lan_peer_files as files

SCRIPTS = Path(__file__).resolve().parents[1] / "bin/orama-system/skills/hermes-harness/scripts"
sys.path.insert(0, str(SCRIPTS))
import lan_peer_assign as assign  # noqa: E402


@pytest.fixture
def peer_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep peer-file tests outside the operator's real inbox and outbox."""
    monkeypatch.setattr(files, "lan_peer_state_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def windows_text_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Emulate Windows implicit text newline translation on any test host."""
    original_open = Path.open

    def windows_text_open(
        path: Path, mode: str = "r", *args: Any, **kwargs: Any
    ) -> IO[Any]:
        """Translate implicit text newlines as Windows does, not binary writes."""
        if "b" not in mode and "w" in mode and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", windows_text_open)


@pytest.mark.unit
@pytest.mark.parametrize("folder", ["inbox", "outbox"])
@pytest.mark.parametrize(
    "body", ["", "line\n", "line\r\n", "line\r", "caf\u00e9\n\n", "\ufeffline\n"]
)
def test_peer_storage_preserves_utf8_bytes_on_windows(
    peer_state: Path, windows_text_mode: None, folder: str, body: str
) -> None:
    """Keep exact body bytes and verifiable LF-only sidecars on every host."""
    writer = files.write_inbox_file if folder == "inbox" else files.write_outbox_file
    record = writer("canary.md", body)
    raw = (peer_state / folder / "canary.md").read_bytes()
    assert raw == body.encode("utf-8")
    assert record["bytes"] == len(raw)
    sidecar = (peer_state / folder / "canary.md.meta.json").read_bytes()
    assert b"\r\n" not in sidecar
    assert not sidecar.startswith(b"\xef\xbb\xbf")
    metadata = json.loads(sidecar)
    assert metadata["bytes"] == len(raw)
    assert record["sha256"] == metadata["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.unit
def test_delivery_state_update_keeps_sidecar_lf_only(
    peer_state: Path, windows_text_mode: None
) -> None:
    """Delivery bookkeeping preserves the cross-platform sidecar representation."""
    files.write_outbox_file("canary.md", "line\n")
    assign._set_state("canary.md", "delivered", evidence="test receipt")
    sidecar = (peer_state / "outbox/canary.md.meta.json").read_bytes()
    assert b"\r\n" not in sidecar
    assert json.loads(sidecar)["state"] == "delivered"


@pytest.mark.unit
@pytest.mark.parametrize("folder", ["inbox", "outbox"])
def test_peer_read_preserves_existing_crlf_and_trailing_newlines(
    peer_state: Path, folder: str
) -> None:
    """Reading a legacy record must not normalize bytes before a later resend."""
    path = peer_state / folder / "legacy.md"
    path.parent.mkdir()
    raw = b"first\r\nsecond\r\n\r\n"
    path.write_bytes(raw)
    reader = files.read_inbox_file if folder == "inbox" else files.read_outbox_file
    body, _ = reader(path.name)
    assert body.encode("utf-8") == raw


@pytest.mark.unit
def test_drop_preserves_source_crlf_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI sends the source text exactly, rather than normalizing newlines."""
    path = tmp_path / "source.md"
    raw = b"first\r\nsecond\r\n"
    path.write_bytes(raw)
    captured: dict[str, Any] = {}

    def capture_request(
        method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 30
    ) -> dict[str, bool]:
        """Capture the transport body without accessing any real peer or token."""
        assert payload is not None
        captured.update(payload)
        return {"ok": True}

    monkeypatch.setattr(assign, "_http_json", capture_request)
    assert assign.main([
        "drop", "--peer", "--peer-ip", "192.0.2.1", "--portal-port", "8443",
        "--file", str(path),
    ]) == 0
    assert captured["body"].encode("utf-8") == raw
