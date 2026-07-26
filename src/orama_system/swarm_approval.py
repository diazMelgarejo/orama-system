"""Server-side swarm launch approval (P5) with legacy grandfathering."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

_PREVIEW_TTL_SEC = 300
_MAX_CACHE_SIZE = 32
_cache: dict[str, tuple[str, float, dict[str, Any]]] = {}


def _secret() -> str:
    for key in ("ORAMA_SWARM_APPROVAL_SECRET", "ORAMA_CONTROL_PLANE_TOKEN", "GOSSIP_SHARED_SECRET"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return ""


def strict_mode() -> bool:
    return os.environ.get("ORAMA_SWARM_STRICT", "").strip().lower() in ("1", "true", "yes")


def grandfather_legacy() -> bool:
    if strict_mode():
        return False
    return os.environ.get("ORAMA_SWARM_LEGACY_APPROVE", "1").strip().lower() not in ("0", "false", "no")


def _fingerprint(preview: dict[str, Any]) -> str:
    payload = {
        "objective": preview.get("objective"),
        "assignments": preview.get("assignments"),
        "task_type": preview.get("task_type"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]


def _sign(preview_id: str, fingerprint: str) -> str:
    secret = _secret()
    if not secret:
        return ""
    return hmac.new(
        secret.encode(),
        f"swarm:{preview_id}:{fingerprint}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _prune_cache() -> None:
    now = time.time()
    for preview_id, (_, ts, _) in list(_cache.items()):
        if now - ts > _PREVIEW_TTL_SEC:
            _cache.pop(preview_id, None)
    while len(_cache) > _MAX_CACHE_SIZE:
        oldest = min(_cache.items(), key=lambda item: item[1][1])[0]
        _cache.pop(oldest, None)


def issue_approval(preview: dict[str, Any]) -> dict[str, str]:
    _prune_cache()
    preview_id = secrets.token_hex(16)
    fp = _fingerprint(preview)
    _cache[preview_id] = (fp, time.time(), preview)
    token = _sign(preview_id, fp)
    return {"preview_id": preview_id, "approval_token": token, "strict_mode": strict_mode()}


def verify_launch(
    *,
    approved: bool,
    preview_id: str | None,
    approval_token: str | None,
    preview: dict[str, Any],
) -> None:
    if grandfather_legacy() and approved and not approval_token:
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
    if not hmac.compare_digest(expected, approval_token.strip()):
        raise ValueError("invalid approval_token")
    _cache.pop(preview_id, None)
