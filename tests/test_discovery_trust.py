from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
TRUST = ROOT / "scripts" / "mesh" / "discovery_trust.py"


@pytest.fixture
def trust_mod():
    spec = importlib.util.spec_from_file_location("discovery_trust", TRUST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_grandfather_known_peer_from_archive(trust_mod, tmp_path, monkeypatch):
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
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "test-secret")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / "pending.json")
    nonce, sig = trust_mod.initiate_handshake("192.168.9.50")
    assert not trust_mod.verify_handshake("192.168.9.50", "wrong-nonce", sig)
    nonce, sig = trust_mod.initiate_handshake("192.168.9.50")
    assert trust_mod.verify_handshake("192.168.9.50", nonce, sig)


def test_blocks_unknown_win_peer(trust_mod, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(trust_mod, "ROOT", tmp_path)
    monkeypatch.setattr(trust_mod, "LOCAL", tmp_path / ".local")
    monkeypatch.setattr(trust_mod, "KNOWN_PEERS", tmp_path / ".local" / "known-peers.json")
    monkeypatch.setattr(trust_mod, "ARCHIVE", tmp_path / ".local" / "lan-topology-archive.json")
    monkeypatch.setattr(trust_mod, "OPENCLAW_STATE", tmp_path / "last.json")
    monkeypatch.setattr(trust_mod, "PENDING_HANDSHAKES", tmp_path / ".local" / "pending.json")
    (tmp_path / ".local").mkdir()
    endpoints = {"win_peers": [{"ip": "192.168.9.88", "models": ["m1"]}]}
    filtered, blocked = trust_mod.filter_endpoints_for_trust(endpoints)
    assert "192.168.9.88" in blocked
    assert filtered["win_peers"] == []
