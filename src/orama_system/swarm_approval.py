"""Server-side swarm launch approval (P5) with legacy grandfathering."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Any

_PREVIEW_TTL_SEC = 300
_MAX_CACHE_SIZE = 32
_cache: dict[str, tuple[str, float, dict[str, Any]]] = {}
_in_flight: dict[str, tuple[str, float, dict[str, Any], str]] = {}
_dispatch_lock = threading.Lock()


def _secret() -> str:
    """Return the first configured HMAC secret for swarm approval tokens."""
    for key in ("ORAMA_SWARM_APPROVAL_SECRET", "ORAMA_CONTROL_PLANE_TOKEN", "GOSSIP_SHARED_SECRET"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return ""


def strict_mode() -> bool:
    """Return whether preview credentials are mandatory for every launch."""
    return os.environ.get("ORAMA_SWARM_STRICT", "").strip().lower() in ("1", "true", "yes")


def grandfather_legacy() -> bool:
    """Return whether boolean-only approval is still accepted (non-strict legacy)."""
    if strict_mode():
        return False
    return os.environ.get("ORAMA_SWARM_LEGACY_APPROVE", "0").strip().lower() in ("1", "true", "yes")


def _fingerprint(preview: dict[str, Any]) -> str:
    """Hash the dispatch-relevant preview fields used for drift detection."""
    payload = {
        "objective": preview.get("objective"),
        "assignments": preview.get("assignments"),
        "task_type": preview.get("task_type"),
        "optimize_for": preview.get("optimize_for"),
        "preferred_device": preview.get("preferred_device"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]


def _sign(preview_id: str, fingerprint: str) -> str:
    """Compute the HMAC approval token for a preview id and fingerprint."""
    secret = _secret()
    if not secret:
        return ""
    return hmac.new(
        secret.encode(),
        f"swarm:{preview_id}:{fingerprint}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _prune_cache() -> None:
    """Drop expired previews and enforce the in-memory cache size cap."""
    now = time.time()
    for preview_id, (_, ts, _) in list(_cache.items()):
        if now - ts > _PREVIEW_TTL_SEC:
            _cache.pop(preview_id, None)
    while len(_cache) > _MAX_CACHE_SIZE:
        oldest = min(_cache.items(), key=lambda item: item[1][1])[0]
        _cache.pop(oldest, None)


def cached_preview(preview_id: str | None) -> dict[str, Any] | None:
    """Return the preview stored at issue time, without consuming it."""
    if not preview_id:
        return None
    entry = _cache.get(preview_id)
    if not entry:
        return None
    _fp, ts, stored = entry
    if time.time() - ts > _PREVIEW_TTL_SEC:
        _cache.pop(preview_id, None)
        return None
    if not isinstance(stored, dict):
        return None
    return copy.deepcopy(stored)


def issue_approval(preview: dict[str, Any]) -> dict[str, Any]:
    """Mint ``preview_id`` / ``approval_token`` credentials for a preview payload."""
    if not _secret():
        raise ValueError("swarm approval secret is not configured")
    _prune_cache()
    preview_id = secrets.token_hex(16)
    fp = _fingerprint(preview)
    _cache[preview_id] = (fp, time.time(), copy.deepcopy(preview))
    _prune_cache()
    token = _sign(preview_id, fp)
    if not token:
        raise ValueError("swarm approval secret is not configured")
    return {"preview_id": preview_id, "approval_token": token, "strict_mode": strict_mode()}


def check_launch(
    *,
    approved: bool,
    preview_id: str | None,
    approval_token: str | None,
    preview: dict[str, Any],
) -> None:
    """Validate approval credentials and preview drift without consuming the cache entry."""
    omitted = preview_id is None and approval_token is None
    preview_id = (preview_id or "").strip()
    approval_token = (approval_token or "").strip()
    if grandfather_legacy() and approved and omitted:
        return
    if not preview_id or not approval_token:
        raise ValueError("preview_id and approval_token required (call /api/swarm/preview first)")
    if not approved:
        raise ValueError("explicit approval required for swarm launch")
    entry = _cache.get(preview_id)
    if not entry:
        raise ValueError("preview expired or unknown — call /api/swarm/preview again")
    fp, ts, _cached = entry
    if time.time() - ts > _PREVIEW_TTL_SEC:
        _cache.pop(preview_id, None)
        raise ValueError("preview expired")
    if _fingerprint(preview) != fp:
        raise ValueError("preview drift — regenerate preview")
    expected = _sign(preview_id, fp)
    try:
        token_ok = hmac.compare_digest(expected, approval_token)
    except (TypeError, ValueError):
        token_ok = False
    if not token_ok:
        raise ValueError("invalid approval_token")


def consume_launch(preview_id: str | None) -> None:
    """Atomically consume a checked preview id before dispatch."""
    normalized = (preview_id or "").strip()
    entry = _cache.pop(normalized, None)
    if not entry:
        raise ValueError("preview expired or unknown — call /api/swarm/preview again")
    _fp, ts, _cached = entry
    if time.time() - ts > _PREVIEW_TTL_SEC:
        raise ValueError("preview expired")


def claim_launch_for_dispatch(
    *,
    approved: bool,
    preview_id: str | None,
    approval_token: str | None,
    preview: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Validate approval and atomically remove the preview from the cache.

    Returns the stored preview payload and a ``launch_attempt_id`` that must
    be passed to ``finalize_launch_claim`` or ``release_launch_claim``. Only one
    in-flight claim exists per ``preview_id``; concurrent callers lose the race
    when the cache entry is already claimed.
    """
    with _dispatch_lock:
        check_launch(
            approved=approved,
            preview_id=preview_id,
            approval_token=approval_token,
            preview=preview,
        )
        normalized = (preview_id or "").strip()
        if normalized in _in_flight:
            raise ValueError("preview expired or unknown — call /api/swarm/preview again")
        entry = _cache.pop(normalized, None)
        if not entry:
            raise ValueError("preview expired or unknown — call /api/swarm/preview again")
        fp, ts, stored = entry
        if time.time() - ts > _PREVIEW_TTL_SEC:
            raise ValueError("preview expired")
        attempt_id = secrets.token_hex(16)
        _in_flight[normalized] = (fp, ts, stored, attempt_id)
        return copy.deepcopy(stored), attempt_id


