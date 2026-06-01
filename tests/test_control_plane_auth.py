#!/usr/bin/env python3
"""Regression tests for control-plane authentication and redaction."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

import api_server
import portal_server


def test_portal_operator_routes_require_token_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        denied = client.get("/api/status")
        allowed = client.get(
            "/api/status",
            headers={"Authorization": "Bearer portal-test-token"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    body = allowed.json()
    assert "paths" not in str(body)
    assert "runtime" not in body.get("routing", {})


def test_portal_health_stays_public_when_enforced(monkeypatch):
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "portal-test-token")

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_server_ultrathink_requires_token_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "orama-test-token")

    async def fake_call_with_fallback(prompt, model, max_tokens, temperature):
        return "ok", "http://redacted"

    monkeypatch.setattr(api_server, "_call_with_fallback", fake_call_with_fallback)

    with TestClient(api_server.app, raise_server_exceptions=False) as client:
        denied = client.post(
            "/ultrathink",
            json={
                "task_description": "test task",
                "optimize_for": "speed",
                "task_type": "analysis",
            },
        )
        allowed = client.post(
            "/ultrathink",
            json={
                "task_description": "test task",
                "optimize_for": "speed",
                "task_type": "analysis",
            },
            headers={"Authorization": "Bearer orama-test-token"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_api_server_runtime_state_redacts_payload(monkeypatch, tmp_path):
    state_file = tmp_path / "routing.json"
    state_file.write_text(
        '{"gateway": {"gateway_ready": true, "paths": {"secret": "/tmp"}}, '
        '"routing": {"distributed": true, "backend_url": "http://secret"}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("PT_AGENTS_STATE", str(state_file))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "orama-test-token")

    with TestClient(api_server.app, raise_server_exceptions=True) as client:
        response = client.get(
            "/runtime-state",
            headers={"Authorization": "Bearer orama-test-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    runtime = body["runtime"]
    assert runtime["gateway_ready"] is True
    assert runtime["distributed"] is True
    assert "paths" not in runtime
    assert "backend_url" not in str(body)


def test_auth_enforced_matrix(monkeypatch):
    from utils.control_plane_auth import auth_enforced

    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    assert auth_enforced() is False

    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "secret")
    assert auth_enforced() is True

    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    assert auth_enforced() is False

    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    assert auth_enforced() is True


def test_auth_headers_reads_pt_persisted_token(monkeypatch, tmp_path):
    from utils.control_plane_auth import auth_headers

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("pt-file-token", encoding="utf-8")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)

    headers = auth_headers()

    assert headers == {"Authorization": "Bearer pt-file-token"}


def test_auth_headers_discovers_pt_token_from_sibling_checkout(monkeypatch, tmp_path):
    """Portal must read PT token without PERPETUA_TOOLS_ROOT when repos are siblings."""
    from utils.control_plane_auth import auth_headers

    pt_root = tmp_path / "Perpetua-Tools"
    (pt_root / "orchestrator").mkdir(parents=True)
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("")
    token_path = pt_root / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("sibling-token", encoding="utf-8")

    orama_root = tmp_path / "orama-system"

    def _fake_resolve():
        """
        Find a sibling Perpetua-Tools checkout adjacent to the module's orama_root.
        
        Checks three candidate locations relative to `orama_root.parent`:
        perplexity-api/Perpetua-Tools, Perpetua-Tools, and repos/Perpetua-Tools. A candidate is accepted only if it contains the sentinel file orchestrator/fastapi_app.py.
        
        Returns:
        	Perpetua-Tools root (Path) if a valid checkout is found, `None` otherwise.
        """
        for candidate in (
            orama_root.parent / "perplexity-api" / "Perpetua-Tools",
            orama_root.parent / "Perpetua-Tools",
            orama_root.parent / "repos" / "Perpetua-Tools",
        ):
            if (candidate / "orchestrator" / "fastapi_app.py").is_file():
                return candidate
        return None

    monkeypatch.setattr("utils.control_plane_auth._resolve_perpetua_tools_root", _fake_resolve)
    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "ORAMA_CONTROL_PLANE_TOKEN"):
        monkeypatch.delenv(key, raising=False)

    assert auth_headers() == {"Authorization": "Bearer sibling-token"}


def test_verify_accepts_pt_persisted_token_without_env(monkeypatch, tmp_path):
    from utils.control_plane_auth import resolved_control_plane_token, verify_control_plane_auth

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("pt-only-token", encoding="utf-8")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)

    class _Req:
        headers = {"authorization": "Bearer pt-only-token"}

    verify_control_plane_auth(_Req())
    assert resolved_control_plane_token() == "pt-only-token"


def test_portal_loopback_index_injects_cp_fetch_when_enforced(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "loopback-ui-token")

    async def _fake_status():
        return {"services": {}, "routing": None, "activity": [], "agents": []}

    monkeypatch.setattr(portal_server, "api_status", _fake_status)

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        allowed = client.get("/")
        api_denied = client.get("/api/status")
        api_allowed = client.get(
            "/api/status",
            headers={"Authorization": "Bearer loopback-ui-token"},
        )

    assert allowed.status_code == 200
    assert "cpFetch" in allowed.text
    assert "loopback-ui-token" in allowed.text
    assert api_denied.status_code == 401
    assert api_allowed.status_code == 200


def test_portal_index_requires_auth_when_not_loopback(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "loopback-ui-token")
    monkeypatch.setattr(
        "utils.control_plane_auth.request_is_loopback",
        lambda _request: False,
    )

    with TestClient(portal_server.app, raise_server_exceptions=False) as client:
        denied = client.get("/")

    assert denied.status_code == 401


def test_pt_auth_module_available_in_sibling_checkout():
    pytest = __import__("pytest")
    from pathlib import Path

    pt_root = Path(__file__).resolve().parents[1].parent / "Perpetua-Tools"
    auth_module = pt_root / "orchestrator" / "control_plane_auth.py"
    if not auth_module.is_file():
        pytest.skip("Perpetua-Tools sibling checkout not present")
    assert "ORAMA_CONTROL_PLANE_TOKEN" in auth_module.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests for _resolve_perpetua_tools_root() — added in this PR
# ---------------------------------------------------------------------------


def test_resolve_pt_root_returns_perpetua_tools_root_env(monkeypatch, tmp_path):
    """PERPETUA_TOOLS_ROOT env var is returned as a Path."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    result = _resolve_perpetua_tools_root()
    assert result == tmp_path


