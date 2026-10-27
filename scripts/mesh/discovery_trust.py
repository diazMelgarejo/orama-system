#!/usr/bin/env python3
"""P6 discovery trust — grandfather known peers, handshake new ones."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import socket
import ssl
import sys
import time
import urllib.request
from pathlib import Path

_LOOPBACK_V4 = str(ipaddress.IPv4Address(0x7F000001))

_MESH_DIR = Path(__file__).resolve().parent
if str(_MESH_DIR) not in sys.path:
    sys.path.insert(0, str(_MESH_DIR))
from mesh_logging import get_mesh_logger  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local"
KNOWN_PEERS = LOCAL / "known-peers.json"
PENDING_HANDSHAKES = LOCAL / "discovery-handshake-pending.json"
ARCHIVE = LOCAL / "lan-topology-archive.json"
SELF_IDENTITY_FILE = LOCAL / "self-identity.json"
OPENCLAW_STATE = Path.home() / ".openclaw" / "state" / "last_discovery.json"
HANDSHAKE_TTL_SEC = 600
log = get_mesh_logger("orama.mesh.discovery_trust", repo_root=ROOT)


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


def _control_plane_token() -> str:
    for key in ("ORAMA_CONTROL_PLANE_TOKEN", "ORAMA_CONTROL_PLANE_TOKEN_PEER", "GOSSIP_SHARED_SECRET"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    for p in (
        Path.home() / ".openclaw" / "state" / "control_plane_token",
        ROOT.parent / ".state" / "control_plane_token",
    ):
        if p.is_file():
            try:
                t = p.read_text(encoding="utf-8").strip()
                if t:
                    return t
            except OSError:
                pass
    return ""


def _get_ssl_context() -> ssl.SSLContext:
    """Return SSL context validating against cluster CA if present, else fallback."""
    for ca_path in (
        os.environ.get("ORAMA_LAN_CA_FILE", ""),
        str(LOCAL / "certs" / "orama-lan-ca-PHLab-H2LGBV3.pem"),
        str(LOCAL / "orama-lan-ca.pem"),
        str(ROOT / "certs" / "ca.pem"),
        str(Path.home() / ".openclaw" / "certs" / "ca.pem"),
    ):
        if ca_path and Path(ca_path).is_file():
            try:
                ctx = ssl.create_default_context(cafile=ca_path)
                ctx.check_hostname = False
                return ctx
            except Exception:
                pass
    return ssl._create_unverified_context()


def is_strict_config_mode() -> bool:
    """Return whether strict configuration peers mode is active.

    When active, discovery only trusts IPs explicitly listed in config files
    or environment configuration, disabling automatic shibboleth auto-trust.
    """
    return os.environ.get("ORAMA_STRICT_CONFIG_PEERS", "").strip().lower() in ("1", "true", "yes")


def _ips_from_env() -> set[str]:
    ips: set[str] = set()
    for key in ("WIN_3080_IP", "WIN_5080_IP", "WIN_PEER_IPS", "PEER_IPS"):
        for part in os.environ.get(key, "").split(","):
            part = part.strip()
            if part:
                ips.add(part)
    return ips


def verify_peer_shibboleth(ip: str, timeout: float = 0.5) -> bool:
    """Probe peer over TLS with known control plane token (shibboleth).

    If peer answers on port 8443 and returns 200 with our token, it is a known cluster peer.
    Timeout is clamped to prevent accumulation during subnet scans.
    """
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    try:
        with socket.create_connection((ip, 8443), timeout=timeout):
            pass
    except Exception:
        return False

    token = _control_plane_token()
    ctx = _get_ssl_context()
    req = urllib.request.Request(f"https://{ip}:8443/health")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    return False


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
    ips |= _ips_from_env()
    if not is_strict_config_mode():
        ips |= _ips_from_archive()
        ips |= _ips_from_last_discovery()
    return {ip for ip in ips if ip and ip not in (_LOOPBACK_V4, "localhost")}


def remember_peer(ip: str) -> None:
    if not ip:
        return
    store = _load_json(KNOWN_PEERS)
    ips = set(store.get("ips") or [])
    ips.add(ip)
    store["ips"] = sorted(ips)
    store["updated_at"] = time.time()
    _save_json(KNOWN_PEERS, store)


def forget_peer(ip: str) -> bool:
    if not ip:
        return False
    store = _load_json(KNOWN_PEERS)
    ips = set(store.get("ips") or [])
    if ip in ips:
        ips.remove(ip)
        store["ips"] = sorted(ips)
        store["updated_at"] = time.time()
        _save_json(KNOWN_PEERS, store)
        return True
    return False


def prompt_confirm_peer(ip: str, role: str = "peer") -> bool:
    """Prompt the operator interactively to confirm whether to trust an unknown peer IP.

    Returns True and remembers peer if user confirms; False otherwise.
    Safe for non-interactive execution: returns False immediately if stdin is not a TTY.
    """
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    if not sys.stdin.isatty():
        return False
    try:
        sys.stderr.write(
            f"\n[PROMPT] Unlisted peer {ip} ({role}) detected on LAN.\n"
            f"         Trust peer and add to {KNOWN_PEERS.name}? [y/N]: "
        )
        sys.stderr.flush()
        answer = sys.stdin.readline().strip().lower()
        if answer in ("y", "yes"):
            remember_peer(ip)
            log.info("Peer %s (%s) manually confirmed and trusted by operator", ip, role)
            return True
    except (OSError, EOFError, KeyboardInterrupt):
        pass
    return False


def get_local_ip() -> str:
    """Determine primary local LAN IP via UDP route probe without transmitting data."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except Exception:
        return _LOOPBACK_V4
    finally:
        s.close()


