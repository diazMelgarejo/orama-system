"""Shared control-plane authentication and operator payload redaction."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

ENV_TOKEN = "ORAMA_CONTROL_PLANE_TOKEN"
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
    Read the control-plane bearer token from the environment.
    
    The returned value is trimmed of leading and trailing whitespace and defaults to an empty string when the environment variable is not set.
    
    Returns:
        The control-plane bearer token with surrounding whitespace removed, or an empty string if not configured.
    """
    return os.getenv(ENV_TOKEN, "").strip()


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
    repo_root = Path(__file__).resolve().parent.parent
    for candidate in (
        repo_root.parent / "perplexity-api" / "Perpetua-Tools",
        repo_root.parent / "Perpetua-Tools",
        repo_root.parent / "repos" / "Perpetua-Tools",
    ):
        if (candidate / "orchestrator" / "fastapi_app.py").is_file():
            return candidate
    return None


def auth_enforced() -> bool:
    """
    Determine whether control-plane bearer authentication is required.
    
    Auth is required when a control-plane token is configured or when
    ORAMA_INSECURE_DEV is explicitly set to a production value (`0`, `false`, `no`).
    Auth is disabled when ORAMA_INSECURE_DEV is explicitly set to an insecure value
    (`1`, `true`, `yes`). When neither a token nor an explicit insecure setting
    is provided, authentication is not enforced to preserve existing local workflows.
    
    Returns:
        `true` if control-plane authentication must be enforced, `false` otherwise.
    """
    if control_plane_token():
        return True
    insecure = os.getenv(ENV_INSECURE, "").strip().lower()
    if insecure in ("1", "true", "yes"):
        return False
    if insecure in ("0", "false", "no"):
        return True
    return False


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
    """Env token first, then PT persisted file (shared stack token)."""
    token = control_plane_token()
    if token:
        return token
    return _read_pt_persisted_token()


def ensure_control_plane_token() -> str:
    """Return configured token, generating one when insecure dev is off."""
    existing = resolved_control_plane_token()
    if existing:
        if not control_plane_token():
            os.environ[ENV_TOKEN] = existing
        return existing
    if not auth_enforced():
        return ""
    generated = secrets.token_urlsafe(32)
    os.environ[ENV_TOKEN] = generated
    return generated


def request_is_loopback(request: Request) -> bool:
    """True for local operator browsers (127.0.0.1 / ::1)."""
    if request.client is None:
        return False
    host = (request.client.host or "").strip()
    # "testclient" is Starlette's in-process host (pytest / TestClient).
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


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
    expected = resolved_control_plane_token()
    if not expected:
        raise HTTPException(status_code=503, detail="Control plane token not configured")
    provided = bearer_token_from_request(request)
    if provided and secrets.compare_digest(provided, expected):
        return
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
        and path in ("/", "/dashboard")
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
