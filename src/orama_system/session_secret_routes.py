"""Write-only session key entry for the portal (operator ruling D5, 2026-11-27).

The page may learn which names are set and nothing else. ``orama_system.session_secrets`` seals every value under
the user's own key; these routes never return, log or repeat one:

* ``GET /api/session-secrets`` answers names and the word ``set``;
* ``PUT /api/session-secrets/{NAME}`` accepts one value and answers only that the name is set;
* ``POST /api/session-secrets/save`` is the one deliberate plain-text export and answers only the target kind and
  the file name;
* ``DELETE /api/session-secrets`` purges the sealed session file.

Authorisation is the same control-plane bearer check the portal's other ``/api`` routes use (the portal middleware
calls the same function as the outer gate), and every mutating route is rate limited per client inside this process.
The sealed store lives under the user's openclaw state directory, never the repository, and one session id is kept
for the life of this process.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path as NamePath, Request
from fastapi.responses import JSONResponse

from orama_system.session_secrets import (
    SessionSecrets,
    SessionSecretsError,
    key_provider_from_environment,
)
from utils.control_plane_auth import resolved_control_plane_token, verify_control_plane_auth

_NAME_PATTERN = r"^[A-Z][A-Z0-9_]{1,63}$"
_MAX_BODY_BYTES = 12_000
_WINDOW_SECONDS = 60.0
_WRITE_MAX_CALLS = 20
_SAVE_MAX_CALLS = 5
_PURGE_MAX_CALLS = 5

_BODY_TOO_LARGE = "the request body is too large for one key value"
_BODY_SHAPE = 'the body must be JSON of the shape {"value": "<the key>"}'
_NO_KEY_SOURCE = (
    "no session key source configured: set ORAMA_SESSION_KEY_MODE=dev-control-plane on a grandfathered "
    "development install, or inject a per-user key provider"
)
_KEY_SOURCE_UNAVAILABLE = (
    "the session key source is not usable: ORAMA_SESSION_KEY_MODE=dev-control-plane needs a control-plane token"
)
_SET_REFUSED = (
    "nothing was stored: the value is empty, longer than 8192 characters or contains a control character, "
    "or the existing session file cannot be opened"
)
_SAVE_REFUSED = (
    "nothing was written: no key is set in this session, the target file already exists, or the folder is not "
    "writable"
)
_UNREADABLE = "the session file cannot be opened with the current key; keys entered before a key change are lost"
_TOO_MANY = "too many session key requests; wait a minute and try again"

_STORES: dict[str, SessionSecrets] = {}
_CALLS: dict[str, list[float]] = {}


def _home_dir() -> Path:
    """Home directory for state: ``HOME`` first so tests and containers stay isolated."""
    override = os.environ.get("HOME")
    return Path(override) if override else Path.home()


def _state_dir() -> Path:
    """Sealed session files: the user's openclaw state folder, never the repository."""
    override = os.environ.get("ORAMA_SESSION_SECRETS_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return _home_dir() / ".openclaw" / "state" / "session-secrets"


def _repo_root() -> Path:
    """Repository root holding ``.env`` and ``.env.example``."""
    return Path(__file__).resolve().parents[2]


def _token_source() -> str:
    """The control-plane token the development key is derived from; never returned or logged."""
    return resolved_control_plane_token()


def _store() -> SessionSecrets:
    """One sealed store per state folder, carrying this process's session id."""
    folder = _state_dir()
    cached = _STORES.get(str(folder))
    if cached is not None:
        return cached
    try:
        provider = key_provider_from_environment(os.environ, _token_source)
    except SessionSecretsError:
        raise HTTPException(status_code=503, detail=_NO_KEY_SOURCE) from None
    try:
        provider.key()
    except SessionSecretsError:
        raise HTTPException(status_code=503, detail=_KEY_SOURCE_UNAVAILABLE) from None
    store = SessionSecrets(folder, provider)
    _STORES[str(folder)] = store
    return store


def _limit(request: Request, bucket: str, max_calls: int) -> None:
    """Allow ``max_calls`` per client and bucket in a one-minute window, in this process only."""
    host = request.client.host if request.client else "unknown"
    key = "%s:%s" % (host, bucket)
    now = time.monotonic()
    recent = [stamp for stamp in _CALLS.get(key, ()) if stamp > now - _WINDOW_SECONDS]
    if len(recent) >= max_calls:
        raise HTTPException(status_code=429, detail=_TOO_MANY)
    recent.append(now)
    _CALLS[key] = recent


def _no_store(payload: dict[str, Any]) -> JSONResponse:
    """Response that a browser and a proxy must never cache."""
    return JSONResponse(
        payload,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


async def _value_from_request(request: Request) -> str:
    """Read the body's value without letting a validation layer echo a rejected input anywhere."""
    raw = await request.body()
    if len(raw) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail=_BODY_TOO_LARGE)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=422, detail=_BODY_SHAPE) from None
    if not isinstance(payload, dict) or list(payload) != ["value"] or not isinstance(payload["value"], str):
        raise HTTPException(status_code=422, detail=_BODY_SHAPE)
    return payload["value"]


def _require_control_plane_auth(request: Request) -> None:
    """The same bearer check the portal's other ``/api`` routes use."""
    verify_control_plane_auth(request)


router = APIRouter(dependencies=[Depends(_require_control_plane_auth)])


@router.get("/api/session-secrets")
async def list_session_secrets() -> JSONResponse:
    """Names and the word ``set``; never a value."""
    store = _store()
    try:
        status = store.status()
    except SessionSecretsError:
        raise HTTPException(status_code=409, detail=_UNREADABLE) from None
    return _no_store({"names": list(status), "status": status})


@router.put("/api/session-secrets/{name}")
async def set_session_secret(
    request: Request,
    name: str = NamePath(min_length=2, max_length=64, pattern=_NAME_PATTERN),
) -> JSONResponse:
    """Store one value for this session; the answer says only that the name is set."""
    _limit(request, "write", _WRITE_MAX_CALLS)
    value = await _value_from_request(request)
    store = _store()
    try:
        store.set(name, value)
    except SessionSecretsError:
        raise HTTPException(status_code=422, detail=_SET_REFUSED) from None
    return _no_store({"name": name, "state": "set"})


@router.post("/api/session-secrets/save")
async def save_session_secrets(request: Request) -> JSONResponse:
    """Write one plain-text file on explicit request; the answer names the file, never a value."""
    _limit(request, "save", _SAVE_MAX_CALLS)
    store = _store()
    root = _repo_root()
    try:
        path, kind = store.save(root / ".env", root / ".env.example")
    except (SessionSecretsError, OSError):
        raise HTTPException(status_code=409, detail=_SAVE_REFUSED) from None
    return _no_store({"kind": kind, "file": path.name})


@router.delete("/api/session-secrets")
async def purge_session_secrets(request: Request) -> JSONResponse:
    """Remove this session's sealed file; the keys are gone, not hidden."""
    _limit(request, "purge", _PURGE_MAX_CALLS)
    _store().purge()
    return _no_store({"purged": True, "names": []})
