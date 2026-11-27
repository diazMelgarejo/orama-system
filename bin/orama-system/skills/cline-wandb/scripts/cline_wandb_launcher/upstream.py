"""The provider leg: URL and header rules, no redirects, and one bounded round trip."""
from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

MAX_RESPONSE_BYTES = 16 * 1024 * 1024


def resolve_upstream_url(upstream_base: str, path: str) -> str:
    """Resolve incoming path against upstream base URL, avoiding duplicated /v1 segments."""
    base = upstream_base.rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        subpath = path[3:]
    elif not base.endswith("/v1") and not path.startswith("/"):
        subpath = f"/{path}"
    else:
        subpath = path
    return f"{base}{subpath}"


class OversizeResponseError(RuntimeError):
    """The upstream response exceeded MAX_RESPONSE_BYTES."""


class TruncatedResponseError(RuntimeError):
    """The upstream response ended before its declared Content-Length."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the provider key must not travel to another origin."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_UPSTREAM_OPENER = urllib.request.build_opener(_NoRedirectHandler)

HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "proxy-connection", "te", "trailer", "transfer-encoding", "upgrade",
})


def hop_by_hop_names(headers: Any, *extra: str) -> frozenset[str]:
    """Lower-cased names to drop: fixed hop-by-hop fields, every field nominated by any Connection
    value, and any `extra` names the caller replaces itself."""
    names = set(HOP_BY_HOP) | {name.lower() for name in extra}
    for value in headers.get_all("Connection") or []:
        names.update(token.strip().lower() for token in str(value).split(",") if token.strip())
    return frozenset(names)


def is_identity_encoded(headers: Any) -> bool:
    """True when no Content-Encoding value names a coding other than identity."""
    values = headers.get_all("Content-Encoding") or []
    return all(token.strip().lower() in ("", "identity") for value in values for token in str(value).split(","))


def _read_bounded(stream: Any) -> bytes:
    data = stream.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise OversizeResponseError(f"upstream response exceeds {MAX_RESPONSE_BYTES} bytes")
    declared = stream.headers.get("Content-Length")
    if declared is not None and declared.strip().isdigit() and len(data) < int(declared.strip()):
        raise TruncatedResponseError(f"upstream response ended at {len(data)} of {declared.strip()} bytes")
    return data


def fetch(req: urllib.request.Request, timeout_ms: int) -> tuple[int, Any, bytes]:
    """One upstream round trip; a failure while reading ANY body (2xx or HTTPError) raises."""
    timeout_s = (timeout_ms / 1000.0) if timeout_ms else None
    try:
        with _UPSTREAM_OPENER.open(req, timeout=timeout_s) as resp:
            return resp.status, resp.headers, _read_bounded(resp)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.headers, _read_bounded(exc)
        finally:
            exc.close()