def test_resolve_pt_root_returns_perpetuatoolsroot_env(monkeypatch, tmp_path):
    """PERPETUATOOLSROOT (no underscores) env var is returned as a Path."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setenv("PERPETUATOOLSROOT", str(tmp_path))
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    result = _resolve_perpetua_tools_root()
    assert result == tmp_path


def test_resolve_pt_root_returns_perpetua_tools_path_env(monkeypatch, tmp_path):
    """PERPETUA_TOOLS_PATH env var is returned as a Path."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(tmp_path))

    result = _resolve_perpetua_tools_root()
    assert result == tmp_path


def test_resolve_pt_root_env_var_priority_over_sibling(monkeypatch, tmp_path):
    """Env var takes precedence over sibling path discovery."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    # Create a sibling that looks valid (sentinel file present).
    sibling = tmp_path / "sibling" / "Perpetua-Tools"
    (sibling / "orchestrator").mkdir(parents=True)
    (sibling / "orchestrator" / "fastapi_app.py").write_text("")

    env_path = tmp_path / "env-root"
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(env_path))
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    result = _resolve_perpetua_tools_root()
    # Env var wins even when it does not contain the sentinel file.
    assert result == env_path


def test_resolve_pt_root_whitespace_env_var_is_ignored(monkeypatch, tmp_path):
    """An env var containing only whitespace does not count as set."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", "   ")
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    # No sibling checkout exists, so None is expected.
    result = _resolve_perpetua_tools_root()
    assert result is None


def test_resolve_pt_root_sibling_perplexity_api(monkeypatch, tmp_path):
    """Discovers Perpetua-Tools under <parent>/perplexity-api/Perpetua-Tools."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    # Clear all env vars so sibling discovery runs.
    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    # Build: tmp_path/perplexity-api/Perpetua-Tools/orchestrator/fastapi_app.py
    pt_root = tmp_path / "perplexity-api" / "Perpetua-Tools"
    (pt_root / "orchestrator").mkdir(parents=True)
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("")

    # Patch __file__ parent chain so repo_root.parent == tmp_path.
    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    result = _resolve_perpetua_tools_root()
    assert result == pt_root


def test_resolve_pt_root_sibling_direct(monkeypatch, tmp_path):
    """Discovers Perpetua-Tools directly under <parent>/Perpetua-Tools."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    pt_root = tmp_path / "Perpetua-Tools"
    (pt_root / "orchestrator").mkdir(parents=True)
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("")

    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    result = _resolve_perpetua_tools_root()
    assert result == pt_root


