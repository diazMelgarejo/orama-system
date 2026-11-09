"""Portal duplicate dispatch returns 409 under every authority discovery mode, through the real dispatch path."""

from importlib import metadata
from pathlib import Path
from types import ModuleType
import sys
from typing import Callable

from fastapi.testclient import TestClient
import pytest

from orama_system.portal_server import app
from test_spawn_authority_discovery import _checkout, spawn as spawn
from test_spawn_installed_authority import _installation

DUPLICATE_CAPABLE_GUARD = """\"\"\"Isolated guard that claims each request once and rejects an equivalent repeat.\"\"\"
_CLAIMED = set()


class DuplicateDispatch(RuntimeError):
    \"\"\"Raised when an equivalent dispatch was already claimed.\"\"\"


class DispatchRequest:
    \"\"\"Carry the fields spawn_agents.dispatch builds.\"\"\"
    def __init__(self, **fields):
        self.__dict__.update(fields)


class DispatchGuard:
    \"\"\"Claim, then run the effect once.\"\"\"
    def __init__(self, state_dir):
        self.state_dir = state_dir

    async def execute(self, request, effect):
        key = (request.scope, request.provider, request.model, request.goal, request.prompt)
        if key in _CLAIMED:
            raise DuplicateDispatch("equivalent dispatch already claimed")
        _CLAIMED.add(key)
        return await effect()
"""


def _duplicate_capable(root: Path) -> Path:
    """Give a synthetic authority a guard that really rejects a repeated dispatch."""
    (root / "orchestrator/dispatch_guard.py").write_text(DUPLICATE_CAPABLE_GUARD)
    return root


def _select_environment_root(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority through an explicit environment root."""
    monkeypatch.setenv("PERPETUATOOLSROOT", str(_duplicate_capable(_checkout(tmp_path / "explicit"))))


def _select_alternate_root(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority through the alternate sibling-checkout root."""
    _duplicate_capable(_checkout(tmp_path / "perplexity-api/Perpetua-Tools"))


def _select_installed_authority(spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the authority recorded by an installed distribution, with no checkout candidate.

    The portal prepends a PT root to sys.path while handling a request, which would let a
    developer machine's real editable PT distribution shadow the fixture on the second
    lookup. Pinning the lookup keeps this test about the 409 mapping, not the host install.
    """
    monkeypatch.syspath_prepend(str(_duplicate_capable(_installation(tmp_path / "site"))))
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
    """The first dispatch runs; the real guard rejects the repeat and the portal answers 409, never 500."""
    select(spawn, tmp_path, monkeypatch)
    effects: list[str] = []

    async def effect(task: str) -> dict:
        """Record the one real effect that the guard allows."""
        effects.append(task)
        return {"ok": True, "output": "done", "elapsed": 0.01}

    monkeypatch.setattr(spawn, "_dispatch_codex", effect)
    monkeypatch.setitem(sys.modules, "spawn_agents", spawn)
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    body = {"agent": "codex", "task": "duplicate mode test"}
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post("/api/spawn-agent", json=body)
        second = client.post("/api/spawn-agent", json=body)
    assert first.status_code == 200 and first.json()["ok"] is True
    assert second.status_code == 409
    assert "already claimed" in second.json()["detail"]
    assert effects == ["duplicate mode test"], "the duplicate must be rejected before any effect runs"
