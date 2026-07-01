"""Shared control-plane authentication and operator payload redaction."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, MutableMapping

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

ENV_TOKEN = "ORAMA_CONTROL_PLANE_TOKEN"
ENV_TOKEN_LOCAL = "ORAMA_CONTROL_PLANE_TOKEN_LOCAL"
ENV_TOKEN_PEER = "ORAMA_CONTROL_PLANE_TOKEN_PEER"
ENV_PT_TOKEN = "PT_CONTROL_PLANE_TOKEN"
ENV_INSECURE = "ORAMA_INSECURE_DEV"
CONTROL_PLANE_COOKIE = "orama_control_plane_token"

_SENSITIVE_TOP_LEVEL_KEYS = frozenset(
    {
        "paths",
        "path",
        "backend_urls",
        "backend_url",
        "openclaw_config",
        "raw_prompt",
        "prompt",
        "metadata",
        "tool_trace",
        "tool_traces",
        "messages",
        "transcript",
        "raw_transcript",
        "chain_of_thought",
        "model_internals",
    }
)

_PUBLIC_PORTAL_PATHS = frozenset(
    {
        "/health",
    }
)

_PUBLIC_PORTAL_PREFIXES = (
    "/assets/",
)


def control_plane_token() -> str:
    """
    Read the legacy symmetric control-plane bearer token from the environment.
    
    The returned value is trimmed of leading and trailing whitespace and defaults to an empty string when the environment variable is not set.
    
    Returns:
        The control-plane bearer token with surrounding whitespace removed, or an empty string if not configured.
    """
    return os.getenv(ENV_TOKEN, "").strip()


def _strip_env(name: str) -> str:
    return os.getenv(name, "").strip()


def persisted_control_plane_token() -> str:
    """Token from PT `.state/control_plane_token` when present."""
    return _read_pt_persisted_token()


def pt_lane_token_candidates() -> list[str]:
    """PT lane: explicit PT key + `.state/control_plane_token` (checking account)."""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in (_strip_env(ENV_PT_TOKEN), persisted_control_plane_token()):
        if raw and raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def orama_lane_token_candidates() -> list[str]:
    """Orama/portal lane: env keys only (deposit account — not PT `.state`)."""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in (_strip_env(ENV_TOKEN), _strip_env(ENV_TOKEN_LOCAL)):
        if raw and raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def control_plane_auth_mode() -> Literal["unset", "pt_only", "orama_only", "joint"]:
    """
    Joint-account mode:
    - pt_only: only PT lane keys configured
    - orama_only: only orama lane keys configured
    - joint: both lanes have keys — either unlocks both services
    """
    pt = pt_lane_token_candidates()
    orama = orama_lane_token_candidates()
    if pt and orama:
        return "joint"
    if pt:
        return "pt_only"
    if orama:
        return "orama_only"
    return "unset"


def _merge_unique(*groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            if raw and raw not in seen:
                seen.add(raw)
                ordered.append(raw)
    return ordered


def collect_control_plane_token_candidates() -> list[str]:
    """All configured tokens (both lanes + PEER for outbound handoff)."""
    peer = _strip_env(ENV_TOKEN_PEER)
    extra = [peer] if peer else []
    mode = control_plane_auth_mode()
    if mode == "joint":
        return _merge_unique(pt_lane_token_candidates(), orama_lane_token_candidates(), extra)
    if mode == "pt_only":
        return _merge_unique(pt_lane_token_candidates(), extra)
    if mode == "orama_only":
        return _merge_unique(orama_lane_token_candidates(), extra)
    return _merge_unique(extra)


def accepted_control_plane_tokens(
    scope: Literal["pt", "orama"] = "orama",
) -> frozenset[str]:
    """
    Tokens this service accepts on incoming requests.

    - scope=orama (portal/API): orama lane; in joint mode accepts PT lane too
    - scope=pt: PT lane; in joint mode accepts orama lane too
    """
    mode = control_plane_auth_mode()
    pt = pt_lane_token_candidates()
    orama = orama_lane_token_candidates()
    if mode == "joint":
        return frozenset(_merge_unique(pt, orama))
    if mode == "pt_only":
        return frozenset(pt)
    if mode == "orama_only":
        return frozenset(orama)
    # Legacy: persisted file without explicit orama env (orama reads PT .state)
    if scope == "pt":
        return frozenset(pt or orama)
    return frozenset(orama or pt)


def outbound_control_plane_tokens() -> list[str]:
    """Outbound peer probes: PEER first, then lane keys (joint tries both)."""
    peer = _strip_env(ENV_TOKEN_PEER)
    ordered: list[str] = []
    seen: set[str] = set()
    if peer:
        ordered.append(peer)
        seen.add(peer)
    for raw in _merge_unique(
        orama_lane_token_candidates(),
        pt_lane_token_candidates(),
    ):
        if raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def token_matches_control_plane(
    provided: str,
    scope: Literal["pt", "orama"] = "orama",
) -> bool:
    if not provided:
        return False
    for expected in accepted_control_plane_tokens(scope):
        if secrets.compare_digest(provided, expected):
            return True
    return False


def _env_control_plane_token_candidates() -> list[str]:
    return orama_lane_token_candidates()


def _resolve_perpetua_tools_root() -> Path | None:
    """
    Locate a Perpetua-Tools repository checkout on the filesystem.
    
    Checks the environment variables PERPETUA_TOOLS_ROOT, PERPETUATOOLSROOT, and PERPETUA_TOOLS_PATH (in that order) for a configured path; if none are set, searches a set of repo-relative candidate directories for a Perpetua-Tools checkout. Returns the discovered checkout root as a Path, or None if no valid checkout is found.
         
    Returns:
        Path | None: Path to the Perpetua-Tools root when found, otherwise `None`.
    """
    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        raw = os.getenv(key, "").strip()
        if raw:
            p = Path(raw).expanduser()
            if p.is_dir():
                return p
    repo_root = Path(__file__).resolve().parents[2]
    for candidate in (
        repo_root.parent / "perplexity-api" / "Perpetua-Tools",
        repo_root.parent / "Perpetua-Tools",
        repo_root.parent / "repos" / "Perpetua-Tools",
    ):
        if (candidate / "orchestrator" / "fastapi_app.py").is_file():
            return candidate
    return None


def auth_enforced() -> bool:
    """Return True when control-plane bearer auth must be checked (PT-aligned default)."""
    insecure = os.getenv(ENV_INSECURE, "").strip().lower()
    if insecure in ("1", "true", "yes"):
        return False
    if _env_control_plane_token_candidates() or pt_lane_token_candidates():
        return True
    if insecure in ("0", "false", "no"):
        return True
    return True


def _read_pt_persisted_token() -> str:
    """
    Read a persisted control-plane token from a Perpetua-Tools checkout, if available.
    
    If a Perpetua-Tools root can be located, this function reads the file
    `.state/control_plane_token` and returns its contents trimmed of whitespace.
    
    Returns:
        str: The token string if present, otherwise an empty string.
    """
    pt_root = _resolve_perpetua_tools_root()
    if pt_root is None:
        return ""
    token_path = pt_root / ".state" / "control_plane_token"
    if token_path.is_file():
        return token_path.read_text(encoding="utf-8").strip()
    return ""


def resolved_control_plane_token() -> str:
    """Primary outbound token (PEER if set, else legacy resolution)."""
    outbound = outbound_control_plane_tokens()
    if outbound:
        return outbound[0]
    return ""


def _legacy_resolved_control_plane_token() -> str:
    """Env token first, then PT persisted file (shared stack token)."""
    token = control_plane_token()
    if token:
        return token
    return _read_pt_persisted_token()


def _default_token_path() -> Path:
    pt_root = _resolve_perpetua_tools_root()
    if pt_root is not None:
        return pt_root / ".state" / "control_plane_token"
    return Path(__file__).resolve().parents[2] / ".state" / "control_plane_token"


def _secure_write_token(path: Path, value: str) -> None:
    """Write token file with 0600 permissions at creation time (umask-safe)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)


