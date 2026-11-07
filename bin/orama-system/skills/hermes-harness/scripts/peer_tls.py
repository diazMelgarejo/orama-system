"""peer_tls.py -- per-stack TLS trust for peer-portal requests (stdlib only).

Trust is scoped to peer portal calls only: nothing here touches
os.environ, SSL_CERT_FILE, or any process-global SSL default.

Settings (read from the environment on every call):
  PEER_CA_FILE               path to a PEM CA bundle. Peer https calls verify
                             chain AND hostname/IP-SAN against it.
  PEER_CA_SHA256             operator-confirmed SHA-256 (hex) of the one CA certificate in
                             PEER_CA_FILE. When set, the file is read ONCE, must hold exactly one
                             PEM block (a CERTIFICATE with that fingerprint), and the context is
                             built from those same verified DER bytes, never from the path again,
                             so a file swapped after the check cannot become trusted.
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
import re
import ssl
import threading
from typing import Any
from urllib.parse import urlsplit

PEER_CA_ENV = "PEER_CA_FILE"
PEER_PINS_ENV = "PEER_PINNED_FINGERPRINTS"
PEER_CA_SHA256_ENV = "PEER_CA_SHA256"
_PEM_MARKER = re.compile(rb"-----BEGIN ([A-Z0-9 ]+)-----")
_PEM_CERT = re.compile(rb"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.DOTALL)


class PeerTrustError(OSError):
    """Peer TLS verification failed; no credential may be sent."""


def normalize_fingerprint(value: str) -> str:
    """Return a SHA-256 fingerprint as 64 lowercase hex characters with separators stripped; raise ValueError when malformed."""
    fp = "".join(ch for ch in (value or "") if ch not in ": \t").lower()
    if len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
        raise ValueError("fingerprint must be 64 hex chars (SHA-256)")
    return fp


def pinned_fingerprints() -> set[str]:
    """Return the set of pinned fingerprints from the environment; raise PeerTrustError when any entry is invalid."""
    pins: set[str] = set()
    for part in (os.environ.get(PEER_PINS_ENV) or "").split(","):
        if part.strip():
            try:
                pins.add(normalize_fingerprint(part))
            except ValueError as exc:
                raise PeerTrustError(f"invalid {PEER_PINS_ENV} entry: {exc}") from exc
    return pins


def peer_ca_file() -> str:
    """Return the configured peer CA bundle path, or an empty string when unset."""
    return (os.environ.get(PEER_CA_ENV) or "").strip()


def cert_fingerprint(der: bytes) -> str:
    """Return the SHA-256 hex fingerprint of a DER-encoded certificate."""
    return hashlib.sha256(der).hexdigest()


def peer_ca_sha256() -> str:
    """Return the normalised PEER_CA_SHA256, or an empty string when unset; raise PeerTrustError when malformed."""
    raw = (os.environ.get(PEER_CA_SHA256_ENV) or "").strip()
    if not raw:
        return ""
    try:
        return normalize_fingerprint(raw)
    except ValueError as exc:
        raise PeerTrustError(f"invalid {PEER_CA_SHA256_ENV}: {exc}") from exc


def _verified_ca_der(data: bytes, expected: str) -> bytes:
    """Return the DER of the single CERTIFICATE block in *data* when its SHA-256 equals *expected*.

    Any other or additional PEM block (a second certificate, a TRUSTED CERTIFICATE, a key) is refused,
    because the TLS library would otherwise load it as a further trust anchor.
    """
    markers = _PEM_MARKER.findall(data)
    if markers != [b"CERTIFICATE"]:
        raise PeerTrustError(f"{PEER_CA_ENV} must hold exactly one CERTIFICATE block when {PEER_CA_SHA256_ENV} is set")
    match = _PEM_CERT.search(data)
    if match is None:
        raise PeerTrustError(f"{PEER_CA_ENV} has a malformed CERTIFICATE block")
    try:
        der = ssl.PEM_cert_to_DER_cert(
            "-----BEGIN CERTIFICATE-----" + match.group(1).decode("ascii") + "-----END CERTIFICATE-----"
        )
    except (ValueError, UnicodeDecodeError) as exc:
        raise PeerTrustError(f"{PEER_CA_ENV} has a malformed CERTIFICATE block") from exc
    if cert_fingerprint(der) != expected:
        raise PeerTrustError(f"{PEER_CA_ENV} does not match {PEER_CA_SHA256_ENV}; refusing to trust it")
    return der


def _ca_context(cafile: str) -> ssl.SSLContext:
    """Build a verifying SSL context that trusts the given CA file; raise PeerTrustError when it cannot be loaded.

    The file is read once. With PEER_CA_SHA256 set, only the DER bytes that passed the fingerprint check
    are loaded, so replacing the file after the check changes nothing.
    """
    try:
        with open(cafile, "rb") as handle:
            data = handle.read()
        expected = peer_ca_sha256()
        if expected:
            cadata: str | bytes = _verified_ca_der(data, expected)
        else:
            cadata = data.decode("ascii") if b"-----BEGIN" in data else data
        return ssl.create_default_context(cadata=cadata)
    except (OSError, ssl.SSLError, UnicodeDecodeError) as exc:
        raise PeerTrustError(f"cannot load {PEER_CA_ENV}: {exc}") from exc


def _fetch_leaf_pem(host: str, port: int, timeout: float) -> str:
    """Fetch the certificate a peer presents using a handshake only (no request data); raise PeerTrustError on failure."""
    # Handshake only; reads the presented certificate, sends no request data.
    try:
        return ssl.get_server_certificate((host, port), timeout=timeout)
    except (OSError, ssl.SSLError) as exc:
        raise PeerTrustError(f"cannot fetch peer certificate from {host}:{port}: {exc}") from exc


def _pinned_context(pem: str) -> ssl.SSLContext:
    """Build a verifying TLS 1.2+ context that trusts only the given PEM leaf certificate (hostname still checked)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cadata=pem)
    partial = getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
    if partial:
        ctx.verify_flags |= partial  # leaf itself may be the trust anchor
    return ctx


_cache: dict[tuple[str, int, str, str, str], ssl.SSLContext] = {}
_cache_lock = threading.Lock()


def context_for(host: str, port: int, timeout: float = 8.0) -> ssl.SSLContext:
    """Return the SSL context for a peer, honouring pins first and then the CA file, otherwise the default verified context; raise PeerTrustError when trust cannot be established."""
    pins = pinned_fingerprints()
    cafile = peer_ca_file()
    key = (host, port, cafile, ",".join(sorted(pins)), peer_ca_sha256())
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
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError as exc:
        raise PeerTrustError(f"invalid peer URL: {exc}") from None
    if parts.scheme != "https" or not hostname:
        return {}
    if not peer_ca_file() and not pinned_fingerprints():
        return {}  # nothing configured: urllib's own default verified context
    try:
        port = parts.port or 443
    except ValueError as exc:
        raise PeerTrustError(f"invalid peer URL port: {exc}") from None
    return {"context": context_for(hostname, port, timeout=timeout)}


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
    """Drop all cached SSL contexts (mainly for tests)."""
    with _cache_lock:
        _cache.clear()
