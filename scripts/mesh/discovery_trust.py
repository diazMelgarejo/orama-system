#!/usr/bin/env python3
"""P6 discovery trust — grandfather known peers, handshake new ones."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local"
KNOWN_PEERS = LOCAL / "known-peers.json"
PENDING_HANDSHAKES = LOCAL / "discovery-handshake-pending.json"
ARCHIVE = LOCAL / "lan-topology-archive.json"
OPENCLAW_STATE = Path.home() / ".openclaw" / "state" / "last_discovery.json"
HANDSHAKE_TTL_SEC = 600


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _secret() -> str:
    for key in ("GOSSIP_SHARED_SECRET", "ORAMA_CONTROL_PLANE_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    data = _load_json(ROOT / ".local" / "mesh-secrets.json")
    secret = (data.get("GOSSIP_SHARED_SECRET") or "").strip()
    return str(secret) if secret else ""


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _ips_from_archive() -> set[str]:
    data = _load_json(ARCHIVE)
    ips: set[str] = set()
    for url in (data.get("endpoints") or {}).values():
        if not isinstance(url, str):
            continue
        for part in url.replace("http://", "").replace("https://", "").split("/"):
            if part and part[0].isdigit():
                ips.add(part.split(":")[0])
    return ips


def _ips_from_last_discovery() -> set[str]:
    data = _load_json(OPENCLAW_STATE)
    ips: set[str] = set()
    for ep in (data.get("endpoints") or {}).values():
        if isinstance(ep, dict) and ep.get("ip"):
            ips.add(str(ep["ip"]))
    return ips


def load_known_peer_ips() -> set[str]:
    store = _load_json(KNOWN_PEERS)
    ips = set(store.get("ips") or [])
    ips |= _ips_from_archive()
    ips |= _ips_from_last_discovery()
    return {ip for ip in ips if ip and ip not in ("127.0.0.1", "localhost")}


def remember_peer(ip: str) -> None:
    if not ip:
        return
    store = _load_json(KNOWN_PEERS)
    ips = set(store.get("ips") or [])
    ips.add(ip)
    store["ips"] = sorted(ips)
    store["updated_at"] = time.time()
    _save_json(KNOWN_PEERS, store)


def handshake_signature(ip: str, nonce: str) -> str:
    secret = _secret()
    if not secret:
        return ""
    return hmac.new(
        secret.encode(),
        f"discovery-handshake:{ip}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _pending_entry(ip: str) -> dict | None:
    pending = _load_json(PENDING_HANDSHAKES)
    entry = pending.get(ip)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("ts", 0)) > HANDSHAKE_TTL_SEC:
        pending.pop(ip, None)
        _save_json(PENDING_HANDSHAKES, pending)
        return None
    return entry


def verify_handshake(ip: str, nonce: str, signature: str) -> bool:
    entry = _pending_entry(ip)
    if not entry:
        return False
    stored_nonce = str(entry.get("nonce") or "")
    if not stored_nonce or stored_nonce != nonce.strip():
        return False
    expected = handshake_signature(ip, nonce)
    if not expected or not hmac.compare_digest(expected, signature.strip()):
        return False
    pending = _load_json(PENDING_HANDSHAKES)
    pending.pop(ip, None)
    _save_json(PENDING_HANDSHAKES, pending)
    return True


def initiate_handshake(ip: str) -> tuple[str, str]:
    nonce = secrets.token_hex(8)
    pending = _load_json(PENDING_HANDSHAKES)
    pending[ip] = {"nonce": nonce, "ts": time.time()}
    _save_json(PENDING_HANDSHAKES, pending)
    sig = handshake_signature(ip, nonce)
    return nonce, sig


def peer_trusted(ip: str) -> bool:
    if not ip or ip in ("127.0.0.1", "localhost"):
        return True
    if ip in load_known_peer_ips():
        return True
    if os.environ.get("ORAMA_APPROVE_DISCOVERY", "").strip().lower() in ("1", "true", "yes"):
        remember_peer(ip)
        return True
    return False


def _block_untrusted_peer(ip: str, role: str, blocked: list[str]) -> None:
    nonce, sig = initiate_handshake(ip)
    blocked.append(ip)
    print(
        f"🤝 New peer {ip} ({role}) — acknowledge before persist:\n"
        f"   ORAMA_APPROVE_DISCOVERY=1 discover.py   # one-shot approve\n"
        f"   discover.py --ack-peer {ip} --nonce {nonce} --signature {sig}",
        flush=True,
    )


def filter_endpoints_for_trust(endpoints: dict) -> tuple[dict, list[str]]:
    """Grandfather known peers; block persist for unknown until ack."""
    out = dict(endpoints)
    blocked: list[str] = []
    for role in ("mac", "win"):
        ep = out.get(role)
        if not ep or not isinstance(ep, dict):
            continue
        ip = str(ep.get("ip") or "").strip()
        if not ip:
            continue
        if peer_trusted(ip):
            remember_peer(ip)
            continue
        _block_untrusted_peer(ip, role, blocked)
        out[role] = None

    peers_in: list[dict] = []
    for peer in out.get("win_peers") or []:
        if not isinstance(peer, dict):
            continue
        ip = str(peer.get("ip") or "").strip()
        if not ip:
            peers_in.append(peer)
            continue
        if peer_trusted(ip):
            remember_peer(ip)
            peers_in.append(peer)
            continue
        _block_untrusted_peer(ip, "win_peer", blocked)
    out["win_peers"] = peers_in
    return out, blocked


def ack_peer(ip: str, nonce: str, signature: str) -> bool:
    if not verify_handshake(ip, nonce, signature):
        return False
    remember_peer(ip)
    return True
