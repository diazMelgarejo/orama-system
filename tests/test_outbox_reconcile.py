"""outbox-resolve / outbox-resubmit and duplicate-safe flush (Mac plan rules)."""
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
        "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "PT_HOME", "PEER_PORTAL_TLS_ENABLED",
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


def _queue(name, port, host=fx.LOOPBACK_V4, body="# body\n"):
    """Queue an outbox file with the given body aimed at the given peer host and port."""
    from orama_system.lan_peer_files import write_outbox_file

    return write_outbox_file(name, body, assignee="win", topic="t", source="mac",
                             peer_ip=host, portal_port=port, error="seed")


def _meta(name):
    """Read an outbox item's metadata sidecar as a dict."""
    from orama_system.lan_peer_files import _meta_path, outbox_dir

    return json.loads(_meta_path(outbox_dir() / name).read_text(encoding="utf-8"))


def _run(capsys, *argv):
    """Run a lan_peer_assign command and return (exit code, parsed stdout JSON, stderr)."""
    rc = lpa.main(list(argv))
    cap = capsys.readouterr()
    return rc, json.loads(cap.out), cap.err


def _outbox_has(name):
    """Return whether the named file is still in the outbox."""
    from orama_system.lan_peer_files import list_outbox

    return name in [i["filename"] for i in list_outbox()]


# ---- outbox-resolve ---------------------------------------------------------

def test_resolve_requires_only(env):
    """outbox-resolve exits when no --only item is given."""
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resolve", "--state", "delivered", "--evidence", "x"])


def test_resolve_records_evidence_without_network(env, capsys):
    """Resolve records sanitised evidence and a resolved time without any network call and keeps the file."""
    _queue("a.md", 1)
    dirty = "receiver" + chr(27) + "[31m reported" + chr(13) + chr(10) + "receipt" + chr(0) + " ok"
    rc, out, _ = _run(capsys, "outbox-resolve", "--only", "a.md", "--state", "delivered",
                      "--evidence", dirty)
    assert rc == 0 and out["ok"] is True
    m = _meta("a.md")
    assert m["state"] == "delivered" and m["resolved_at"].endswith("Z")
    assert m["evidence"] == "receiver [31m reported receipt ok"
    assert not any(ord(c) < 32 or 0x7F <= ord(c) <= 0x9F for c in m["evidence"])
    assert _outbox_has("a.md")  # evidence recorded, file kept


def test_resolve_truncates_evidence(env, capsys):
    """Resolve truncates evidence to 500 characters."""
    _queue("b.md", 1)
    _run(capsys, "outbox-resolve", "--only", "b.md", "--state", "superseded", "--evidence", "e" * 5000)
    m = _meta("b.md")
    assert m["state"] == "superseded" and len(m["evidence"]) == 500


def test_resolve_rejects_credentials_and_changes_nothing(env):
    """Resolve rejects evidence that looks like a credential and leaves the item unchanged."""
    _queue("c.md", 1)
    for bad in ("Bearer abcdef123456", "token=abc123", f"seen {fx.SYNTHETIC_TOKEN} here"):
        with pytest.raises(SystemExit):
            lpa.main(["outbox-resolve", "--only", "c.md", "--state", "delivered", "--evidence", bad])
    assert _meta("c.md").get("state", "queued") == "queued"


def test_resolve_unmatched_only_is_atomic(env):
    """Resolve with an unmatched --only name fails and changes none of the items."""
    _queue("d.md", 1)
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resolve", "--only", "d.md", "--only", "nope.md", "--state", "delivered",
                  "--evidence", "x"])
    assert _meta("d.md").get("state", "queued") == "queued"


def test_resolve_has_no_credential_options(env):
    """outbox-resolve accepts no credential options."""
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resolve", "--only", "x.md", "--state", "delivered", "--evidence", "x",
                  "--token", "abc"])