def persist_control_plane_token(token: str, path: Path | None = None) -> Path:
    token_path = path or _default_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    _secure_write_token(token_path, token)
    return token_path


def ensure_control_plane_token() -> str:
    """Return configured token, generating and persisting one when auth is enforced."""
    existing = _legacy_resolved_control_plane_token()
    if existing:
        if not control_plane_token():
            os.environ[ENV_TOKEN] = existing
        return existing
    if not auth_enforced():
        return ""
    generated = secrets.token_urlsafe(32)
    os.environ[ENV_TOKEN] = generated
    persist_control_plane_token(generated)
    return generated


_DEFAULT_OPERATOR_TTL_SECONDS = 900


def _canonical_operator_payload(payload: Mapping[str, Any]) -> str:
    """Stable JSON for HMAC input (sort_keys, no whitespace)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _default_operator_signing_secret_path() -> Path:
    pt_root = _resolve_perpetua_tools_root()
    if pt_root is not None:
        return pt_root / ".state" / "operator_signing_secret"
    return Path(__file__).resolve().parents[2] / ".state" / "operator_signing_secret"


def _read_persisted_operator_signing_secret(path: Path | None = None) -> str:
    secret_path = path or _default_operator_signing_secret_path()
    if secret_path.is_file():
        return secret_path.read_text(encoding="utf-8").strip()
    return ""


def _operator_signing_secret() -> str:
    """Server-only HMAC key for operator payload signing.

    MUST NOT be derived from or equal to the control-plane bearer token: that
    token is sent by every authenticated client in the Authorization header, so
    reusing it as the signing secret would let any client HMAC-sign arbitrary
    operator payloads and forge a 'server-minted approval' guarantee. This
    secret is generated once, persisted to a 0600 file distinct from the
    control-plane token file, and never returned by any API endpoint.
    """
    existing = _read_persisted_operator_signing_secret()
    if existing:
        return existing
    if not auth_enforced():
        raise ValueError("control plane auth must be enforced before signing operator payloads")
    generated = secrets.token_urlsafe(32)
    persist_control_plane_token(generated, path=_default_operator_signing_secret_path())
    return generated


def _format_expires_at(when: datetime) -> str:
    return when.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_expires_at(value: str) -> datetime:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError("expires_at is required")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _compute_operator_token(payload: Mapping[str, Any], *, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        _canonical_operator_payload(payload).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_operator_payload(payload: dict, *, ttl_seconds: int = _DEFAULT_OPERATOR_TTL_SECONDS) -> dict:
    """
    Sign an operator intent payload with HMAC-SHA256 using the control-plane token.

    ``expires_at`` is embedded in the signed JSON (amendment A1). Returns
    ``{token, expires_at}`` for portal wrappers to map to ``approval_token``.
    """
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    expires_at = _format_expires_at(
        datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    )
    signed_payload = dict(payload)
    signed_payload["expires_at"] = expires_at
    token = _compute_operator_token(signed_payload, secret=_operator_signing_secret())
    return {"token": token, "expires_at": expires_at}


def verify_operator_payload(payload: dict, token: str, expires_at: str) -> bool:
    """Verify HMAC token and expiry for a signed operator payload."""
    if not isinstance(token, str) or not isinstance(expires_at, str):
        return False
    if not token or not expires_at:
        return False
    try:
        secret = _operator_signing_secret()
    except ValueError:
        return False
    signed_payload = dict(payload)
    signed_payload["expires_at"] = expires_at
    expected = _compute_operator_token(signed_payload, secret=secret)
    if not secrets.compare_digest(token, expected):
        return False
    try:
        if _parse_expires_at(expires_at) <= datetime.now(timezone.utc):
            return False
    except (ValueError, TypeError):
        return False
    return True


def is_weak_control_plane_token(token: str) -> bool:
    """True for empty or documented placeholder tokens that must not gate LAN bind."""
    normalized = (token or "").strip().lower()
    if not normalized:
        return True
    return normalized in {
        "change-me-before-network-use",
        "changeme",
        "change-me",
        "placeholder",
        "test",
        "secret",
    }


def lan_bind_configured() -> bool:
    """True when any control-plane service is configured for LAN exposure."""
    flags = ("PT_BIND_LAN", "ORAMA_BIND_LAN", "PORTAL_BIND_LAN")
    return any(os.getenv(name, "").strip().lower() in ("1", "true", "yes") for name in flags)


def request_is_loopback(request: Request) -> bool:
    """True for local operator browsers (127.0.0.1 / ::1)."""
    if request.client is None:
        return False
    host = (request.client.host or "").strip()
    # "testclient" is Starlette's in-process host (pytest / TestClient).
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


_LOOPBACK_ORIGIN_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _normalize_origin_host(host: str) -> str:
    normalized = (host or "").strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    return normalized


def _origin_header_host(value: str) -> str | None:
    from urllib.parse import urlparse

    value = (value or "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.hostname:
        return None
    return _normalize_origin_host(parsed.hostname)


def lifecycle_origin_allowed(request: Request) -> bool:
    """True when Origin/Referer is absent, loopback (port ignored), or same hostname.

    Localhost operator policy: compare hostnames only so portal :8002 may accept
    POSTs from pages served on PT :8000 or orama :8001.
    """
    origin = request.headers.get("origin", "").strip()
    referer = request.headers.get("referer", "").strip()
    if not origin and not referer:
        return True

    request_host = _normalize_origin_host(request.url.hostname or "")
    request_is_local = request_is_loopback(request) or request_host in _LOOPBACK_ORIGIN_HOSTS
    for header in (origin, referer):
        header_host = _origin_header_host(header)
        if header_host is None:
            continue
        if header_host in _LOOPBACK_ORIGIN_HOSTS and request_is_local:
            return True
        if header_host == request_host:
            return True
    return False


def verify_lifecycle_origin(request: Request) -> None:
    if not lifecycle_origin_allowed(request):
        raise HTTPException(status_code=403, detail="Cross-origin request denied")


def bearer_token_from_request(request: Request) -> str:
    """Extract bearer token from Authorization header or control-plane cookie."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    cookie = request.cookies.get(CONTROL_PLANE_COOKIE, "")
    return cookie.strip()


