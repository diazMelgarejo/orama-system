"""peer_tls.py -- per-stack TLS trust for peer-portal requests (stdlib only).

Trust is scoped to peer portal calls only: nothing here touches
os.environ, SSL_CERT_FILE, or any process-global SSL default.

Settings (read from the environment on every call):
  PEER_CA_FILE               path to a PEM CA bundle. Peer https calls verify
                             chain AND hostname/IP-SAN against it.
  PEER_PINNED_FINGERPRINTS   comma list of SHA-256 hex fingerprints of peer
                             leaf certificates (colons / case ignored).

Resolution for an https peer (host, port):
  1. pins set: fetch the presented leaf (no application data is sent), and
     if its SHA-256 matches a pin, trust exactly that certificate as the
     anchor for a FULL verified handshake (validity period + hostname/IP-SAN
     still enforced). A mismatching leaf is a hard failure unless a CA file
     is also set, in which case the CA path below decides.
  2. CA file set: ssl.create_default_context(cafile=...), full verification.
  3. neither: the platform default context (public roots), full verification.
Failure raises PeerTrustError (an OSError); callers must not send tokens.
Verification is never disabled for the request itself.
"""
from __future__ import annotations

import hashlib
import os
import ssl
import threading
from typing import Any
from urllib.parse import urlsplit

PEER_CA_ENV = "PEER_CA_FILE"
PEER_PINS_ENV = "PEER_PINNED_FINGERPRINTS"


class PeerTrustError(OSError):
    """Peer TLS verification failed; no credential may be sent."""


def normalize_fingerprint(value: str) -> str:
    fp = "".join(ch for ch in (value or "") if ch not in ": \t").lower()
    if len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
        raise ValueError("fingerprint must be 64 hex chars (SHA-256)")
    return fp


def pinned_fingerprints() -> set[str]:
    pins: set[str] = set()
    for part in (os.environ.get(PEER_PINS_ENV) or "").split(","):
        if part.strip():
            try:
                pins.add(normalize_fingerprint(part))
            except ValueError as exc:
                raise PeerTrustError(f"invalid {PEER_PINS_ENV} entry: {exc}") from exc
    return pins


def peer_ca_file() -> str:
    return (os.environ.get(PEER_CA_ENV) or "").strip()


def cert_fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


def _ca_context(cafile: str) -> ssl.SSLContext:
    try:
        return ssl.create_default_context(cafile=cafile)
    except (OSError, ssl.SSLError) as exc:
        raise PeerTrustError(f"cannot load {PEER_CA_ENV}: {exc}") from exc


def _fetch_leaf_pem(host: str, port: int, timeout: float) -> str:
    # Handshake only; reads the presented certificate, sends no request data.
    try:
        return ssl.get_server_certificate((host, port), timeout=timeout)
    except (OSError, ssl.SSLError) as exc:
        raise PeerTrustError(f"cannot fetch peer certificate from {host}:{port}: {exc}") from exc


def _pinned_context(pem: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cadata=pem)
    partial = getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
    if partial:
        ctx.verify_flags |= partial  # leaf itself may be the trust anchor
    return ctx


_cache: dict[tuple[str, int, str, str], ssl.SSLContext] = {}
_cache_lock = threading.Lock()


def context_for(host: str, port: int, timeout: float = 8.0) -> ssl.SSLContext:
    pins = pinned_fingerprints()
    cafile = peer_ca_file()
    key = (host, port, cafile, ",".join(sorted(pins)))
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    if pins:
        pem = _fetch_leaf_pem(host, port, timeout)
        fp = cert_fingerprint(ssl.PEM_cert_to_DER_cert(pem))
        if fp in pins:
            ctx = _pinned_context(pem)
        elif cafile:
            ctx = _ca_context(cafile)
        else:
            raise PeerTrustError(
                f"peer {host}:{port} certificate fingerprint does not match any "
                f"pinned value (got sha256:{fp[:12]}...); refusing connection"
            )
    elif cafile:
        ctx = _ca_context(cafile)
    else:
        ctx = ssl.create_default_context()
    # Only cache CA/default contexts; pin contexts are re-derived so a
    # rotated leaf is re-checked against the pin list each process call.
    if not pins:
        with _cache_lock:
            _cache[key] = ctx
    return ctx


def urlopen_kwargs(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """Extra kwargs for urllib.request.urlopen: a per-request context for
    https peer URLs, nothing for http. Raises PeerTrustError on failure."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        return {}
    if not peer_ca_file() and not pinned_fingerprints():
        return {}  # nothing configured: urllib's own default verified context
    port = parts.port or 443
    return {"context": context_for(parts.hostname, port, timeout=timeout)}


def websocket_kwargs(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """Extra kwargs for websockets.connect: the same per-stack context as
    urlopen_kwargs, passed as ``ssl=`` for wss:// URLs, nothing for ws://.
    With neither PEER_CA_FILE nor pins set this returns {} so the library's
    default verified context applies (SSL_CERT_FILE still works there).
    Raises PeerTrustError on failure; callers must not send tokens."""
    if not url.startswith("wss://"):
        return {}
    kw = urlopen_kwargs("https://" + url[len("wss://"):], timeout)
    return {"ssl": kw["context"]} if kw else {}


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