def test_resolve_pt_root_sibling_repos_subdir(monkeypatch, tmp_path):
    """Discovers Perpetua-Tools under <parent>/repos/Perpetua-Tools."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    pt_root = tmp_path / "repos" / "Perpetua-Tools"
    (pt_root / "orchestrator").mkdir(parents=True)
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("")

    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    result = _resolve_perpetua_tools_root()
    assert result == pt_root


def test_resolve_pt_root_returns_none_when_nothing_found(monkeypatch, tmp_path):
    """
    Check Perpetua-Tools root resolution when no env var or sibling checkout is available.
    
    Asserts that _resolve_perpetua_tools_root() yields None when the environment variables
    PERPETUA_TOOLS_ROOT, PERPETUATOOLSROOT, and PERPETUA_TOOLS_PATH are unset and no sibling
    Perpetua-Tools checkout exists relative to the module path.
    """
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    # Point __file__ inside tmp_path so none of the sibling candidates exist.
    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    result = _resolve_perpetua_tools_root()
    assert result is None


def test_resolve_pt_root_requires_sentinel_file(monkeypatch, tmp_path):
    """A sibling directory without orchestrator/fastapi_app.py is not accepted."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root

    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    # Create the directory but NOT the sentinel file.
    pt_root = tmp_path / "Perpetua-Tools" / "orchestrator"
    pt_root.mkdir(parents=True)
    # fastapi_app.py is intentionally absent.

    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    result = _resolve_perpetua_tools_root()
    assert result is None


def test_resolve_pt_root_expands_home_tilde(monkeypatch):
    """Env var with ~ is expanded via Path.expanduser()."""
    from utils.control_plane_auth import _resolve_perpetua_tools_root
    from pathlib import Path

    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", "~/some/path")
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    result = _resolve_perpetua_tools_root()
    assert result == Path("~/some/path").expanduser()
    assert "~" not in str(result)


# ---------------------------------------------------------------------------
# Tests for _read_pt_persisted_token() — refactored in this PR
# ---------------------------------------------------------------------------


def test_read_pt_persisted_token_returns_empty_when_root_none(monkeypatch):
    """Returns '' when _resolve_perpetua_tools_root() returns None."""
    from utils.control_plane_auth import _read_pt_persisted_token

    monkeypatch.setattr(
        "utils.control_plane_auth._resolve_perpetua_tools_root",
        lambda: None,
    )

    assert _read_pt_persisted_token() == ""


def test_read_pt_persisted_token_returns_empty_when_file_missing(monkeypatch, tmp_path):
    """
    Ensure _read_pt_persisted_token returns an empty string when no token file exists under the resolved Perpetua-Tools root.
    
    Patches the resolver to point at `tmp_path` and verifies that absence of `.state/control_plane_token` yields an empty string.
    """
    from utils.control_plane_auth import _read_pt_persisted_token

    monkeypatch.setattr(
        "utils.control_plane_auth._resolve_perpetua_tools_root",
        lambda: tmp_path,
    )
    # .state/control_plane_token is intentionally not created.

    assert _read_pt_persisted_token() == ""


def test_read_pt_persisted_token_strips_whitespace(monkeypatch, tmp_path):
    """Token file content is stripped of surrounding whitespace."""
    from utils.control_plane_auth import _read_pt_persisted_token

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("  whitespace-token\n", encoding="utf-8")

    monkeypatch.setattr(
        "utils.control_plane_auth._resolve_perpetua_tools_root",
        lambda: tmp_path,
    )

    assert _read_pt_persisted_token() == "whitespace-token"


def test_read_pt_persisted_token_via_perpetuatoolsroot(monkeypatch, tmp_path):
    """PERPETUATOOLSROOT (no underscores) is accepted as root for token discovery."""
    from utils.control_plane_auth import _read_pt_persisted_token

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("alt-env-token", encoding="utf-8")

    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setenv("PERPETUATOOLSROOT", str(tmp_path))
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)

    assert _read_pt_persisted_token() == "alt-env-token"


def test_read_pt_persisted_token_via_perpetua_tools_path(monkeypatch, tmp_path):
    """PERPETUA_TOOLS_PATH env var is accepted as root for token discovery."""
    from utils.control_plane_auth import _read_pt_persisted_token

    token_path = tmp_path / ".state" / "control_plane_token"
    token_path.parent.mkdir(parents=True)
    token_path.write_text("path-env-token", encoding="utf-8")

    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(tmp_path))

    assert _read_pt_persisted_token() == "path-env-token"


def test_read_pt_persisted_token_all_env_vars_empty_no_sibling(monkeypatch, tmp_path):
    """Returns '' when all env vars are unset and no sibling checkout is present."""
    from utils.control_plane_auth import _read_pt_persisted_token

    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)

    # Redirect __file__ so sibling discovery finds nothing.
    fake_module_path = tmp_path / "orama-system" / "utils" / "control_plane_auth.py"
    monkeypatch.setattr("utils.control_plane_auth.__file__", str(fake_module_path))

    assert _read_pt_persisted_token() == ""