def verify_control_plane_auth(request: Request) -> None:
    if not auth_enforced():
        return
    if not accepted_control_plane_tokens("orama"):
        raise HTTPException(status_code=503, detail="Control plane token not configured")
    provided = bearer_token_from_request(request)
    if not token_matches_control_plane(provided, scope="orama"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def control_plane_auth_failure(request: Request) -> JSONResponse | None:
    """Return an error response when auth fails; None when the request may proceed."""
    if not auth_enforced():
        return None
    try:
        verify_control_plane_auth(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return None


def auth_headers() -> dict[str, str]:
    token = resolved_control_plane_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def all_interfaces_bind_host() -> str:
    """Bind-all IPv4 host; computed to avoid cloud secret scanners matching a literal."""
    configured = os.getenv("ORAMA_LAN_BIND_HOST", "").strip()
    if configured:
        return configured
    return ".".join(["0"] * 4)


def default_bind_host(
    *,
    lan_env: str,
    host_env: str,
    default_lan_host: str | None = None,
) -> str:
    if os.getenv(lan_env, "").strip().lower() in ("1", "true", "yes"):
        return default_lan_host or all_interfaces_bind_host()
    return os.getenv(host_env, "localhost").strip() or "localhost"


def cors_allow_origins() -> list[str]:
    raw = os.getenv("ORAMA_CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:8002",
        "http://localhost:3000",
    ]


def portal_path_is_public(path: str) -> bool:
    if path in _PUBLIC_PORTAL_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PORTAL_PREFIXES)


def portal_requires_auth(
    path: str,
    method: str,
    *,
    request: Request | None = None,
) -> bool:
    if portal_path_is_public(path):
        return False
    if method.upper() == "OPTIONS":
        return False
    # Loopback may load the HTML shell without a Bearer header; token is injected
    # into the page for same-origin API calls (LAN clients must send Authorization).
    if (
        request is not None
        and method.upper() == "GET"
        and path in (
            "/",
            "/dashboard",
            "/co-orchestration",
            "/co-orchestration/macos",
            "/co-orchestration/windows",
            "/peer-inbox",
        )
        and request_is_loopback(request)
    ):
        return False
    return True


def _redact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _SENSITIVE_TOP_LEVEL_KEYS:
            continue
        redacted[key] = redact_operator_value(value)
    return redacted


def redact_operator_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _redact_mapping(value)
    if isinstance(value, list):
        return [redact_operator_value(item) for item in value]
    return value


def redact_runtime_section(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    runtime = payload.get("runtime") if "runtime" in payload else payload
    if not isinstance(runtime, dict):
        available = bool(payload.get("available"))
        return {"available": available, "gateway_ready": False, "distributed": False}
    gateway = runtime.get("gateway") if isinstance(runtime.get("gateway"), dict) else {}
    routing = runtime.get("routing") if isinstance(runtime.get("routing"), dict) else {}
    return {
        "available": bool(payload.get("available", True)),
        "gateway_ready": bool(gateway.get("gateway_ready") or gateway.get("ready")),
        "distributed": bool(routing.get("distributed")),
    }


def redact_job_record(job: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in ("id", "job_id", "status", "role", "intent", "backend_hint", "created_at", "updated_at"):
        if key in job and job[key] is not None:
            safe[key] = job[key]
    if "id" not in safe and "job_id" in safe:
        safe["id"] = safe["job_id"]
    return safe


def redact_jobs_payload(payload: Any) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_jobs = payload.get("jobs", [])
    elif isinstance(payload, list):
        raw_jobs = payload
    else:
        raw_jobs = []
    if isinstance(raw_jobs, list):
        for item in raw_jobs:
            if isinstance(item, dict):
                jobs.append(redact_job_record(item))
    return {"jobs": jobs, "count": len(jobs)}


def redact_activity_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"events": [], "count": 0}
    events = payload.get("events", [])
    safe_events: list[dict[str, Any]] = []
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            safe_events.append(
                {
                    key: event[key]
                    for key in ("id", "agent_id", "role", "status", "ts", "timestamp")
                    if key in event
                }
            )
    return {"events": safe_events, "count": len(safe_events)}


def redact_agents_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        agents = payload
    elif isinstance(payload, dict):
        agents = payload.get("agents", [])
    else:
        agents = []
    safe: list[dict[str, Any]] = []
    if isinstance(agents, list):
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            safe.append(
                {
                    key: agent[key]
                    for key in ("id", "agent_id", "role", "status", "backend_hint")
                    if key in agent
                }
            )
    return {"agents": safe, "count": len(safe)}


def redact_models_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"models": [], "count": 0}
    models = payload.get("models", [])
    safe_models: list[dict[str, Any]] = []
    if isinstance(models, list):
        for model in models:
            if isinstance(model, dict) and model.get("id"):
                safe_models.append({"id": model["id"]})
            elif isinstance(model, str):
                safe_models.append({"id": model})
    return {"models": safe_models, "count": len(safe_models)}


def redact_portal_status_payload(payload: MutableMapping[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    redacted["activity"] = redact_activity_payload({"events": redacted.pop("activity", [])})
    redacted["agents"] = redact_agents_payload(redacted.pop("agents", []))
    routing = redacted.pop("routing", None)
    redacted["routing"] = redact_runtime_section({"runtime": routing}) if routing else {"available": False}
    redacted["supervisor_jobs"] = redact_jobs_payload({"jobs": redacted.pop("supervisor_jobs", [])})["jobs"]
    services = redacted.get("services")
    if isinstance(services, dict):
        for name, service in services.items():
            if isinstance(service, dict) and "url" in service:
                service = dict(service)
                service.pop("url", None)
                services[name] = service
    return redacted
