"""Network-free regressions for migration trust, delivery and recovery boundaries."""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import sys
import urllib.error
import urllib.request
from email.message import Message
from io import BytesIO
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit
OLD, NEW, A, B = [str(ipaddress.IPv4Address(i)) for i in (0xC0000201, 0xC0000202, 0xC0000203, 0xC0000204)]


@pytest.fixture
def trust(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load a fresh module with every writable state location isolated."""
    path = Path(__file__).resolve().parents[1] / "scripts/mesh/discovery_trust.py"
    spec = importlib.util.spec_from_file_location("mesh.discovery_trust", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "mesh.discovery_trust", module)
    spec.loader.exec_module(module)
    for name in ("KNOWN_PEERS", "ARCHIVE", "OPENCLAW_STATE", "SELF_IDENTITY_FILE", "PENDING_HANDSHAKES"):
        monkeypatch.setattr(module, name, tmp_path / f"{name}.json")
    for key in ("WIN_3080_IP", "WIN_5080_IP", "WIN_PEER_IPS", "PEER_IPS", "ORAMA_STRICT_CONFIG_PEERS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MESH_MIGRATION_SECRET", "synthetic-signing-key")
    monkeypatch.setattr(module, "_get_ssl_context", lambda: object())
    monkeypatch.setattr(module, "_control_plane_tokens", lambda: ["synthetic-bearer"])
    module._save_json(module.KNOWN_PEERS, {"ips": [OLD]})
    module.save_self_identity({"node_id": "win", "last_known_ip": OLD})
    return module


class Response:
    """Small context-managed HTTP response used by delivery tests."""
    status = 200

    def __init__(self, payload: dict) -> None:
        """Keep the supplied response body."""
        self.payload = payload

    def __enter__(self) -> Response:
        """Enter the response context."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the synthetic response."""

    def read(self, limit: int) -> bytes:
        """Return bounded response bytes."""
        return json.dumps(self.payload).encode()[:limit]


@pytest.mark.parametrize("destination", ["http://other.invalid/x", "https://other.invalid/x"])
def test_redirect_is_never_constructed(trust: ModuleType, destination: str) -> None:
    """Redirect handling cannot construct a second credential-bearing request."""
    request = urllib.request.Request("https://peer.invalid/x", headers={"Authorization": "Bearer synthetic"})
    handler = trust._NoRedirect()
    assert handler.redirect_request(request, None, 302, "redirect", {}, destination) is None


@pytest.mark.parametrize("destination", ["http://other.invalid/x", "https://other.invalid/x"])
def test_authenticated_request_stops_at_first_redirect(trust: ModuleType, monkeypatch: pytest.MonkeyPatch, destination: str) -> None:
    """The production opener issues exactly one request when a verified origin redirects."""
    calls: list[urllib.request.Request] = []

    def respond(handler: object, request: urllib.request.Request) -> object:
        """Simulate the verified TLS response without opening a network connection."""
        calls.append(request)
        headers = Message()
        headers["Location"] = destination
        response = urllib.response.addinfourl(BytesIO(b""), headers, request.full_url, 302)
        response.msg = "Found"
        return response

    import ssl
    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", respond)
    request = urllib.request.Request("https://peer.invalid/x", headers={"Authorization": "Bearer synthetic"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        trust._open_peer(request, ssl.create_default_context(), 1.0)
    assert caught.value.code == 302
    assert len(calls) == 1
    assert calls[0].full_url == "https://peer.invalid/x"


def test_strict_valid_signature_cannot_admit_new_destination(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Signing authority cannot override the operator's strict address allowlist."""
    monkeypatch.setenv("ORAMA_STRICT_CONFIG_PEERS", "1")
    announcement = trust.create_migration_announcement("win", OLD, NEW)
    assert trust.apply_migration_announcement(announcement) is False
    with pytest.raises(ValueError, match="strict configuration"):
        trust.remember_peer(NEW)
    assert NEW not in trust.load_known_peer_ips()


def test_revocation_overrides_archive_and_relaxed_admission(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached or relaxed admission cannot resurrect an administratively removed peer."""
    trust._save_json(trust.ARCHIVE, {"endpoints": {"win": f"https://{OLD}:8443"}})
    trust._save_json(trust.OPENCLAW_STATE, {"endpoints": {"win": {"ip": OLD}}})
    monkeypatch.setenv("WIN_PEER_IPS", OLD)
    monkeypatch.setenv("ORAMA_DISCOVERY_RELAXED", "1")
    assert trust.forget_peer(OLD)
    assert OLD not in trust.load_known_peer_ips()
    assert trust.peer_trusted(OLD) is False


def test_partial_ack_retries_only_pending_recipient_after_reload(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """One acknowledgement never suppresses another recipient's durable retry."""
    calls: list[str] = []

    def deliver(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Acknowledge A and fail B on the first process-equivalent pass."""
        calls.append(request.host)
        if request.host.startswith(B):
            raise OSError("offline")
        announcement = json.loads(request.data)["data"]
        return Response({"ok": True, "migration_id": trust.migration_digest(announcement)})

    monkeypatch.setattr(trust, "_open_peer", deliver)
    trust.check_and_announce_self_migration(NEW, [A, B])
    saved = trust.load_self_identity()
    assert saved["last_known_ip"] == OLD
    assert saved["pending_migration"]["recipients"] == [B]
    calls.clear()

    def acknowledge(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Acknowledge the retained recipient from freshly read disk state."""
        calls.append(request.host)
        return Response({"ok": True, "migration_id": trust.migration_digest(json.loads(request.data)["data"])})

    monkeypatch.setattr(trust, "_open_peer", acknowledge)
    trust.check_and_announce_self_migration(NEW, [A, B])
    assert calls == [f"{B}:8443"]
    assert trust.load_self_identity()["last_known_ip"] == NEW
    assert "pending_migration" not in trust.load_self_identity()


@pytest.mark.parametrize("ack", [{"ok": True}, {"ok": False}, {"ok": True, "migration_id": "wrong"}])
def test_http_success_without_exact_application_ack_is_pending(trust: ModuleType, monkeypatch: pytest.MonkeyPatch, ack: dict) -> None:
    """HTTP success alone cannot commit sender migration state."""
    monkeypatch.setattr(trust, "_open_peer", lambda *args: Response(ack))
    trust.check_and_announce_self_migration(NEW, [A])
    assert trust.load_self_identity()["last_known_ip"] == OLD


def test_stale_pending_migration_is_superseded_on_newer_address(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A later DHCP move must announce last_ip→newest and retain unpaid recipients."""
    c = str(ipaddress.IPv4Address(0xC0000205))
    calls: list[str] = []

    def fail(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Keep every recipient pending on the first address change."""
        calls.append(json.loads(request.data)["data"]["new_ip"])
        raise OSError("offline")

    monkeypatch.setattr(trust, "_open_peer", fail)
    trust.check_and_announce_self_migration(NEW, [A, B])
    assert trust.load_self_identity()["pending_migration"]["new_ip"] == NEW
    calls.clear()

    def still_offline(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Observe the superseded announcement while recipients stay pending."""
        payload = json.loads(request.data)["data"]
        calls.append(f"{request.host}:{payload['previous_ip']}->{payload['new_ip']}")
        raise OSError("offline")

    monkeypatch.setattr(trust, "_open_peer", still_offline)
    trust.check_and_announce_self_migration(c, [A])
    saved = trust.load_self_identity()
    assert saved["last_known_ip"] == OLD
    assert saved["pending_migration"]["new_ip"] == c
    assert saved["pending_migration"]["recipients"] == [A, B]
    assert calls == [f"{A}:8443:{OLD}->{c}", f"{B}:8443:{OLD}->{c}"]


def test_pending_migration_cleared_when_address_returns_to_last_known(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returning to the committed address drops a stale pending migration."""
    monkeypatch.setattr(trust, "_open_peer", lambda *args: (_ for _ in ()).throw(OSError("offline")))
    trust.check_and_announce_self_migration(NEW, [A])
    assert "pending_migration" in trust.load_self_identity()
    assert trust.check_and_announce_self_migration(OLD, [A]) is None
    assert "pending_migration" not in trust.load_self_identity()
    assert trust.load_self_identity()["last_known_ip"] == OLD


def test_ack_peer_returns_false_when_remember_peer_rejects(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verified handshake cannot bypass revocation or strict allowlist policy."""
    trust.forget_peer(OLD)
    monkeypatch.setattr(trust, "verify_handshake", lambda *args: True)
    assert trust.ack_peer(OLD, "nonce", "signature") is False
    assert OLD not in trust.load_known_peer_ips()


def test_filter_endpoints_skips_remember_peer_for_loopback(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loopback trust must not call remember_peer (strict mode would raise)."""
    monkeypatch.setenv("ORAMA_STRICT_CONFIG_PEERS", "1")
    calls: list[str] = []
    original = trust.remember_peer

    def tracked(ip: str) -> None:
        """Record remember_peer attempts while preserving production behavior."""
        calls.append(ip)
        original(ip)

    monkeypatch.setattr(trust, "remember_peer", tracked)
    endpoints = {"mac": {"ip": "127.0.0.1"}, "win": None, "win_peers": []}
    out, blocked = trust.filter_endpoints_for_trust(endpoints)
    assert out["mac"] == {"ip": "127.0.0.1"}
    assert blocked == []
    assert calls == []


def test_delivery_tries_next_canonical_credential_only_on_auth_refusal(trust: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A rejected peer credential can fall back without following redirects."""
    monkeypatch.setattr(trust, "_control_plane_tokens", lambda: ["synthetic-first", "synthetic-second"])
    calls: list[str] = []

    def deliver(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Refuse the first candidate and acknowledge the second."""
        calls.append(request.get_header("Authorization"))
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 401, "refused", {}, None)
        return Response({"ok": True, "migration_id": trust.migration_digest(json.loads(request.data)["data"])})

    monkeypatch.setattr(trust, "_open_peer", deliver)
    trust.check_and_announce_self_migration(NEW, [A])
    assert calls == ["Bearer synthetic-first", "Bearer synthetic-second"]
    assert trust.load_self_identity()["last_known_ip"] == NEW


def test_explicit_operator_reapproval_lifts_revocation(trust: ModuleType) -> None:
    """Only the explicit approval workflow can undo an effective revocation."""
    trust.forget_peer(OLD)
    with pytest.raises(ValueError, match="revoked"):
        trust.remember_peer(OLD)
    trust.approve_peer(OLD)
    assert OLD in trust.load_known_peer_ips()


@pytest.mark.parametrize("outcome", ["accepted", "signature", "persistence"])
def test_route_application_ack_controls_sender_commit(trust: ModuleType, monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    """Exercise producer through authenticated route, dispatcher and sender settlement."""
    from fastapi.testclient import TestClient
    import orama_system.portal_server as portal
    from orama_system.lan_peer_channel import LanPeerChannel

    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "synthetic-route-bearer")
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setattr(portal, "_lan_peer_channel", LanPeerChannel())
    client = TestClient(portal.app)
    if outcome == "persistence":
        def fail_write(ip: str) -> None:
            """Simulate storage refusing the receiver's trust update."""
            raise OSError("synthetic storage failure")
        monkeypatch.setattr(trust, "remember_peer", fail_write)

    def deliver(request: urllib.request.Request, context: object, timeout: float) -> Response:
        """Pass a tampered wire event through the real protected route."""
        wire = json.loads(request.data)
        if outcome == "signature":
            wire["data"]["signature"] = "invalid"
        response = client.post("/api/peer-event", json=wire, headers={"Authorization": "Bearer synthetic-route-bearer"})
        assert response.status_code == (200 if outcome == "accepted" else 409)
        return Response(response.json())

    monkeypatch.setattr(trust, "_open_peer", deliver)
    trust.check_and_announce_self_migration(NEW, [A])
    assert trust.load_self_identity()["last_known_ip"] == (NEW if outcome == "accepted" else OLD)
    assert (NEW in trust.load_known_peer_ips()) is (outcome == "accepted")


@pytest.mark.parametrize("lane", ["peer", "local", "pt-root"])
def test_token_resolver_uses_canonical_lane_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lane: str) -> None:
    """Peer precedence, local-only credentials and configured PT token files remain supported."""
    import utils.control_plane_auth as auth
    path = Path(__file__).resolve().parents[1] / "scripts/mesh/discovery_trust.py"
    spec = importlib.util.spec_from_file_location("isolated_discovery_tokens", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key in ("ORAMA_CONTROL_PLANE_TOKEN", "ORAMA_CONTROL_PLANE_TOKEN_PEER", "ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "PT_CONTROL_PLANE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    if lane == "peer":
        monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "synthetic-local")
        monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", "synthetic-peer")
        expected = "synthetic-peer"
    elif lane == "local":
        monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "synthetic-local-only")
        expected = "synthetic-local-only"
    else:
        (tmp_path / ".state").mkdir()
        (tmp_path / ".state/control_plane_token").write_text("synthetic-pt-file", encoding="utf-8")
        expected = "synthetic-pt-file"
    assert module._control_plane_tokens() == auth.outbound_control_plane_tokens()
    assert module._control_plane_tokens()[0] == expected
