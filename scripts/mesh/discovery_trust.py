#!/usr/bin/env python3
"""P6 discovery trust — grandfather known peers, handshake new ones."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import socket
import ssl
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]
    import msvcrt
else:
    msvcrt = None  # type: ignore[assignment]

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


class DiscoveryStateError(RuntimeError):
    """Raise when durable trust authority cannot be safely interpreted."""


def _trust_state_lock_path() -> Path:
    """Return the lock shared by all trust and migration-state writers."""
    return LOCAL / ".discovery-trust.lock"


def _try_lock_file(handle) -> None:
    """Acquire the portable advisory lock held across a state transaction."""
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    handle.seek(0)
    handle.write("0")
    handle.flush()
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)


def _unlock_file(handle) -> None:
    """Release the portable advisory lock held across a state transaction."""
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_UN)
        return
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def _state_transaction(timeout: float = 10.0):
    """Serialize short read-modify-write operations across CLI and portal processes."""
    lock_path = _trust_state_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    handle = open(lock_path, "a+", encoding="utf-8")
    locked = False
    try:
        while True:
            try:
                _try_lock_file(handle)
                locked = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("discovery trust state lock timeout")
                time.sleep(0.02)
        yield
    finally:
        if locked:
            _unlock_file(handle)
        handle.close()


def _load_json(path: Path) -> dict:
    """Read optional JSON state, returning an empty mapping when unavailable."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_authority_mapping(path: Path, label: str) -> dict:
    """Load one authoritative state mapping without treating corruption as first run."""
    if not path.exists():
        return {}
    if not path.is_file():
        raise DiscoveryStateError(f"{label} state is not a regular file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiscoveryStateError(f"{label} state cannot be read; repair it before retrying") from exc
    if not isinstance(data, dict):
        raise DiscoveryStateError(f"{label} state must be a JSON object; repair it before retrying")
    return data


def _require_string_list(data: dict, field: str, label: str) -> list[str]:
    """Return an optional authority list only when all persisted entries are strings."""
    value = data.get(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DiscoveryStateError(f"{label} state has invalid {field}; repair it before retrying")
    return value


def _load_known_peer_store() -> dict:
    """Load and validate trust authority before any admission or revocation decision."""
    store = _load_authority_mapping(KNOWN_PEERS, "known peers")
    for field in ("ips", "approved_ips", "revoked_ips"):
        _require_string_list(store, field, "known peers")
    return store


def _load_self_identity_unlocked() -> dict:
    """Load validated self identity while the shared state transaction is held."""
    data = _load_authority_mapping(SELF_IDENTITY_FILE, "self identity")
    if not data:
        return {
            "node_id": "win" if sys.platform == "win32" else "mac",
            "role": "win" if sys.platform == "win32" else "mac",
            "last_known_ip": "",
            "history": [],
        }
    for field in ("node_id", "role", "last_known_ip"):
        if field in data and not isinstance(data[field], str):
            raise DiscoveryStateError(f"self identity state has invalid {field}; repair it before retrying")
    if "history" in data and not isinstance(data["history"], list):
        raise DiscoveryStateError("self identity state has invalid history; repair it before retrying")
    if "migration_generation" in data and (
        not isinstance(data["migration_generation"], int)
        or isinstance(data["migration_generation"], bool)
        or data["migration_generation"] < 0
    ):
        raise DiscoveryStateError("self identity state has invalid migration generation; repair it before retrying")
    pending = data.get("pending_migration")
    if pending is not None:
        if not isinstance(pending, dict):
            raise DiscoveryStateError("self identity state has invalid pending migration; repair it before retrying")
        if "new_ip" in pending and not isinstance(pending["new_ip"], str):
            raise DiscoveryStateError("self identity state has invalid pending migration; repair it before retrying")
        for field in ("recipients", "all_recipients"):
            if field in pending:
                _require_string_list(pending, field, "self identity pending migration")
    return data


def _save_self_identity_unlocked(data: dict) -> None:
    """Persist an already-validated self identity inside the shared transaction."""
    _save_json(SELF_IDENTITY_FILE, data)


def _secret() -> str:
    """Resolve the migration signing key independently of bearer credentials."""
    for key in ("MESH_MIGRATION_SECRET", "GOSSIP_SHARED_SECRET"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    data = _load_json(ROOT / ".local" / "mesh-secrets.json")
    secret = (data.get("MESH_MIGRATION_SECRET") or data.get("GOSSIP_SHARED_SECRET") or "").strip()
    return str(secret) if secret else ""


def _save_json(path: Path, data: dict) -> None:
    """Atomically replace private state after flushing its durable contents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _ips_from_archive() -> set[str]:
    """Extract grandfathered peer candidates from the local topology archive."""
    data = _load_json(ARCHIVE)
    ips: set[str] = set()
    for url in (data.get("endpoints") or {}).values():
        if not isinstance(url, str):
            continue
        for part in url.replace("http://", "").replace("https://", "").split("/"):
            if part and part[0].isdigit():
                ips.add(part.split(":")[0])
    return ips


def _control_plane_tokens() -> list[str]:
    """Use the shared peer-first outbound credential contract, never signing secrets."""
    source = str(Path(__file__).resolve().parents[2] / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from utils.control_plane_auth import outbound_control_plane_tokens

    return outbound_control_plane_tokens()


def _control_plane_token() -> str:
    """Return the first canonical outbound candidate for compatibility callers."""
    return next(iter(_control_plane_tokens()), "")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect before credentials can leave the verified origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Leave redirects as HTTP errors rather than constructing another request."""
        return None


def _open_peer(request: urllib.request.Request, context: ssl.SSLContext, timeout: float):
    """Open one verified HTTPS request with redirects and ambient proxies disabled."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(), urllib.request.HTTPSHandler(context=context)
    )
    return opener.open(request, timeout=timeout)


def _find_ca_file() -> str | None:
    """Locate the explicitly configured or existing cluster trust bundle."""
    env_ca = os.environ.get("ORAMA_LAN_CA_FILE", "").strip()
    if env_ca and Path(env_ca).is_file():
        return env_ca
    if (LOCAL / "certs").is_dir():
        for ca_p in sorted((LOCAL / "certs").glob("*.pem")):
            if ca_p.is_file():
                return str(ca_p)
    for ca_path in (
        str(LOCAL / "orama-lan-ca.pem"),
        str(ROOT / "certs" / "ca.pem"),
        str(Path.home() / ".openclaw" / "certs" / "ca.pem"),
    ):
        if Path(ca_path).is_file():
            return ca_path
    return None


def _get_ssl_context() -> ssl.SSLContext | None:
    """Return SSL context validating against cluster CA if present.

    Always fails closed (returns None) when no CA is available or CA loading
    fails. Bearer-bearing discovery probes and migration announcements must
    never use an unverified TLS context — including when
    ORAMA_DISCOVERY_RELAXED=1 (that flag only relaxes peer auto-trust, not TLS).
    """
    ca_file = _find_ca_file()
    if ca_file:
        try:
            ctx = ssl.create_default_context(cafile=ca_file)
            return ctx
        except Exception as exc:
            log.warning("Failed to load cluster CA from %s: %s", ca_file, exc)

    log.warning("Cluster CA unavailable; refusing insecure SSL context")
    return None


def is_strict_config_mode() -> bool:
    """Return whether strict configuration peers mode is active.

    When active, discovery only trusts IPs explicitly listed in config files
    or environment configuration, disabling automatic shibboleth auto-trust.
    """
    return os.environ.get("ORAMA_STRICT_CONFIG_PEERS", "").strip().lower() in ("1", "true", "yes")


def _ips_from_env() -> set[str]:
    """Read explicitly configured peer-address allowlists."""
    ips: set[str] = set()
    for key in ("WIN_3080_IP", "WIN_5080_IP", "WIN_PEER_IPS", "PEER_IPS"):
        for part in os.environ.get(key, "").split(","):
            part = part.strip()
            if part:
                ips.add(part)
    return ips


def verify_peer_shibboleth(ip: str, timeout: float = 0.5) -> bool:
    """Probe peer over TLS with known control plane token (shibboleth).

    Performs a 2-stage verification against authenticated route /api/peer-inbox:
      1. Probe without token: MUST fail with HTTP 401 Unauthorized.
      2. Probe with canonical outbound candidates: MUST return HTTP 200 OK.

    TLS authenticates the server; status codes only check portal access behavior.

    If no trusted CA context is available, verification fails closed to prevent token
    disclosure over untrusted TLS. Timeout is clamped to prevent subnet scan delays.
    """
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout < float("inf"):
        return False
    timeout = min(float(timeout), 0.5)
    try:
        with socket.create_connection((ip, 8443), timeout=timeout):
            pass
    except Exception:
        return False

    ctx = _get_ssl_context()
    if ctx is None:
        log.warning("No cluster CA available; refusing unverified shibboleth probe for %s", ip)
        return False

    tokens = _control_plane_tokens()
    if not tokens:
        return False

    # Stage 1: Unauthenticated probe must be rejected with 401
    unauth_req = urllib.request.Request(f"https://{ip}:8443/api/peer-inbox")
    try:
        with _open_peer(unauth_req, ctx, timeout) as resp:
            # If an unauthenticated request returns 200, the peer does not enforce auth (rogue/untrusted)
            log.warning("Peer %s returned %d to unauthenticated probe; untrusted", ip, resp.status)
            return False
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            log.debug("Peer %s unauthenticated probe returned HTTP %d (expected 401)", ip, exc.code)
            return False
    except Exception:
        return False

    # Stage 2: Authenticated probe must return 200 OK
    for token in tokens:
        auth_req = urllib.request.Request(f"https://{ip}:8443/api/peer-inbox")
        auth_req.add_header("Authorization", f"Bearer {token}")
        try:
            with _open_peer(auth_req, ctx, timeout) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as exc:
            if exc.code not in (401, 403):
                return False
        except OSError:
            return False
    return False


def _ips_from_last_discovery() -> set[str]:
    """Read historical peer candidates without treating them as live probes."""
    data = _load_json(OPENCLAW_STATE)
    ips: set[str] = set()
    for ep in (data.get("endpoints") or {}).values():
        if isinstance(ep, dict) and ep.get("ip"):
            ips.add(str(ep["ip"]))
    return ips


def load_known_peer_ips() -> set[str]:
    """Combine allowed sources and subtract explicit revocations last."""
    store = _load_known_peer_store()
    ips = set(store.get("approved_ips") or [])
    ips |= _ips_from_env()
    if not is_strict_config_mode():
        ips |= set(store.get("ips") or [])
        ips |= _ips_from_archive()
        ips |= _ips_from_last_discovery()
    return {ip for ip in ips if ip and ip not in (_LOOPBACK_V4, "localhost")} - set(store.get("revoked_ips") or [])


def remember_peer(ip: str) -> None:
    """Persist admission only when neither explicit revocation nor strict policy forbids it."""
    if not ip:
        return
    with _state_transaction():
        store = _load_known_peer_store()
        ips = set(store.get("ips") or [])
        if ip in set(store.get("revoked_ips") or []):
            raise ValueError("peer explicitly revoked; operator reapproval required")
        if is_strict_config_mode() and ip not in set(store.get("approved_ips") or []) | _ips_from_env():
            raise ValueError("strict configuration requires explicit peer approval")
        ips.add(ip)
        store["ips"] = sorted(ips)
        store["updated_at"] = time.time()
        _save_json(KNOWN_PEERS, store)


def forget_peer(ip: str) -> bool:
    """Revoke effective trust across all positive sources, including rediscovery."""
    if not ip:
        return False
    with _state_transaction():
        store = _load_known_peer_store()
        ips = set(store.get("ips") or [])
        ips.discard(ip)
        store["ips"] = sorted(ips)
        store["revoked_ips"] = sorted(set(store.get("revoked_ips") or []) | {ip})
        store["updated_at"] = time.time()
        _save_json(KNOWN_PEERS, store)
        ident = _load_self_identity_unlocked()
        pending = ident.get("pending_migration")
        if isinstance(pending, dict) and _remove_recipients(pending, {ip}):
            # Revocation is an explicit operator decision. It removes the peer from
            # both the current retry and every future superseding announcement.
            _save_self_identity_unlocked(ident)
    return True


def prompt_confirm_peer(ip: str, role: str = "peer") -> bool:
    """Prompt the operator interactively to confirm whether to trust an unknown peer IP.

    Returns True and remembers peer if user confirms; False otherwise.
    Safe for non-interactive execution: returns False immediately if stdin is not a TTY.
    """
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        log.warning("Refusing non-IP peer %s (%s)", ip, role)
        return False
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
            approve_peer(ip)
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
    with _state_transaction():
        return _load_self_identity_unlocked()


def _remove_recipients(pending: dict, removed: set[str]) -> bool:
    """Remove explicitly retired recipients from every durable migration audience."""
    changed = False
    for field in ("recipients", "all_recipients"):
        recipients = pending.get(field)
        if not isinstance(recipients, list):
            continue
        retained = [peer for peer in recipients if peer not in removed]
        if retained != recipients:
            pending[field] = retained
            changed = True
    return changed


def save_self_identity(data: dict) -> None:
    """Atomically persist observed address and pending recipient state."""
    with _state_transaction():
        _save_self_identity_unlocked(data)


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
      1. Envelope structure, field types, and timestamp freshness.
      2. IP address validity (must be valid non-loopback addresses).
      3. Cryptographic signature under cluster secret.
      4. Fleet membership: previous_ip MUST be an established member in known_peers or archive.
    """
    if not isinstance(announcement, dict):
        return False, "invalid envelope"
    if announcement.get("type") != "mesh_ip_migration_announcement":
        return False, "unexpected event type"

    node_id = str(announcement.get("node_id") or "").strip()
    previous_ip = str(announcement.get("previous_ip") or "").strip()
    new_ip = str(announcement.get("new_ip") or "").strip()

    try:
        ts = int(announcement.get("timestamp") or 0)
    except (TypeError, ValueError):
        return False, "invalid timestamp"

    nonce = str(announcement.get("nonce") or "").strip()
    signature = str(announcement.get("signature") or "").strip()

    if not (node_id and previous_ip and new_ip and ts and nonce and signature):
        return False, "missing required migration fields"

    for label, ip_str in (("previous_ip", previous_ip), ("new_ip", new_ip)):
        try:
            addr = ipaddress.ip_address(ip_str)
            if addr.is_loopback:
                return False, f"{label} cannot be a loopback address"
        except ValueError:
            return False, f"invalid {label} address format"

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
    if new_ip in set(_load_json(KNOWN_PEERS).get("revoked_ips") or []):
        return False, "destination explicitly revoked"
    if is_strict_config_mode() and new_ip not in known_ips:
        return False, "strict configuration requires explicit destination approval"

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


def migration_digest(announcement: dict) -> str:
    """Bind an acknowledgement to the exact canonical signed announcement."""
    return hashlib.sha256(json.dumps(announcement, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _prepare_self_migration(current_ip: str, peer_ips: list[str] | None) -> tuple[dict, str, list[str], int] | None:
    """Create or reload a pending migration while holding state only for local mutation."""
    with _state_transaction():
        ident = _load_self_identity_unlocked()
        last_ip = ident.get("last_known_ip", "")
        if not last_ip:
            ident["last_known_ip"] = current_ip
            ident["history"] = [{"ip": current_ip, "timestamp": time.time()}]
            _save_self_identity_unlocked(ident)
            return None

        pending = ident.get("pending_migration") or {}
        if pending and "all_recipients" not in pending:
            log.warning("Legacy migration lacks its full audience; operator reconciliation required before retry")
            return None
        revoked = set(_load_known_peer_store().get("revoked_ips") or [])
        if pending and _remove_recipients(pending, revoked):
            _save_self_identity_unlocked(ident)
        if current_ip == last_ip and not pending:
            return None

        node_id = ident.get("node_id") or ("win" if sys.platform == "win32" else "mac")
        role = ident.get("role") or node_id
        announcement = create_migration_announcement(
            node_id=node_id,
            previous_ip=last_ip,
            new_ip=current_ip,
            role=role,
        )
        if pending and pending.get("new_ip") == current_ip:
            generation = ident.get("migration_generation")
            if generation is None:
                generation = 1
                ident["migration_generation"] = generation
                _save_self_identity_unlocked(ident)
            return announcement, last_ip, list(pending.get("recipients") or []), generation

        targets = sorted(load_known_peer_ips()) if peer_ips is None else peer_ips
        stale = list(pending.get("all_recipients") or pending.get("recipients") or [])
        delivery_targets = sorted({
            peer for peer in [*targets, *stale]
            if peer not in (current_ip, last_ip, _LOOPBACK_V4, "localhost") and peer not in revoked
        })
        generation = int(ident.get("migration_generation", 0)) + 1
        ident["migration_generation"] = generation
        ident["pending_migration"] = {
            "new_ip": current_ip,
            "all_recipients": list(delivery_targets),
            "recipients": list(delivery_targets),
        }
        _save_self_identity_unlocked(ident)
        return announcement, last_ip, delivery_targets, generation


def _settle_migration_ack(current_ip: str, peer: str, generation: int) -> bool:
    """Record one exact acknowledgement only if its migration and recipient remain current."""
    with _state_transaction():
        ident = _load_self_identity_unlocked()
        pending = ident.get("pending_migration")
        if (
            not isinstance(pending, dict)
            or pending.get("new_ip") != current_ip
            or ident.get("migration_generation") != generation
        ):
            return False
        revoked = set(_load_known_peer_store().get("revoked_ips") or [])
        if peer in revoked:
            if _remove_recipients(pending, {peer}):
                _save_self_identity_unlocked(ident)
            return False
        recipients = pending.get("recipients")
        if not isinstance(recipients, list) or peer not in recipients:
            return False
        recipients.remove(peer)
        _save_self_identity_unlocked(ident)
        return True


def _commit_migration_if_complete(current_ip: str, last_ip: str, generation: int) -> bool:
    """Commit a migration only when the current durable retry audience is empty."""
    with _state_transaction():
        ident = _load_self_identity_unlocked()
        pending = ident.get("pending_migration")
        if (
            not isinstance(pending, dict)
            or pending.get("new_ip") != current_ip
            or ident.get("migration_generation") != generation
        ):
            return False
        if pending.get("recipients"):
            return False
        ident.pop("pending_migration", None)
        ident["last_known_ip"] = current_ip
        ident.setdefault("history", []).append({
            "ip": current_ip,
            "previous_ip": last_ip,
            "timestamp": time.time(),
        })
        _save_self_identity_unlocked(ident)
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

    prepared = _prepare_self_migration(current_ip, peer_ips)
    if prepared is None:
        return None
    announcement, last_ip, delivery_targets, generation = prepared

    log.info(
        "Self IP migration detected ('know thyself'): %s -> %s. Announcing to peers...",
        last_ip,
        current_ip,
    )

    ack_count = 0
    if delivery_targets:
        ctx = _get_ssl_context()
        if ctx is None:
            log.warning("No cluster CA available; cannot announce migration over TLS")
        else:
            tokens = _control_plane_tokens()
            payload_bytes = json.dumps({
                "type": announcement["type"],
                "source": announcement.get("node_id", ""),
                "ts": int(announcement.get("timestamp", 0)),
                "data": announcement,
            }).encode("utf-8")

            for peer in delivery_targets:
                for token in tokens:
                    req = urllib.request.Request(
                        f"https://{peer}:8443/api/peer-event",
                        data=payload_bytes,
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                    )
                    try:
                        with _open_peer(req, ctx, 1.0) as resp:
                            ack = json.loads(resp.read(4096))
                            if isinstance(ack, dict) and resp.status == 200 and ack.get("ok") is True and ack.get("migration_id") == migration_digest(announcement):
                                ack_count += _settle_migration_ack(current_ip, peer, generation)
                            break
                    except urllib.error.HTTPError as exc:
                        if exc.code not in (401, 403):
                            break
                    except (OSError, ValueError):
                        log.debug("Peer migration delivery failed; retaining pending recipient")
                        break

    # A recipient is retired only by an exact acknowledgement or explicit operator edit.
    if _commit_migration_if_complete(current_ip, last_ip, generation):
        log.info(
            "Self IP migration committed to self-identity.json (%d peer acks)",
            ack_count,
        )
    else:
        log.warning(
            "Self IP migration still has pending recipients; keeping last_known_ip=%s to retry next run",
            last_ip,
        )

    return announcement


def handshake_signature(ip: str, nonce: str) -> str:
    """Sign a discovery acknowledgement using the migration-secret lane."""
    secret = _secret()
    if not secret:
        return ""
    return hmac.new(
        secret.encode(),
        f"discovery-handshake:{ip}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _pending_entry(ip: str) -> dict | None:
    """Load a fresh handshake challenge and remove expired challenges."""
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
    """Consume a matching, fresh signed discovery challenge once."""
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
    """Persist a new challenge for operator-mediated peer acknowledgement."""
    nonce = secrets.token_hex(8)
    pending = _load_json(PENDING_HANDSHAKES)
    pending[ip] = {"nonce": nonce, "ts": time.time()}
    _save_json(PENDING_HANDSHAKES, pending)
    sig = handshake_signature(ip, nonce)
    return nonce, sig


def peer_trusted(ip: str, role: str = "") -> bool:
    """Evaluate revocation before all automatic or configured admission paths."""
    if not ip or ip in (_LOOPBACK_V4, "localhost"):
        return True
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        log.warning("Refusing non-IP peer %s (%s)", ip, role or "unknown")
        return False
    if ip in set(_load_json(KNOWN_PEERS).get("revoked_ips") or []):
        return False
    if ip in load_known_peer_ips():
        return True
    if is_strict_config_mode():
        if prompt_confirm_peer(ip, role or "unknown"):
            return True
        return False
    if os.environ.get("ORAMA_APPROVE_DISCOVERY", "").strip().lower() in ("1", "true", "yes"):
        try:
            remember_peer(ip)
        except ValueError:
            return False
        return True
    if os.environ.get("ORAMA_DISCOVERY_RELAXED", "").strip().lower() in ("1", "true", "yes"):
        try:
            remember_peer(ip)
        except ValueError:
            return False
        return True
    # Shibboleth: dynamically verify whether peer holds the valid control plane token / CA
    if verify_peer_shibboleth(ip):
        log.info("Peer %s dynamically authenticated via control plane shibboleth", ip)
        try:
            remember_peer(ip)
        except ValueError:
            return False
        return True
    # Interactive fallback prompt if TTY is present
    if prompt_confirm_peer(ip, role or "unknown"):
        return True
    return False


def _block_untrusted_peer(ip: str, role: str, blocked: list[str]) -> None:
    """Record a blocked peer and advertise the explicit approval workflow."""
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
            if ip not in (_LOOPBACK_V4, "localhost"):
                try:
                    remember_peer(ip)
                except ValueError:
                    _block_untrusted_peer(ip, role, blocked)
                    out[role] = None
                    continue
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
            if ip not in (_LOOPBACK_V4, "localhost"):
                try:
                    remember_peer(ip)
                except ValueError:
                    _block_untrusted_peer(ip, "win_peer", blocked)
                    continue
            peers_in.append(peer)
            continue
        _block_untrusted_peer(ip, "win_peer", blocked)
    out["win_peers"] = peers_in
    return out, blocked


def ack_peer(ip: str, nonce: str, signature: str) -> bool:
    """Admit an acknowledged challenge only within current trust policy."""
    if not verify_handshake(ip, nonce, signature):
        return False
    try:
        remember_peer(ip)
    except ValueError:
        return False
    return True


def approve_peer(ip: str) -> None:
    """Apply explicit operator approval, including lifting a prior revocation."""
    ipaddress.ip_address(ip)
    with _state_transaction():
        store = _load_known_peer_store()
        store["revoked_ips"] = sorted(set(store.get("revoked_ips") or []) - {ip})
        store["ips"] = sorted(set(store.get("ips") or []) | {ip})
        store["approved_ips"] = sorted(set(store.get("approved_ips") or []) | {ip})
        _save_json(KNOWN_PEERS, store)


def main() -> int:
    """Manage explicit approval, revocation and diagnostic probes from the CLI."""
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
        approve_peer(ip)
        print(f"✅ Trusted peer {ip} added to {KNOWN_PEERS}.")
        return 0

    if args.remove_ip:
        ip = args.remove_ip.strip()
        if forget_peer(ip):
            print(f"✅ Revoked {ip} across configured, archived and discovered trust sources; explicit --trust-ip required to reapprove.")
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
