"""Portal duplicate dispatch returns 409 under every authority discovery mode, with no skips."""

from importlib import metadata
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from typing import Callable

from fastapi.testclient import TestClient
import pytest

from orama_system.portal_server import app
from test_spawn_authority_discovery import _checkout, spawn as spawn
from test_spawn_installed_authority import _installation


def _select_environment_root(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority through an explicit environment root."""
    monkeypatch.setenv("PERPETUATOOLSROOT", str(_checkout(tmp_path / "explicit")))


def _select_alternate_root(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority through the alternate sibling-checkout root."""
    _checkout(tmp_path / "perplexity-api/Perpetua-Tools")


def _select_installed_authority(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority recorded by an installed distribution, with no checkout candidate.

    The portal prepends a PT root to sys.path while handling a request, which would let a
    developer machine's real editable PT distribution shadow the fixture on the second
    lookup. Pinning the lookup keeps this test about the 409 mapping, not the host install.
    """
    monkeypatch.syspath_prepend(str(_installation(tmp_path / "site")))
    fixture_distribution = metadata.distribution("perpetua-tools")
    monkeypatch.setattr(metadata, "distribution", lambda _name: fixture_distribution)


MODES: list[tuple[str, Callable[[ModuleType, Path, pytest.MonkeyPatch], None]]] = [
    ("environment-root", _select_environment_root),
    ("alternate-root", _select_alternate_root),
    ("installed-authority", _select_installed_authority),
]


@pytest.mark.parametrize("select", [mode for _, mode in MODES], ids=[name for name, _ in MODES])
def test_duplicate_dispatch_is_conflict_in_each_discovery_mode(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    select: Callable[[ModuleType, Path, pytest.MonkeyPatch], None],
) -> None:
    """A DuplicateDispatch from the selected authority maps to HTTP 409, never 500."""
    select(spawn, tmp_path, monkeypatch)
    duplicate_type = spawn.duplicate_dispatch_error_type()
    assert duplicate_type.__name__ == "DuplicateDispatch"

    async def dispatch(agent: str, task: str, model: str | None = None) -> dict:
        """Simulate the selected guard rejecting an already claimed dispatch."""
        raise duplicate_type("equivalent dispatch already claimed")

    monkeypatch.setitem(sys.modules, "spawn_agents", SimpleNamespace(
        dispatch=dispatch, duplicate_dispatch_error_type=spawn.duplicate_dispatch_error_type,
    ))
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/spawn-agent", json={"agent": "codex", "task": "test"})
    assert response.status_code == 409
    assert "already claimed" in response.json()["detail"]