def test_resolved_items_are_not_flushed_and_counted(env, capsys):
    """Resolved items are skipped by flush and counted by outbox-status."""
    _queue("e.md", 1)
    _run(capsys, "outbox-resolve", "--only", "e.md", "--state", "superseded", "--evidence", "replaced")
    rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "2")
    assert out["results"] == []
    rc, out, _ = _run(capsys, "outbox-status")
    assert out["items"][0]["state"] == "superseded" and out["counts"]["superseded"] == 1


# ---- outbox-resubmit --------------------------------------------------------

def test_resubmit_requires_explicit_only_and_destination(env):
    """outbox-resubmit requires --only, a destination host and a destination port."""
    _queue("f.md", 1)
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resubmit", "--peer-ip", "localhost", "--portal-port", "1"])
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resubmit", "--only", "f.md", "--portal-port", "1"])
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resubmit", "--only", "f.md", "--peer-ip", "localhost"])


def test_resubmit_sends_same_name_keeps_origin_and_records_history(tls_peer, capsys):
    """Resubmit sends the same filename, preserves the original destination, records history and marks the item delivered."""
    _queue("g.md", 1, host=fx.LOOPBACK_V4)
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "g.md", "--peer-ip", "localhost",
                      "--portal-port", str(tls_peer.port), "--timeout", "3")
    assert rc == 0 and out["results"][0]["status"] == "delivered"
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "POST"]
    assert tls_peer.auth_headers == [f"Bearer {fx.SYNTHETIC_TOKEN}"] * 2
    m = _meta("g.md")
    assert m["peer_ip"] == fx.LOOPBACK_V4 and m["portal_port"] == "1"  # origin preserved
    h = m["history"][-1]
    assert h["from"] == {"peer_ip": fx.LOOPBACK_V4, "portal_port": "1"}
    assert h["to"] == {"peer_ip": "localhost", "portal_port": str(tls_peer.port)}
    assert h["result"] == "delivered" and h["at"].endswith("Z")
    assert m["state"] == "delivered" and _outbox_has("g.md")


def test_resubmit_failure_keeps_item_and_file(env, capsys):
    """A failed resubmit keeps the item queued with an error, history and the file."""
    _queue("h.md", 1)
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "h.md", "--peer-ip", fx.LOOPBACK_V4,
                      "--portal-port", "1", "--timeout", "2")
    assert rc == 1 and out["results"][0]["status"] == "error"
    m = _meta("h.md")
    assert m["state"] == "queued" and m["last_error"] and m["history"][-1]["result"].startswith("error")
    assert _outbox_has("h.md")


def test_resubmit_over_http_withholds_token(env, tmp_path, capsys):
    """Resubmit over plain http sends no token and records sent, not delivered."""
    srv = fx.start_server(tmp_path, tls=False)
    try:
        _queue("i.md", 1)
        rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "i.md", "--peer-ip", fx.LOOPBACK_V4,
                          "--portal-port", str(srv.port), "--timeout", "3")
        assert rc == 1 and out["results"][0]["status"] == "sent"
        assert srv.auth_headers == []
        assert _meta("i.md")["state"] == "sent"
    finally:
        srv.stop()


def test_resubmit_skips_already_resolved(tls_peer, capsys):
    """Resubmit skips an item that was already resolved and sends nothing."""
    _queue("j.md", 1)
    _run(capsys, "outbox-resolve", "--only", "j.md", "--state", "delivered", "--evidence", "seen")
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "j.md", "--peer-ip", "localhost",
                      "--portal-port", str(tls_peer.port))
    assert rc == 0 and out["results"][0]["status"] == "skipped" and tls_peer.seen == []


# ---- duplicate safety -------------------------------------------------------

def test_resubmit_does_not_send_when_peer_already_has_file(tls_peer, capsys):
    """Resubmit does not POST when the peer already has the same content; it records verified evidence instead."""
    body = "# body\n"
    _queue("k.md", 1, body=body)
    tls_peer.reply = {"ok": True, "files": [{"filename": "k.md", "bytes": len(body)}]}
    tls_peer.replies["/api/peer-inbox/k.md"] = {"ok": True, "body": body}
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "k.md", "--peer-ip", "localhost",
                      "--portal-port", str(tls_peer.port), "--timeout", "3")
    assert rc == 0 and out["results"][0]["status"] == "delivered"
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "GET"]  # listing + content check, never POSTed
    assert tls_peer.seen[1][1] == "/api/peer-inbox/k.md"
    m = _meta("k.md")
    assert m["state"] == "delivered" and "sha256 verified" in m["evidence"]
    assert m["listed_size"] == len(body) and m["size_matches"] is True
    assert _outbox_has("k.md")


