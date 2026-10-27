from __future__ import annotations

import importlib.util
import ipaddress
import json
import sys
import time
from pathlib import Path
from typing import Protocol

import pytest

_IP_238 = str(ipaddress.IPv4Address(0xC0A809EE))
_IP_153 = str(ipaddress.IPv4Address(0xC0A80899))
_IP_77 = str(ipaddress.IPv4Address(0xC0A8094D))
_IP_88 = str(ipaddress.IPv4Address(0xC0A80958))
_IP_150 = str(ipaddress.IPv4Address(0xC0A80996))
_IP_151 = str(ipaddress.IPv4Address(0xC0A80997))
_IP_152 = str(ipaddress.IPv4Address(0xC0A80998))
_ROGUE_1 = str(ipaddress.IPv4Address(0x0A000001))
_ROGUE_2 = str(ipaddress.IPv4Address(0x0A000002))

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
TRUST = ROOT / "scripts" / "mesh" / "discovery_trust.py"


class DiscoveryTrustModule(Protocol):
    ROOT: Path
    LOCAL: Path
    KNOWN_PEERS: Path
    ARCHIVE: Path
    OPENCLAW_STATE: Path
    PENDING_HANDSHAKES: Path
    HANDSHAKE_TTL_SEC: int

    def filter_endpoints_for_trust(self, endpoints: dict) -> tuple[dict, list[str]]: ...
    def initiate_handshake(self, ip: str) -> tuple[str, str]: ...
    def verify_handshake(self, ip: str, nonce: str, signature: str) -> bool: ...


