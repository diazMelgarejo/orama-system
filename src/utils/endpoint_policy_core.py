"""Shared endpoint policy core (cross-repo invariant module).

This module isolates the *security boundary logic* for model endpoint validation
so that multiple services (Perpetua-Tools, orama-system, agents) can reuse a
single canonical implementation.

Design goal:
- No raw stdlib exceptions escape this module
- All invalid inputs normalize to ModelEndpointPolicyError
- Host classification is deterministic and testable
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class ModelEndpointPolicyError(ValueError):
    pass


_ALLOWED_SCHEMES = {"http", "https"}


def host_allowed(host: str, *, allow_public: bool) -> bool:
    normalized = (host or "").strip().lower()
    if not normalized:
        return False

    if normalized in ("localhost", "::1") or normalized.endswith(".localhost"):
        return True

    if normalized.startswith("127."):
        return True

    try:
        addr = ipaddress.ip_address(normalized)
    except ValueError:
        return allow_public

    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped

    if addr.is_link_local:
        return False

    if addr.is_loopback or addr.is_private:
        return True

    return allow_public


def validate_base_url(url: str, *, allow_public: bool) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ModelEndpointPolicyError("empty endpoint URL")

    if "://" not in raw:
        raw = f"http://{raw}"

    try:
        parsed = urlparse(raw)

        scheme = (parsed.scheme or "").lower()
        if scheme not in _ALLOWED_SCHEMES:
            raise ModelEndpointPolicyError("invalid scheme")

        if parsed.username or parsed.password:
            raise ModelEndpointPolicyError("credentials not allowed")

        host = parsed.hostname
        if not host:
            raise ModelEndpointPolicyError("missing hostname")

        port = parsed.port

    except ValueError as exc:
        raise ModelEndpointPolicyError(f"invalid url: {exc}") from exc

    if not host_allowed(host, allow_public=allow_public):
        raise ModelEndpointPolicyError("host not allowed")

    if port is None:
        port = 443 if scheme == "https" else 80

    if ":" in host and not host.startswith("["):
        netloc = f"[{host}]:{port}"
    else:
        netloc = f"{host}:{port}"

    return f"{scheme}://{netloc}".rstrip("/")