def test_flush_does_not_send_duplicate_and_keeps_evidence(tls_peer, capsys):
    """Flush does not send a duplicate when the peer already has the same content and keeps the evidence."""
    _queue("l.md", tls_peer.port, host="localhost")
    tls_peer.reply = {"ok": True, "files": [{"filename": "l.md", "bytes": 7}]}
    tls_peer.replies["/api/peer-inbox/l.md"] = {"ok": True, "body": "# body\n"}
    rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "3", "--strict")
    assert rc == 0 and "sha256 verified" in out["results"][0]["detail"]
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "GET"]
    assert _meta("l.md")["state"] == "delivered" and _outbox_has("l.md")


def test_listing_failure_blocks_send_and_keeps_item(env, monkeypatch, tmp_path, capsys):
    """A failed duplicate-check listing blocks the send and keeps the item."""
    srv = fx.start_server(tmp_path, fx.make_leaf(issuer=fx.make_ca()))
    try:
        monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
        monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "x.pem", fx.make_ca("x")[1])))
        _queue("m.md", srv.port, host="localhost")
        rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "3", "--strict")
        assert rc == 1 and "duplicate check failed" in out["results"][0]["detail"]
        assert srv.seen == [] and _outbox_has("m.md")
    finally:
        srv.stop()


# ---- review-fix regressions -------------------------------------------------

def test_same_name_different_size_is_collision_not_delivered(tls_peer, capsys):
    """Same name with a different size is a collision: nothing is sent and the item stays queued."""
    _queue("n.md", 1, body="# body\nline2\n")
    tls_peer.reply = {"ok": True, "files": [{"filename": "n.md", "bytes": 999}]}
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "n.md", "--peer-ip", "localhost",
                      "--portal-port", str(tls_peer.port), "--timeout", "3")
    assert rc == 1 and out["results"][0]["status"] == "error"
    assert "name collision" in out["results"][0]["detail"]
    assert [m for m, _, _ in tls_peer.seen] == ["GET"]  # never POSTed
    m = _meta("n.md")
    assert m["state"] == "queued" and m["size_matches"] is False
    assert _outbox_has("n.md")


def test_crlf_receiver_size_counts_as_same_content(tls_peer, capsys):
    """A receiver size equal to the CRLF encoding of the body counts as the same content."""
    body = "# body\nline2\n"
    _queue("o.md", 1, body=body)
    crlf_len = len(body.replace("\n", "\r\n").encode("utf-8"))
    tls_peer.reply = {"ok": True, "files": [{"filename": "o.md", "bytes": crlf_len}]}
    tls_peer.replies["/api/peer-inbox/o.md"] = {"ok": True, "body": body.replace("\n", "\r\n")}
    rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "o.md", "--peer-ip", "localhost",
                      "--portal-port", str(tls_peer.port), "--timeout", "3")
    assert rc == 0 and out["results"][0]["status"] == "delivered"
    assert _meta("o.md")["size_matches"] is True


def test_evidence_filter_sees_through_control_characters(env):
    """The evidence filter detects credentials hidden behind control characters."""
    for bad in ("Bearer" + chr(0) + "eyJhbGciOiJIUzI1NiJ9.x", "api_key" + chr(0) + "= sk-live-abc",
                "Bearer" + chr(27) + "[0m abc123"):
        with pytest.raises(SystemExit):
            lpa._clean_evidence(bad)


def test_resubmit_rejects_out_of_range_port(env):
    """Resubmit rejects a destination port outside the valid range."""
    _queue("p.md", 1)
    with pytest.raises(SystemExit):
        lpa.main(["outbox-resubmit", "--only", "p.md", "--peer-ip", "localhost",
                  "--portal-port", "70000"])