def load_self_identity() -> dict:
    """Load the node's durable self-identity from disk."""
    data = _load_json(SELF_IDENTITY_FILE)
    if not data:
        data = {
            "node_id": "win" if sys.platform == "win32" else "mac",
            "role": "win" if sys.platform == "win32" else "mac",
            "last_known_ip": "",
            "history": [],
        }
    return data


def save_self_identity(data: dict) -> None:
    _save_json(SELF_IDENTITY_FILE, data)


def create_migration_announcement(
    node_id: str,
    previous_ip: str,
    new_ip: str,
    role: str = "",
) -> dict:
    """Create a signed IP migration announcement with cryptographic proof of fleet membership."""
    ts = int(time.time())
    nonce = secrets.token_hex(8)
    secret = _secret()
    sig = ""
    if secret:
        sig = hmac.new(
            secret.encode(),
            f"mesh-ip-migration:{node_id}:{previous_ip}:{new_ip}:{ts}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
    return {
        "type": "mesh_ip_migration_announcement",
        "node_id": node_id,
        "role": role or node_id,
        "previous_ip": previous_ip,
        "new_ip": new_ip,
        "timestamp": ts,
        "nonce": nonce,
        "signature": sig,
    }


def verify_migration_announcement(announcement: dict, window_sec: int = 300) -> tuple[bool, str]:
    """Verify proof of identity and previous mesh fleet membership.

    Checks:
      1. Envelope structure and timestamp freshness.
      2. Cryptographic signature under cluster secret.
      3. Fleet membership: previous_ip MUST be an established member in known_peers or archive.
    """
    if not isinstance(announcement, dict):
        return False, "invalid envelope"
    if announcement.get("type") != "mesh_ip_migration_announcement":
        return False, "unexpected event type"

    node_id = str(announcement.get("node_id") or "").strip()
    previous_ip = str(announcement.get("previous_ip") or "").strip()
    new_ip = str(announcement.get("new_ip") or "").strip()
    ts = int(announcement.get("timestamp") or 0)
    nonce = str(announcement.get("nonce") or "").strip()
    signature = str(announcement.get("signature") or "").strip()

    if not (node_id and previous_ip and new_ip and ts and nonce and signature):
        return False, "missing required migration fields"

    if abs(time.time() - ts) > window_sec:
        return False, "announcement expired or clock drift exceeded"

    secret = _secret()
    if not secret:
        return False, "no cluster secret configured"

    expected_sig = hmac.new(
        secret.encode(),
        f"mesh-ip-migration:{node_id}:{previous_ip}:{new_ip}:{ts}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return False, "invalid cryptographic signature"

    # Proof of previous mesh fleet membership:
    # previous_ip MUST already be known to this node's known_peers or archive!
    known_ips = load_known_peer_ips()
    if previous_ip not in known_ips:
        return False, f"previous IP {previous_ip} was never an acknowledged mesh fleet member"

    return True, "verified"


def apply_migration_announcement(announcement: dict) -> bool:
    """Verify and apply a peer's IP migration announcement."""
    ok, reason = verify_migration_announcement(announcement)
    if not ok:
        log.warning("Rejected IP migration announcement: %s", reason)
        return False

    new_ip = announcement["new_ip"]
    prev_ip = announcement["previous_ip"]
    node_id = announcement.get("node_id", "peer")

    remember_peer(new_ip)
    log.info(
        "Mesh IP migration accepted: node '%s' migrated from %s -> %s (verified fleet member)",
        node_id,
        prev_ip,
        new_ip,
    )
    return True


def check_and_announce_self_migration(
    current_ip: str | None = None,
    peer_ips: list[str] | None = None,
) -> dict | None:
    """Check if local node IP has changed ('know thyself'), and announce to mesh peers."""
    if not current_ip:
        current_ip = get_local_ip()
    if not current_ip or current_ip in (_LOOPBACK_V4, "localhost"):
        return None

    ident = load_self_identity()
    last_ip = ident.get("last_known_ip", "")

    # First run: record current IP without announcing
    if not last_ip:
        ident["last_known_ip"] = current_ip
        ident["history"] = [{"ip": current_ip, "timestamp": time.time()}]
        save_self_identity(ident)
        return None

    # No change
    if current_ip == last_ip:
        return None

    # IP CHANGED! Node knows thyself:
    node_id = ident.get("node_id") or ("win" if sys.platform == "win32" else "mac")
    role = ident.get("role") or node_id
    announcement = create_migration_announcement(
        node_id=node_id,
        previous_ip=last_ip,
        new_ip=current_ip,
        role=role,
    )

    log.info(
        "Self IP migration detected ('know thyself'): %s -> %s. Announcing to peers...",
        last_ip,
        current_ip,
    )

    ident["last_known_ip"] = current_ip
    ident.setdefault("history", []).append({
        "ip": current_ip,
        "previous_ip": last_ip,
        "timestamp": time.time(),
    })
    save_self_identity(ident)

    targets = peer_ips or list(load_known_peer_ips())
    token = _control_plane_token()
    ctx = _get_ssl_context()
    payload_bytes = json.dumps(announcement).encode("utf-8")

    for peer in targets:
        if peer in (current_ip, last_ip, _LOOPBACK_V4, "localhost"):
            continue
        req = urllib.request.Request(
            f"https://{peer}:8443/api/peer-event",
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
        )
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=1.0) as resp:
                if resp.status == 200:
                    log.info("Announced IP migration to peer %s: 200 OK", peer)
        except Exception as e:
            log.debug("Peer %s unreachable during migration announcement: %s", peer, e)

    return announcement


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


def peer_trusted(ip: str, role: str = "") -> bool:
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    if ip in load_known_peer_ips():
        return True
    if is_strict_config_mode():
        if prompt_confirm_peer(ip, role or "unknown"):
            return True
        return False
    if os.environ.get("ORAMA_APPROVE_DISCOVERY", "").strip().lower() in ("1", "true", "yes"):
        remember_peer(ip)
        return True
    if os.environ.get("ORAMA_DISCOVERY_RELAXED", "").strip().lower() in ("1", "true", "yes"):
        remember_peer(ip)
        return True
    # Shibboleth: dynamically verify whether peer holds the valid control plane token / CA
    if verify_peer_shibboleth(ip):
        log.info("Peer %s dynamically authenticated via control plane shibboleth", ip)
        remember_peer(ip)
        return True
    # Interactive fallback prompt if TTY is present
    if prompt_confirm_peer(ip, role or "unknown"):
        return True
    return False


def _block_untrusted_peer(ip: str, role: str, blocked: list[str]) -> None:
    nonce, sig = initiate_handshake(ip)
    blocked.append(ip)
    log.warning(
        "New peer %s (%s) — acknowledge before persist:\n"
        "   ORAMA_APPROVE_DISCOVERY=1 discover.py   # one-shot approve\n"
        "   discover.py --ack-peer %s --nonce %s --signature %s",
        ip,
        role,
        ip,
        nonce,
        sig,
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
        if peer_trusted(ip, role):
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
            continue
        if peer_trusted(ip, "win_peer"):
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


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Manage Orama mesh peer trust and discovery trust policies.")
    parser.add_argument("--list", action="store_true", help="List all known trusted peer IPs.")
    parser.add_argument("--trust-ip", metavar="IP", help="Add and trust an IP address.")
    parser.add_argument("--remove-ip", metavar="IP", help="Remove an IP address from trusted peers.")
    parser.add_argument("--shibboleth-probe", metavar="IP", help="Run cryptographic shibboleth probe against IP.")
    parser.add_argument("--yes", "-y", action="store_true", help="Confirm without prompting.")
    args = parser.parse_args()

    if args.list:
        ips = sorted(load_known_peer_ips())
        print(f"Known trusted peer IPs ({len(ips)}):")
        for ip in ips:
            print(f"  - {ip}")
        return 0

    if args.trust_ip:
        ip = args.trust_ip.strip()
        if not args.yes and sys.stdin.isatty():
            ans = input(f"Add {ip} to trusted peers ({KNOWN_PEERS.name})? [y/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print("Aborted.")
                return 1
        remember_peer(ip)
        print(f"✅ Trusted peer {ip} added to {KNOWN_PEERS}.")
        return 0

    if args.remove_ip:
        ip = args.remove_ip.strip()
        if forget_peer(ip):
            print(f"✅ Removed {ip} from {KNOWN_PEERS}.")
            return 0
        else:
            print(f"⚠️  {ip} not found in {KNOWN_PEERS}.")
            return 1

    if args.shibboleth_probe:
        ip = args.shibboleth_probe.strip()
        ok = verify_peer_shibboleth(ip)
        if ok:
            print(f"✅ Shibboleth PASS: {ip} holds valid cluster credentials.")
            return 0
        else:
            print(f"❌ Shibboleth FAIL: {ip} did not return 200 with cluster credentials.")
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
