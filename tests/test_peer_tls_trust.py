"""Per-stack peer TLS trust (PEER_CA_FILE / PEER_PINNED_FINGERPRINTS)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography", reason="cryptography needed to mint throwaway test certs")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import peer_tls_fixtures as fx  # noqa: E402

import lan_peer_assign as lpa  # noqa: E402
import peer_tls  # noqa: E402
import probe_lan_peer as probe  # noqa: E402


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    for var in (
        "PEER_CA_FILE", "PEER_PINNED_FINGERPRINTS", "SSL_CERT_FILE", "ORAMA_CONTROL_PLANE_TOKEN_PEER",
        "ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "PT_CONTROL_PLANE_TOKEN", "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "PT_HOME",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", fx.SYNTHETIC_TOKEN)
    peer_tls.clear_cache()
    yield
    peer_tls.clear_cache()


@pytest.fixture
def ca_server(tmp_path):
    ca = fx.make_ca()
    leaf = fx.make_leaf(issuer=ca)
    ca_pem = fx.write_pem(tmp_path / "ca.pem", ca[1])
    srv = fx.start_server(tmp_path, leaf)
    yield srv, ca_pem, leaf[1]
    srv.stop()


def _url(srv, host="localhost"):
    return f"https://{host}:{srv.port}/api/peer-file"


def test_ca_file_trust_succeeds_for_dns_name_and_ip(ca_server, monkeypatch):
    srv, ca_pem, _ = ca_server
    monkeypatch.setenv("PEER_CA_FILE", str(ca_pem))
    for host in ("localhost", fx.LOOPBACK_V4):
        result, authed = lpa._http_json_ex("POST", _url(srv, host), {"x": 1}, timeout=5)
        assert result == {"ok": True} and authed is True
    assert srv.auth_headers and all(h == f"Bearer {fx.SYNTHETIC_TOKEN}" for h in srv.auth_headers)


def test_trust_is_not_global(ca_server, monkeypatch):
    import os
    srv, ca_pem, _ = ca_server
    monkeypatch.setenv("PEER_CA_FILE", str(ca_pem))
    before = dict(os.environ)
    lpa._http_json_ex("GET", _url(srv), timeout=5)
    assert dict(os.environ) == before
    assert "SSL_CERT_FILE" not in os.environ


def test_different_ca_fails_and_token_never_sent(ca_server, monkeypatch, tmp_path):
    srv, _, _ = ca_server
    other = fx.write_pem(tmp_path / "other.pem", fx.make_ca("someone-else")[1])
    monkeypatch.setenv("PEER_CA_FILE", str(other))
    with pytest.raises(SystemExit) as ei:
        lpa._http_json_ex("POST", _url(srv), {"x": 1}, timeout=5)
    assert "token not sent" in str(ei.value) or "verif" in str(ei.value).lower()
    assert srv.auth_headers == []
    assert srv.seen == []
    assert fx.SYNTHETIC_TOKEN not in str(ei.value)


def test_no_ca_default_roots_fail_and_token_never_sent(ca_server):
    srv, _, _ = ca_server
    with pytest.raises(SystemExit):
        lpa._http_json_ex("POST", _url(srv), {"x": 1}, timeout=5)
    assert srv.seen == []  # not even a request arrived, let alone a header


def test_pinned_self_signed_success_and_mismatch(tmp_path, monkeypatch):
    leaf = fx.make_leaf()  # self-signed
    srv = fx.start_server(tmp_path, leaf)
    try:
        fp = fx.fingerprint(leaf[1])
        monkeypatch.setenv("PEER_PINNED_FINGERPRINTS", ":".join(fp[i:i + 2] for i in range(0, 64, 2)).upper())
        result, authed = lpa._http_json_ex("POST", _url(srv), {}, timeout=5)
        assert result == {"ok": True} and authed
        assert srv.auth_headers == [f"Bearer {fx.SYNTHETIC_TOKEN}"]

        n = len(srv.seen)
        peer_tls.clear_cache()
        monkeypatch.setenv("PEER_PINNED_FINGERPRINTS", "ab" * 32)
        with pytest.raises(SystemExit) as ei:
            lpa._http_json_ex("POST", _url(srv), {}, timeout=5)
        assert "pinned" in str(ei.value) and "token not sent" in str(ei.value)
        assert len(srv.seen) == n  # nothing reached the server after mismatch
    finally:
        srv.stop()


def test_pin_matching_but_expired_cert_is_rejected(tmp_path, monkeypatch):
    leaf = fx.make_leaf(expired=True)
    srv = fx.start_server(tmp_path, leaf)
    try:
        monkeypatch.setenv("PEER_PINNED_FINGERPRINTS", fx.fingerprint(leaf[1]))
        with pytest.raises(SystemExit):
            lpa._http_json_ex("POST", _url(srv), {}, timeout=5)
        assert srv.auth_headers == []
    finally:
        srv.stop()


def test_invalid_pin_entry_is_a_hard_error(monkeypatch):
    monkeypatch.setenv("PEER_PINNED_FINGERPRINTS", "not-a-fingerprint")
    with pytest.raises(peer_tls.PeerTrustError):
        peer_tls.pinned_fingerprints()


def test_probe_http_get_obeys_trust(ca_server, monkeypatch, tmp_path):
    srv, ca_pem, _ = ca_server
    monkeypatch.setenv("PEER_CA_FILE", str(ca_pem))
    status, _body = probe.http_get(_url(srv), token=fx.SYNTHETIC_TOKEN, timeout=5)
    assert status == 200 and srv.auth_headers
    n = len(srv.seen)
    peer_tls.clear_cache()
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "o.pem", fx.make_ca("x")[1])))
    status, detail = probe.http_post_json(_url(srv), {}, token=fx.SYNTHETIC_TOKEN, timeout=5)
    assert status == -1 and len(srv.seen) == n
    assert fx.SYNTHETIC_TOKEN not in detail


def test_http_never_carries_a_token(tmp_path, caplog):
    srv = fx.start_server(tmp_path, tls=False)
    try:
        url = f"http://{fx.LOOPBACK_V4}:{srv.port}/api/peer-file"
        assert lpa._is_authenticated_transport(url) is False
        with caplog.at_level(logging.ERROR, logger="lan_peer_assign"):
            result, authed = lpa._http_json_ex("POST", url, {}, timeout=5)
        assert authed is False  # accepted, but never as an authenticated delivery
        assert srv.seen and srv.auth_headers == []
        assert "SECURITY_STOP" in caplog.text
        assert fx.SYNTHETIC_TOKEN not in caplog.text
    finally:
        srv.stop()


def test_verification_is_never_disabled_in_source():
    src = Path(peer_tls.__file__).read_text(encoding="utf-8")
    assert "CERT_NONE" not in src
    assert "check_hostname = False" not in src
    assert "_create_unverified_context" not in src