def test_flush_skips_item_resubmitted_elsewhere(env, capsys):
    """Flush skips an item whose last history hop went to another destination."""
    _queue("q.md", 1)
    lpa._set_state("q.md", "sent", history=[
        {"from": {"peer_ip": fx.LOOPBACK_V4, "portal_port": "1"},
         "to": {"peer_ip": "localhost", "portal_port": "2"}, "at": "x", "result": "sent"}])
    rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "2")
    assert out["results"][0]["status"] == "skipped" and "--only" in out["results"][0]["detail"]


def test_urlopen_kwargs_bad_port_is_trust_error(env, monkeypatch, tmp_path):
    """A bad port in a trust-configured URL raises PeerTrustError."""
    monkeypatch.setenv("PEER_CA_FILE", str(tmp_path / "ca.pem"))
    with pytest.raises(peer_tls.PeerTrustError):
        peer_tls.urlopen_kwargs("https://host.invalid:70000/x")


# ---- round-2 review fixes (content proof, redirect skip, host typo, Cf chars) -

def _resubmit(capsys, name, port):
    """Run outbox-resubmit for one item to the localhost TLS peer on a port."""
    return _run(capsys, "outbox-resubmit", "--only", name, "--peer-ip", "localhost",
                "--portal-port", str(port), "--timeout", "3")


def test_equal_size_different_content_is_not_delivered(tls_peer, capsys):
    """Equal size but different content is not delivered and nothing is sent."""
    new_body, old_body = "date: 2026-10-25\n", "date: 2026-10-24\n"
    assert len(new_body) == len(old_body)
    _queue("r.md", 1, body=new_body)
    tls_peer.reply = {"ok": True, "files": [{"filename": "r.md", "bytes": len(old_body)}]}
    tls_peer.replies["/api/peer-inbox/r.md"] = {"ok": True, "body": old_body}
    rc, out, _ = _resubmit(capsys, "r.md", tls_peer.port)
    assert rc == 1 and out["results"][0]["status"] == "error"
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "GET"]  # never POSTed
    m = _meta("r.md")
    assert m["state"] == "queued" and m["content_verified"] is False
    assert "different or unverifiable content; operator must resolve" in m["last_error"]
    assert _outbox_has("r.md")


def test_equal_size_unfetchable_content_stays_queued(tls_peer, capsys):
    """Equal size with unfetchable content stays queued and nothing is sent."""
    body = "# body\n"
    _queue("s.md", 1, body=body)
    tls_peer.reply = {"ok": True, "files": [{"filename": "s.md", "bytes": len(body)}]}
    # content endpoint answers without a body -> unverifiable
    tls_peer.replies["/api/peer-inbox/s.md"] = {"ok": True}
    rc, out, _ = _resubmit(capsys, "s.md", tls_peer.port)
    assert rc == 1 and out["results"][0]["status"] == "error"
    m = _meta("s.md")
    assert m["state"] == "queued" and "unverifiable content" in m["last_error"]
    assert "POST" not in [x for x, _, _ in tls_peer.seen]


def test_equal_size_over_http_is_not_delivered(env, tmp_path, capsys):
    """Equal size over plain http is recorded as sent, not delivered, with no token."""
    srv = fx.start_server(tmp_path, tls=False)
    try:
        body = "# body\n"
        _queue("t.md", 1, body=body)
        srv.reply = {"ok": True, "files": [{"filename": "t.md", "bytes": len(body)}]}
        rc, out, _ = _run(capsys, "outbox-resubmit", "--only", "t.md", "--peer-ip", "localhost",
                          "--portal-port", str(srv.port), "--timeout", "3")
        assert out["results"][0]["status"] == "sent"  # unauthenticated listing: never delivered
        assert _meta("t.md")["state"] == "sent" and srv.auth_headers == []
    finally:
        srv.stop()


def _redirect_hop():
    """Return a history entry recording a hop to another destination."""
    return [{"from": {"peer_ip": fx.LOOPBACK_V4, "portal_port": "1"},
             "to": {"peer_ip": "localhost", "portal_port": "2"}, "at": "x", "result": "error"}]


