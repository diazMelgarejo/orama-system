"""Outbox delivery states for lan_peer_assign (queued / sent / delivered)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography", reason="cryptography needed to mint throwaway test certs")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import peer_tls_fixtures as fx  # noqa: E402

import lan_peer_assign as lpa  # noqa: E402
import peer_tls  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Isolated environment: clean peer-trust variables, a temporary home and a synthetic control-plane token; returns the home path."""
    for var in (
        "PEER_CA_FILE", "PEER_PINNED_FINGERPRINTS", "ORAMA_CONTROL_PLANE_TOKEN_PEER",
        "ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "PT_CONTROL_PLANE_TOKEN", "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "PT_HOME",
    ):
        monkeypatch.delenv(var, raising=False)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", fx.SYNTHETIC_TOKEN)
    peer_tls.clear_cache()
    return home


@pytest.fixture
def tls_peer(env, monkeypatch, tmp_path):
    """Run a verifying TLS peer signed by a throwaway CA and point peer trust at that CA; stops the server afterwards."""
    ca = fx.make_ca()
    srv = fx.start_server(tmp_path, fx.make_leaf(issuer=ca))
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", ca[1])))
    yield srv
    srv.stop()


def _queue(name, port, host="localhost"):
    """Queue a small outbox file aimed at the given peer host and port."""
    from orama_system.lan_peer_files import write_outbox_file

    return write_outbox_file(name, "# body\n", assignee="win", topic="t", source="mac",
                             peer_ip=host, portal_port=port, error="seed")


def _meta(name):
    """Read an outbox item's metadata sidecar as a dict."""
    from orama_system.lan_peer_files import _meta_path, outbox_dir

    return json.loads(_meta_path(outbox_dir() / name).read_text(encoding="utf-8"))


def _flush(capsys, *extra):
    """Run flush-outbox with a short timeout and return (exit code, parsed stdout JSON, stderr)."""
    rc = lpa.main(["flush-outbox", "--timeout", "3", *extra])
    cap = capsys.readouterr()
    return rc, json.loads(cap.out), cap.err


def test_unreachable_peer_stays_queued_never_delivered(env, capsys):
    """An unreachable peer leaves the item queued with an error and the file kept, never delivered."""
    _queue("a.md", 1, host=fx.LOOPBACK_V4)
    rc, out, err = _flush(capsys, "--strict")
    assert rc == 1 and out["delivered"] == 0 and out["still_queued"] == 1
    assert "delivered 0, still queued 1" in err
    m = _meta("a.md")
    assert m["state"] == "queued" and m["last_error"]
    assert (Path(env) / ".openclaw/state/lan_peer/outbox/a.md").is_file()


def test_authenticated_ok_is_delivered_and_removed_by_default(tls_peer, capsys):
    """An authenticated ok reply marks the item delivered, removes it by default, and sends the token only over verified https."""
    _queue("b.md", tls_peer.port)
    rc, out, err = _flush(capsys, "--strict")
    assert rc == 0 and out["results"][0]["status"] == "delivered"
    assert "delivered 1, still queued 0" in err
    # duplicate-safety: one authenticated listing GET precedes the POST
    assert set(tls_peer.auth_headers) == {f"Bearer {fx.SYNTHETIC_TOKEN}"}
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "POST"]
    from orama_system.lan_peer_files import list_outbox
    assert list_outbox() == []


def test_keep_delivered_records_state(tls_peer, capsys):
    """With --keep-delivered the item is kept in the delivered state and a later default flush does not resend it."""
    _queue("c.md", tls_peer.port)
    _flush(capsys, "--keep-delivered")
    m = _meta("c.md")
    assert m["state"] == "delivered" and m["delivered_at"] and m["last_error"] == ""
    # delivered entries are not resent by a default flush
    n = len(tls_peer.seen)
    rc, out, _ = _flush(capsys)
    assert out["results"] == [] and len(tls_peer.seen) == n