@pytest.fixture(autouse=True)
def hermetic_test_environment(monkeypatch) -> None:
    """Verify hermetic test environment."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)


@pytest.fixture
def trust_mod(tmp_path, monkeypatch) -> DiscoveryTrustModule:
    """Verify trust mod."""
    spec = importlib.util.spec_from_file_location("discovery_trust", TRUST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PENDING_HANDSHAKES", tmp_path / ".local" / "pending.json")
    return module  # type: ignore[return-value]


def test_grandfather_known_peer_from_archive(trust_mod, tmp_path, monkeypatch):
    """Verify grandfather known peer from archive."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "lan-topology-archive.json").write_text(
        '{"endpoints": {"LM_STUDIO_WIN_ENDPOINTS": "http://192.168.8.153:1234"}}',
        encoding="utf-8",
    )
    endpoints = {"win": {"ip": "192.168.8.153", "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert blocked == []
    assert filtered["win"]["ip"] == "192.168.8.153"


def test_blocks_unknown_peer_until_approve(trust_mod, tmp_path, monkeypatch):
    """Verify blocks unknown peer until approve."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / ".local" / "pending.json")
    (tmp_path / ".local").mkdir()
    endpoints = {"win": {"ip": "192.168.9.99", "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert "192.168.9.99" in blocked
    assert filtered.get("win") is None


def test_handshake_requires_matching_nonce(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify handshake requires matching nonce."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-secret")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / "pending.json")
    nonce, sig = trust_mod.initiate_handshake("192.168.9.50")
    assert not trust_mod.verify_handshake("192.168.9.50", "wrong-nonce", sig)
    nonce, sig = trust_mod.initiate_handshake("192.168.9.50")
    assert trust_mod.verify_handshake("192.168.9.50", nonce, sig)


def test_expired_handshake_rejected(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify expired handshake rejected."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-secret")
    pending_path = tmp_path / "pending.json"
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", pending_path)
    ip = "192.168.9.51"
    nonce, sig = trust_mod.initiate_handshake(ip)
    stale_ts = time.time() - trust_mod.HANDSHAKE_TTL_SEC - 1
    pending_path.write_text(
        json.dumps({ip: {"nonce": nonce, "ts": stale_ts}}),
        encoding="utf-8",
    )
    assert not trust_mod.verify_handshake(ip, nonce, sig)


def test_blocks_unknown_win_peer(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify blocks unknown win peer."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / ".local" / "pending.json")
    monkeypatch.setattr(trust_mod, "verify_peer_shibboleth", lambda ip: False)
    (tmp_path / ".local").mkdir()
    endpoints = {"win_peers": [{"ip": _IP_88, "models": ["m1"]}]}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert _IP_88 in blocked
    assert filtered["win_peers"] == []


def test_env_ips_auto_trusted(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify env ips auto trusted."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setenv("WIN_3080_IP", _IP_238)
    (tmp_path / ".local").mkdir()
    assert _IP_238 in trust_mod.load_known_peer_ips()
    endpoints = {"win": {"ip": _IP_238, "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert blocked == []
    assert filtered["win"]["ip"] == _IP_238


def test_shibboleth_auto_trusts_live_peer(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify shibboleth auto trusts live peer."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setattr(trust_mod, "verify_peer_shibboleth", lambda ip: ip == _IP_238)
    (tmp_path / ".local").mkdir()
    endpoints = {"win": {"ip": _IP_238, "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert blocked == []
    assert filtered["win"]["ip"] == _IP_238
    assert _IP_238 in trust_mod.load_known_peer_ips()


def test_discovery_relaxed_env(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify discovery relaxed env."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setenv("ORAMA_DISCOVERY_RELAXED", "1")
    (tmp_path / ".local").mkdir()
    endpoints = {"win": {"ip": _IP_77, "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert blocked == []
    assert filtered["win"]["ip"] == _IP_77


def test_strict_config_mode_blocks_unlisted_even_if_shibboleth_passes(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify strict config mode blocks unlisted even if shibboleth passes."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / ".local" / "pending.json")
    monkeypatch.setattr(trust_mod, "verify_peer_shibboleth", lambda ip: True)
    monkeypatch.setenv("ORAMA_STRICT_CONFIG_PEERS", "1")
    (tmp_path / ".local").mkdir()
    # Unknown IP not in known-peers.json
    endpoints = {"win": {"ip": _IP_88, "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert _IP_88 in blocked
    assert filtered.get("win") is None


def test_strict_config_mode_accepts_configured_ips(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify strict config mode accepts configured ips."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setenv("ORAMA_STRICT_CONFIG_PEERS", "1")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text(json.dumps({"ips": [_IP_238]}), encoding="utf-8")
    endpoints = {"win": {"ip": _IP_238, "models": []}}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert blocked == []
    assert filtered["win"]["ip"] == _IP_238


def test_prompt_confirm_peer_accepts_on_yes(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify prompt confirm peer accepts on yes."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    (tmp_path / ".local").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdin, "readline", lambda: "y\n")
    assert trust_mod.prompt_confirm_peer(_IP_150, role="test") is True
    assert _IP_150 in trust_mod.load_known_peer_ips()


def test_prompt_confirm_peer_rejects_on_no(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify prompt confirm peer rejects on no."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    (tmp_path / ".local").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdin, "readline", lambda: "n\n")
    assert trust_mod.prompt_confirm_peer(_IP_151, role="test") is False
    assert _IP_151 not in trust_mod.load_known_peer_ips()


def test_prompt_confirm_peer_non_interactive_fails_safe(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify prompt confirm peer non interactive fails safe."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    (tmp_path / ".local").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert trust_mod.prompt_confirm_peer(_IP_152, role="test") is False
    assert _IP_152 not in trust_mod.load_known_peer_ips()


def test_create_and_verify_ip_migration_announcement(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify create and verify ip migration announcement."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text(json.dumps({"ips": [_IP_153]}), encoding="utf-8")

    # Shifted node creates announcement with proof of identity and previous fleet membership
    announcement = trust_mod.create_migration_announcement(
        node_id="win",
        previous_ip=_IP_153,
        new_ip=_IP_238,
    )
    assert announcement["type"] == "mesh_ip_migration_announcement"
    assert announcement["previous_ip"] == _IP_153
    assert announcement["new_ip"] == _IP_238
    assert len(announcement["signature"]) == 64

    # Recipient verifies announcement
    ok, reason = trust_mod.verify_migration_announcement(announcement)
    assert ok is True
    assert reason == "verified"

    # Applying the announcement updates known peers
    assert trust_mod.apply_migration_announcement(announcement) is True
    assert _IP_238 in trust_mod.load_known_peer_ips()


def test_ip_migration_rejects_unknown_previous_fleet_member(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify ip migration rejects unknown previous fleet member."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text('{"ips": []}', encoding="utf-8")

    # Impostor claims migration from an IP that was never in the fleet
    announcement = trust_mod.create_migration_announcement(
        node_id="rogue",
        previous_ip=_ROGUE_1,
        new_ip=_ROGUE_2,
    )
    ok, reason = trust_mod.verify_migration_announcement(announcement)
    assert ok is False
    assert "was never an acknowledged mesh fleet member" in reason


def test_ip_migration_rejects_tampered_or_stale(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify ip migration rejects tampered or stale."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text(json.dumps({"ips": [_IP_153]}), encoding="utf-8")

    announcement = trust_mod.create_migration_announcement(
        node_id="win",
        previous_ip=_IP_153,
        new_ip=_IP_238,
    )
    # Tamper with new_ip
    bad_announcement = dict(announcement, new_ip=_ROGUE_2)
    ok, reason = trust_mod.verify_migration_announcement(bad_announcement)
    assert ok is False
    assert "invalid cryptographic signature" in reason

    # Stale timestamp
    stale_announcement = dict(announcement, timestamp=time.time() - 400)
    ok, reason = trust_mod.verify_migration_announcement(stale_announcement)
    assert ok is False
    assert "expired" in reason


def test_self_ip_migration_know_thyself_flow(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify self ip migration know thyself flow."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "SELF_IDENTITY_FILE", tmp_path / ".local" / "self-identity.json")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    (tmp_path / ".local").mkdir()

    # Step 1: Initialize self identity with original IP
    (tmp_path / ".local" / "self-identity.json").write_text(
        json.dumps({"node_id": "win", "role": "win", "last_known_ip": _IP_153}),
        encoding="utf-8",
    )

    # Step 2: IP shifts to new IP; check_and_announce_self_migration detects migration
    announcement = trust_mod.check_and_announce_self_migration(
        current_ip=_IP_238,
        peer_ips=[],  # Mock no outbound calls in test
    )
    assert announcement is not None
    assert announcement["previous_ip"] == _IP_153
    assert announcement["new_ip"] == _IP_238

    # Self identity updated
    saved = json.loads((tmp_path / ".local" / "self-identity.json").read_text())
    assert saved["last_known_ip"] == _IP_238


def test_ip_migration_rejects_invalid_types_and_loopback(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify ip migration rejects invalid types and loopback."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text(json.dumps({"ips": [_IP_153]}), encoding="utf-8")

    loopback_ip = str(ipaddress.IPv4Address(0x7F000001))

    # Invalid timestamp type
    bad_ts_announcement = {
        "type": "mesh_ip_migration_announcement",
        "node_id": "win",
        "previous_ip": _IP_153,
        "new_ip": _IP_238,
        "timestamp": "not-a-number",
        "nonce": "test-nonce",
        "signature": "test-sig",
    }
    ok, reason = trust_mod.verify_migration_announcement(bad_ts_announcement)
    assert ok is False
    assert reason == "invalid timestamp"

    # Loopback previous_ip
    loopback_announcement = {
        "type": "mesh_ip_migration_announcement",
        "node_id": "win",
        "previous_ip": loopback_ip,
        "new_ip": _IP_238,
        "timestamp": int(time.time()),
        "nonce": "test-nonce",
        "signature": "test-sig",
    }
    ok, reason = trust_mod.verify_migration_announcement(loopback_announcement)
    assert ok is False
    assert "loopback" in reason

    # Invalid IP address syntax
    bad_ip_announcement = {
        "type": "mesh_ip_migration_announcement",
        "node_id": "win",
        "previous_ip": "invalid-ip-string",
        "new_ip": _IP_238,
        "timestamp": int(time.time()),
        "nonce": "test-nonce",
        "signature": "test-sig",
    }
    ok, reason = trust_mod.verify_migration_announcement(bad_ip_announcement)
    assert ok is False
    assert "invalid previous_ip address format" in reason


def test_self_ip_migration_retries_if_no_peer_acks(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify self ip migration retries if no peer acks."""
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "SELF_IDENTITY_FILE", tmp_path / ".local" / "self-identity.json")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    (tmp_path / ".local").mkdir()

    # Initial state
    (tmp_path / ".local" / "self-identity.json").write_text(
        json.dumps({"node_id": "win", "role": "win", "last_known_ip": _IP_153}),
        encoding="utf-8",
    )

    # When targets exist but all calls fail, last_known_ip MUST NOT advance!
    def mock_fail_open_peer(*args, **kwargs):
        """Fail delivery through the production opener path."""
        raise OSError("unreachable")

    monkeypatch.setattr(trust_mod, "_get_ssl_context", lambda: object())
    monkeypatch.setattr(trust_mod, "_control_plane_tokens", lambda: ["synthetic-bearer"])
    monkeypatch.setattr(trust_mod, "_open_peer", mock_fail_open_peer)

    announcement = trust_mod.check_and_announce_self_migration(
        current_ip=_IP_238,
        peer_ips=[_IP_88],
    )
    assert announcement is not None
    saved = json.loads((tmp_path / ".local" / "self-identity.json").read_text())
    assert saved["last_known_ip"] == _IP_153  # Kept prior IP for retry!
    assert saved["pending_migration"]["recipients"] == [_IP_88]


@pytest.mark.asyncio
async def test_lan_peer_channel_on_inbound_wire_envelope(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify lan peer channel on inbound wire envelope."""
    from orama_system.lan_peer_channel import LanPeerChannel

    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-cluster-secret")
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "known-peers.json").write_text(json.dumps({"ips": [_IP_153]}), encoding="utf-8")

    announcement = trust_mod.create_migration_announcement(
        node_id="win",
        previous_ip=_IP_153,
        new_ip=_IP_238,
    )

    channel = LanPeerChannel()
    wire_event = {
        "type": "mesh_ip_migration_announcement",
        "source": "win",
        "ts": int(time.time()),
        "data": announcement,
    }
    monkeypatch.setitem(sys.modules, "mesh.discovery_trust", trust_mod)

    await channel.on_inbound(wire_event)
    assert _IP_238 in trust_mod.load_known_peer_ips()


def test_ssl_context_never_unverified_even_when_relaxed(trust_mod, tmp_path, monkeypatch) -> None:
    """Bearer-bearing paths must not get an unverified TLS context under ORAMA_DISCOVERY_RELAXED."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    (tmp_path / ".local").mkdir()
    monkeypatch.delenv("ORAMA_LAN_CA_FILE", raising=False)
    monkeypatch.setattr(trust_mod, "_find_ca_file", lambda: None)
    monkeypatch.setenv("ORAMA_DISCOVERY_RELAXED", "1")
    assert trust_mod._get_ssl_context() is None
    src = TRUST.read_text(encoding="utf-8")
    assert "_create_unverified_context" not in src


def test_control_plane_token_excludes_gossip_shared_secret(trust_mod, monkeypatch) -> None:
    """HMAC signing secrets must not double as the control-plane bearer."""
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", raising=False)
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_LOCAL", raising=False)
    monkeypatch.delenv("PT_CONTROL_PLANE_TOKEN", raising=False)
    import utils.control_plane_auth as auth
    monkeypatch.setattr(auth, "persisted_control_plane_token", lambda: "")
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "gossip-only-secret")
    monkeypatch.setenv("MESH_MIGRATION_SECRET", "migration-only-secret")
    assert trust_mod._control_plane_token() == ""
    assert trust_mod._secret() == "migration-only-secret"


def test_shibboleth_fails_closed_without_ca_even_when_relaxed(trust_mod, tmp_path, monkeypatch) -> None:
    """Verify shibboleth fails closed without ca even when relaxed."""
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    (tmp_path / ".local").mkdir()
    monkeypatch.delenv("ORAMA_LAN_CA_FILE", raising=False)
    monkeypatch.setattr(trust_mod, "_find_ca_file", lambda: None)
    monkeypatch.setenv("ORAMA_DISCOVERY_RELAXED", "1")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "bearer-token")
    # TCP connect succeeds so we reach the SSL gate.
    monkeypatch.setattr(
        trust_mod.socket,
        "create_connection",
        lambda *args, **kwargs: type("C", (), {"__enter__": lambda s: s, "__exit__": lambda *a: None})(),
    )
    assert trust_mod.verify_peer_shibboleth(_IP_88) is False