def test_flush_skips_queued_item_with_redirected_history(env, capsys):
    """Flush skips a queued item with redirected history unless --only is given."""
    _queue("u.md", 1)
    lpa._set_state("u.md", "queued", history=_redirect_hop())
    rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "2")
    assert out["results"][0]["status"] == "skipped" and "--only" in out["results"][0]["detail"]


def test_flush_only_resends_to_last_approved_destination(tls_peer, capsys):
    """Flush with --only resends to the last approved destination and extends the history."""
    _queue("v.md", 1)  # stale original: loopback port 1
    lpa._set_state("v.md", "queued", history=[
        {"from": {"peer_ip": fx.LOOPBACK_V4, "portal_port": "1"},
         "to": {"peer_ip": "localhost", "portal_port": str(tls_peer.port)}, "at": "x", "result": "error"}])
    rc, out, _ = _run(capsys, "flush-outbox", "--only", "v.md", "--timeout", "3")
    assert rc == 0 and out["results"][0]["status"] == "delivered"
    assert out["results"][0]["peer_ip"] == "localhost" and out["results"][0]["portal_port"] == tls_peer.port
    assert [m for m, _, _ in tls_peer.seen] == ["GET", "POST"]
    m = _meta("v.md")
    assert m["state"] == "delivered" and len(m["history"]) == 2 and _outbox_has("v.md")


def test_peer_base_brackets_only_real_ipv6():
    """_peer_base brackets only real IPv6 literals and rejects host:port typos."""
    assert lpa._peer_base("2001:db8::1", 8002) == "http://[2001:db8::1]:8002"
    assert lpa._peer_base("[2001:db8::1]", 8002) == "http://[2001:db8::1]:8002"
    assert lpa._peer_base("peer.example.test", 8002) == "http://peer.example.test:8002"
    for bad in ("host:8002", "192.0.2.5:8002", "[host:8002]", "[2001:db8::1", "host]"):
        with pytest.raises(SystemExit):
            lpa._peer_base(bad, 8002)


def test_host_port_typo_is_clean_systemexit_not_traceback(env, capsys):
    """A host:port typo is a clean SystemExit on resubmit and a per-item error on flush, not a traceback."""
    _queue("w.md", 1)
    with pytest.raises(SystemExit) as ei:
        lpa.main(["outbox-resubmit", "--only", "w.md", "--peer-ip", "host:8002", "--portal-port", "8002"])
    assert "host:port" in str(ei.value)
    assert _meta("w.md").get("state", "queued") == "queued"
    # a stored host:port peer_ip on a flush is reported per item, no traceback
    _queue("w2.md", 1, host="host:8002")
    rc, out, _ = _run(capsys, "flush-outbox", "--timeout", "2", "--only", "w2.md")
    assert rc == 1 and out["results"][0]["status"] == "error"


def test_urlopen_kwargs_malformed_url_is_trust_error(env, monkeypatch, tmp_path):
    """A malformed URL in a trust-configured URL raises PeerTrustError."""
    monkeypatch.setenv("PEER_CA_FILE", str(tmp_path / "ca.pem"))
    with pytest.raises(peer_tls.PeerTrustError):
        peer_tls.urlopen_kwargs("https://[host:8002]:8002/x")


def test_evidence_filter_sees_through_format_characters(env):
    """The evidence filter detects credentials hidden behind format characters and strips them from clean text."""
    for bad in ("Bearer" + chr(0x200B) + "eyJhbGciOiJIUzI1NiJ9.secret",
                "api_key" + chr(0x2060) + "= sk-live-abc",
                "Bearer" + chr(0xAD) + "abc123def",
                "token" + chr(0x2028) + "= abc123"):
        with pytest.raises(SystemExit):
            lpa._clean_evidence(bad)
    out = lpa._clean_evidence("receipt" + chr(0x200B) + "ok" + chr(0xAD) + "fine")
    assert out == "receipt ok fine"