def test_response_without_ok_true_is_sent_not_delivered(tls_peer, capsys):
    """A 2xx reply without ok true is recorded as sent, not delivered."""
    tls_peer.reply = {"ok": False}
    _queue("d.md", tls_peer.port)
    rc, out, err = _flush(capsys, "--strict")
    assert rc == 1 and out["results"][0]["status"] == "sent"
    assert _meta("d.md")["state"] == "sent"
    assert "delivered 0, still queued 1" in err


def test_http_peer_is_never_delivered_and_token_withheld(env, monkeypatch, tmp_path, capsys):
    """A plain http peer is never marked delivered and no token is sent to it."""
    monkeypatch.delenv("PEER_PORTAL_TLS_ENABLED", raising=False)
    srv = fx.start_server(tmp_path, tls=False)
    try:
        _queue("e.md", srv.port, host=fx.LOOPBACK_V4)
        rc, out, _ = _flush(capsys, "--strict")
        assert rc == 1 and out["results"][0]["status"] == "sent"
        assert srv.auth_headers == []
        assert _meta("e.md")["state"] == "sent"
    finally:
        srv.stop()


def test_verification_failure_keeps_queued_and_sends_no_token(env, monkeypatch, tmp_path, capsys):
    """A TLS verification failure leaves the item queued and sends no token."""
    srv = fx.start_server(tmp_path, fx.make_leaf(issuer=fx.make_ca()))
    try:
        monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
        monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "x.pem", fx.make_ca("x")[1])))
        _queue("f.md", srv.port)
        rc, out, _ = _flush(capsys, "--strict")
        assert rc == 1 and _meta("f.md")["state"] == "queued"
        assert "CERTIFICATE_VERIFY_FAILED" in _meta("f.md")["last_error"]
        assert srv.seen == []
    finally:
        srv.stop()


def test_only_flushes_selected(tls_peer, capsys):
    """--only flushes just the named items (by filename or stem)."""
    for n in ("g1.md", "g2.md", "g3.md"):
        _queue(n, tls_peer.port)
    rc, out, err = _flush(capsys, "--only", "g2.md", "--only", "g3")
    assert sorted(r["filename"] for r in out["results"]) == ["g2.md", "g3.md"]
    from orama_system.lan_peer_files import list_outbox
    assert [i["filename"] for i in list_outbox()] == ["g1.md"]
    assert _meta("g1.md").get("state", "queued") == "queued"


def test_state_filter(tls_peer, capsys):
    """--state flushes only items in the requested state."""
    tls_peer.reply = {"ok": False}
    _queue("h1.md", tls_peer.port)
    _queue("h2.md", tls_peer.port)
    _flush(capsys, "--only", "h1.md")  # h1 -> sent
    tls_peer.reply = {"ok": True}
    rc, out, _ = _flush(capsys, "--state", "sent")
    assert [r["filename"] for r in out["results"]] == ["h1.md"] and out["delivered"] == 1
    assert _meta("h2.md").get("state", "queued") == "queued"


def test_old_meta_without_state_reads_as_queued_and_status_is_readonly(env, capsys):
    """Metadata without a state reads as queued and outbox-status does not modify it or leak the token."""
    _queue("old.md", 1, host=fx.LOOPBACK_V4)
    from orama_system.lan_peer_files import _meta_path, outbox_dir

    mp = _meta_path(outbox_dir() / "old.md")
    meta = json.loads(mp.read_text(encoding="utf-8"))
    meta.pop("state", None)
    mp.write_text(json.dumps(meta), encoding="utf-8")
    before = mp.read_bytes()
    assert lpa.main(["outbox-status"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["items"][0]["state"] == "queued" and data["counts"] == {"queued": 1, "sent": 0, "delivered": 0}
    assert mp.read_bytes() == before
    assert fx.SYNTHETIC_TOKEN not in out


def test_drop_failure_records_queued_state(env, capsys, tmp_path):
    """A failed peer drop is queued locally with state queued and exit code 2."""
    f = tmp_path / "t.md"
    f.write_text("x", encoding="utf-8")
    rc = lpa.main(["drop", "--peer", "--peer-ip", fx.LOOPBACK_V4, "--portal-port", "1",
                   "--file", str(f), "--timeout", "2"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["state"] == "queued"
    assert _meta("t.md")["state"] == "queued"
