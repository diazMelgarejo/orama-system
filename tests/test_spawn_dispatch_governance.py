"""Legacy public spawn APIs must share PT's durable runtime authority."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import subprocess
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


def test_empty_ollama_model_is_refused_before_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty configured model cannot identify a fallback provider effect."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(module, "MANAGER_MODEL", "")
    effects: list[str] = []

    async def effect(task: str) -> dict:
        """Record any attempted Ollama provider effect."""
        effects.append(task)
        return {"ok": True}

    monkeypatch.setattr(module, "_dispatch_ollama_mac", effect)
    with pytest.raises(ValueError, match="model"):
        asyncio.run(module.dispatch("ollama-mac", "review"))
    assert effects == []


def test_cursor_fixed_model_must_pass_governance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A fixed Cursor model cannot be authorized as an unspecified default."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    effects: list[str] = []

    async def effect(task: str) -> dict:
        """Record any attempted Cursor subprocess effect."""
        effects.append(task)
        return {"ok": True}

    monkeypatch.setattr(module, "_dispatch_cursor", effect)
    with pytest.raises(RuntimeError):
        asyncio.run(module.dispatch("cursor", "review"))
    assert effects == []


@pytest.mark.parametrize("provider", ["codex", "gemini", "gemini-review", "cursor", "ollama-mac"])
def test_ignored_cli_model_override_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    """Reject model assertions that the CLI worker would silently ignore."""
    module = _load_spawn()
    monkeypatch.setenv("PT_STATE_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="model"):
        asyncio.run(module.dispatch(provider, "review code", model="claimed-model"))


def test_cli_passes_explicit_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """An operator can supply a new scope for reconciled CLI work."""
    module = _load_spawn()
    seen: list[str | None] = []

    async def dispatch(agent: str, task: str, model: str | None = None, *, scope: str | None = None) -> dict:
        """Capture the scope passed across the CLI boundary."""
        seen.append(scope)
        return {"ok": True}

    monkeypatch.setattr(module, "dispatch", dispatch)
    monkeypatch.setattr(sys, "argv", ["spawn_agents.py", "--task", "review", "--scope", "reconciled"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert seen == ["reconciled"]


@pytest.mark.parametrize(
    "refusal_exc",
    [
        ValueError("model override is not supported by this worker"),
        PermissionError("banned launch id"),
    ],
)
def test_cli_refusal_exits_with_code_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], refusal_exc: Exception
) -> None:
    """CLI refusal handling exits with code 2 and prints refusal message."""
    module = _load_spawn()

    async def dispatch(agent: str, task: str, model: str | None = None, *, scope: str | None = None) -> dict:
        raise refusal_exc

    monkeypatch.setattr(module, "dispatch", dispatch)
    monkeypatch.setattr(sys, "argv", ["spawn_agents.py", "--task", "review"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "dispatch refused:" in captured.err
    assert str(refusal_exc) in captured.err


def test_cli_duplicate_dispatch_uses_real_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the actual dispatch guard exception is handled as a duplicate."""
    module = _load_spawn()
    duplicate_type = module.duplicate_dispatch_error_type()

    async def dispatch(agent: str, task: str, model: str | None = None, *, scope: str | None = None) -> dict:
        """Simulate a duplicate from the real guard type."""
        raise duplicate_type("duplicate")

    monkeypatch.setattr(module, "dispatch", dispatch)
    monkeypatch.setattr(sys, "argv", ["spawn_agents.py", "--task", "review"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2


def test_cli_unrelated_runtime_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unrelated runtime failures are not presented as dispatch refusals."""
    module = _load_spawn()

    async def dispatch(agent: str, task: str, model: str | None = None, *, scope: str | None = None) -> dict:
        """Simulate an unrelated runtime failure."""
        raise RuntimeError("unrelated")

    monkeypatch.setattr(module, "dispatch", dispatch)
    monkeypatch.setattr(sys, "argv", ["spawn_agents.py", "--task", "review"])
    with pytest.raises(RuntimeError, match="unrelated"):
        module.main()


def test_cli_governance_refusal_exits_with_code_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Governance refusal from dispatch exits with code 2 and prints refusal message."""
    module = _load_spawn()
    gov_err_type = getattr(module, "ModelGovernanceError", RuntimeError)

    async def dispatch(agent: str, task: str, model: str | None = None, *, scope: str | None = None) -> dict:
        raise gov_err_type("banned launch id: test-banned")

    monkeypatch.setattr(module, "dispatch", dispatch)
    monkeypatch.setattr(sys, "argv", ["spawn_agents.py", "--task", "review"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "dispatch refused: banned launch id: test-banned" in captured.err


def test_foreign_cached_orchestrator_cannot_replace_pt_guard(tmp_path: Path) -> None:
    """A cached package with the same name cannot intercept PT authorization."""
    pt_root = os.environ.get("PERPETUATOOLSROOT")
    if not pt_root:
        pytest.skip("PERPETUATOOLSROOT is required for the PT integration test")
    code = '''
import asyncio, importlib.util, os, sys, types
foreign = types.ModuleType("orchestrator")
foreign.__path__ = []
sys.modules["orchestrator"] = foreign
spec = importlib.util.spec_from_file_location("spawn_collision_test", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
async def effect(task): return {"ok": True}
module._dispatch_codex = effect
asyncio.run(module.dispatch("codex", "review", scope="same"))
try:
    asyncio.run(module.dispatch("codex", "review", scope="same"))
except RuntimeError:
    pass
else:
    raise AssertionError("duplicate effect admitted")
assert sys.modules["orchestrator"] is foreign
'''
    env = {**os.environ, "PT_STATE_DIR": str(tmp_path), "PERPETUATOOLSROOT": pt_root}
    script = Path(__file__).resolve().parents[1] / "scripts" / "spawn_agents.py"
    result = subprocess.run([sys.executable, "-c", code, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