def finalize_launch_claim(preview_id: str | None, attempt_id: str) -> None:
    """Drop a reserved preview after every downstream job post succeeded."""
    normalized = (preview_id or "").strip()
    with _dispatch_lock:
        entry = _in_flight.get(normalized)
        if entry and entry[3] == attempt_id:
            _in_flight.pop(normalized, None)


def release_launch_claim(
    preview_id: str | None,
    attempt_id: str,
    *,
    restore_to_cache: bool,
) -> None:
    """End a failed dispatch attempt.

    When ``restore_to_cache`` is true, every accepted job passed
    ``cancellation_allows_restore`` (durable ``cancelled`` plus an allowed
    containment pair, or mixed-deploy absence of both fields). The preview
    returns to the approval cache for one retry. When false (orphaned jobs
    remain, including ``cli`` / ``unresolved``), the approval stays consumed.
    """
    normalized = (preview_id or "").strip()
    with _dispatch_lock:
        entry = _in_flight.pop(normalized, None)
        if not entry or entry[3] != attempt_id:
            return
        fp, ts, stored, _attempt = entry
        if restore_to_cache:
            _cache[normalized] = (fp, ts, stored)
            _prune_cache()


def verify_launch(
    *,
    approved: bool,
    preview_id: str | None,
    approval_token: str | None,
    preview: dict[str, Any],
) -> None:
    """Validate credentials and atomically consume the preview (legacy verify path)."""
    check_launch(
        approved=approved,
        preview_id=preview_id,
        approval_token=approval_token,
        preview=preview,
    )
    if grandfather_legacy() and approved and preview_id is None and approval_token is None:
        return
    consume_launch(preview_id)
