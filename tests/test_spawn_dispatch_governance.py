"""Legacy public spawn APIs must share PT's durable runtime authority."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


def _load_spawn() -> object:
    """Load this checkout's script without importing a sibling script."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "spawn_agents.py"
    spec = importlib.util.spec_from_file_location("spawn_governance_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_dispatch_deduplicates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A direct public script call must not bypass the PT guard."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    effects: list[str] = []

    async def effect(task: str) -> dict:
        """Substitute only the external CLI effect."""
        effects.append(task)
        return {"ok": True}

    monkeypatch.setattr(module, "_dispatch_codex", effect)
    first = asyncio.run(module.dispatch("codex", "review code", scope="goal-a"))
    assert first["ok"] is True
    with pytest.raises(RuntimeError, match="already claimed"):
        asyncio.run(module.dispatch("codex", "review code", scope="goal-a"))
    assert effects == ["review code"]
    assert asyncio.run(module.dispatch("codex", "review code", scope="goal-b"))["ok"] is True


def test_public_race_cannot_bypass_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The separate public race entrypoint must use the identical governed path."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    effects: list[str] = []

    async def effect(task: str) -> dict:
        """Represent the existing race implementation without network or GPU."""
        effects.append(task)
        return {"ok": True}

    monkeypatch.setattr(module, "_dispatch_race", effect)
    asyncio.run(module.dispatch_race("review code", scope="goal-a"))
    with pytest.raises(RuntimeError, match="already claimed"):
        asyncio.run(module.dispatch("race", "review code", scope="goal-a"))
    assert effects == ["review code"]


@pytest.mark.parametrize("provider", ["codex", "gemini", "gemini-review", "cursor"])
def test_ignored_cli_model_override_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    """Reject model assertions that the CLI worker would silently ignore."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="model"):
        asyncio.run(module.dispatch(provider, "review code", model="claimed-model"))
