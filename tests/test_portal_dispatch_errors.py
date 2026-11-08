"""Client-facing error handling for the portal's agent dispatch endpoint."""

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from orama_system.portal_server import app


@pytest.mark.parametrize(
    ("error", "status", "message"),
    [
        (ValueError("CLI model override is not supported by this worker"), 400, "model override"),
        (PermissionError("dispatch denied"), 403, "dispatch denied"),
    ],
)
def test_dispatch_rejections_are_client_errors(monkeypatch: pytest.MonkeyPatch, error: Exception, status: int, message: str) -> None:
    """Expected validation and authorization failures produce useful 4xx responses."""
    async def dispatch(agent: str, task: str, model: str | None = None) -> dict:
        """Simulate a provider rejecting the request before launching an agent."""
        raise error

    monkeypatch.setitem(sys.modules, "spawn_agents", SimpleNamespace(dispatch=dispatch))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/spawn-agent", json={"agent": "codex", "task": "test", "model": "custom"})
    assert response.status_code == status
    assert message in response.json()["detail"]


def test_unexpected_dispatch_failure_remains_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected provider failures must not be represented as client errors."""
    async def dispatch(agent: str, task: str, model: str | None = None) -> dict:
        """Simulate an unexpected provider failure."""
        raise RuntimeError("unexpected failure")

    monkeypatch.setitem(sys.modules, "spawn_agents", SimpleNamespace(dispatch=dispatch))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/spawn-agent", json={"agent": "codex", "task": "test"})
    assert response.status_code == 500


def test_duplicate_dispatch_returns_conflict_with_foreign_cached_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """A duplicate from the isolated PT authority still returns a conflict."""
    foreign_spawn = ModuleType("scripts.spawn_agents")
    foreign_spawn.__file__ = "/foreign/scripts/spawn_agents.py"
    monkeypatch.setitem(sys.modules, "scripts.spawn_agents", foreign_spawn)
    path = Path(__file__).resolve().parents[1] / "scripts" / "spawn_agents.py"
    spec = importlib.util.spec_from_file_location("portal_dispatch_test_spawn", path)
    assert spec is not None and spec.loader is not None
    spawn_agents = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, spawn_agents)
    spec.loader.exec_module(spawn_agents)
    assert Path(spawn_agents.__file__).resolve() == path
    assert sys.modules["scripts.spawn_agents"] is foreign_spawn
    foreign = ModuleType("orchestrator")
    foreign.__file__ = "/foreign/orchestrator/__init__.py"
    monkeypatch.setitem(sys.modules, "orchestrator", foreign)
    pt_root = os.environ.get("PERPETUATOOLSROOT", "")
    if not pt_root or not (Path(pt_root) / "orchestrator" / "dispatch_guard.py").is_file():
        pytest.skip("PT dispatch authority is not configured")
    duplicate_type = spawn_agents.duplicate_dispatch_error_type()

    async def dispatch(agent: str, task: str, model: str | None = None) -> dict:
        """Simulate the guard rejecting an already claimed dispatch."""
        raise duplicate_type("equivalent dispatch already claimed")

    monkeypatch.setitem(sys.modules, "spawn_agents", SimpleNamespace(
        dispatch=dispatch, duplicate_dispatch_error_type=spawn_agents.duplicate_dispatch_error_type,
    ))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/spawn-agent", json={"agent": "codex", "task": "test"})
    assert response.status_code == 409
    assert "already claimed" in response.json()["detail"]
