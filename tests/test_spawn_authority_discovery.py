"""Bind dispatch authority to the first complete explicitly discovered checkout."""

from pathlib import Path
from types import ModuleType
import sys

import pytest

from test_spawn_dispatch_governance import _load_spawn


@pytest.fixture
def spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Remove workstation discovery settings and all real sibling candidates."""
    for key in ("PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)
    module = _load_spawn()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path / "orama-system")
    monkeypatch.setattr(sys, "path", sys.path.copy())
    return module


def _checkout(root: Path) -> Path:
    """Create a complete minimal authority with a recognizable state resolver."""
    package = root / "orchestrator"
    package.mkdir(parents=True)
    policy = root / "src/perpetua_tools"
    policy.mkdir(parents=True)
    (policy / "__init__.py").write_text('"""Test policy package."""\n')
    (policy / "model_governance.py").write_text('"""Test policy module."""\n')
    (package / "__init__.py").write_text('"""Isolated test authority."""\n')
    (package / "dispatch_guard.py").write_text(
        '"""Isolated guard."""\n'
        'class DispatchGuard:\n    """Test guard."""\n'
        'class DispatchRequest:\n    """Test request."""\n'
        'class DuplicateDispatch(RuntimeError):\n    """Test duplicate."""\n'
    )
    (package / "state_dir.py").write_text(
        '"""Isolated state resolver."""\n'
        'def resolve_default_state_dir():\n    """Identify selected root."""\n'
        f'    return {str(root)!r}\n'
    )
    return root


@pytest.mark.parametrize("key", ["PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"])
def test_each_environment_alias_selects_authority(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str,
) -> None:
    """Every supported explicit spelling works without the primary alias set."""
    root = _checkout(tmp_path / "explicit")
    monkeypatch.setenv(key, str(root))
    assert spawn._pt_dispatch_authority()[2]() == str(root)


@pytest.mark.parametrize("relative", ["perplexity-api/Perpetua-Tools", "Perpetua-Tools", "repos/Perpetua-Tools"])
def test_each_sibling_layout_selects_authority(spawn: ModuleType, tmp_path: Path, relative: str) -> None:
    """Each supported sibling fallback works independently of local configuration."""
    root = _checkout(tmp_path / relative)
    assert spawn._pt_dispatch_authority()[2]() == str(root)


def test_incomplete_candidates_do_not_mask_complete_later_checkout(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing directories and guard-only checkouts cannot mask a usable path."""
    incomplete = _checkout(tmp_path / "incomplete")
    (incomplete / "orchestrator/state_dir.py").unlink()
    empty = tmp_path / "empty"
    empty.mkdir()
    valid = _checkout(tmp_path / "valid")
    monkeypatch.setenv("PERPETUATOOLSROOT", str(incomplete))
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(empty))
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(valid))
    assert spawn._pt_dispatch_authority()[2]() == str(valid)


def test_empty_root_alias_does_not_mask_path_alias(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A directory alone is not authority even when it is the first legacy alias."""
    empty = tmp_path / "empty"
    empty.mkdir()
    valid = _checkout(tmp_path / "valid")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(empty))
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(valid))
    assert spawn._pt_dispatch_authority()[2]() == str(valid)


def test_candidate_precedence_and_class_identity(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit aliases precede siblings and repeated loads preserve exception types."""
    roots = [_checkout(tmp_path / name) for name in ("primary", "root", "path")]
    _checkout(tmp_path / "Perpetua-Tools")
    for key, root in zip(("PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"), roots):
        monkeypatch.setenv(key, str(root))
    first = spawn._pt_dispatch_authority()
    assert first[2]() == str(roots[0])
    assert spawn._pt_dispatch_authority()[0] is first[0]
    assert spawn.duplicate_dispatch_error_type().__module__ == first[0].__module__
    monkeypatch.delenv("PERPETUATOOLSROOT")
    assert spawn._pt_dispatch_authority()[2]() == str(roots[1])


def test_incomplete_sibling_is_skipped(spawn: ModuleType, tmp_path: Path) -> None:
    """A guard-only sibling cannot prevent discovery of the next complete sibling."""
    incomplete = _checkout(tmp_path / "perplexity-api/Perpetua-Tools")
    (incomplete / "orchestrator/state_dir.py").unlink()
    valid = _checkout(tmp_path / "Perpetua-Tools")
    assert spawn._pt_dispatch_authority()[2]() == str(valid)


def test_missing_candidates_refuse_ambient_authority(spawn: ModuleType) -> None:
    """An installed or cached unrelated orchestrator is never a discovery fallback."""
    with pytest.raises(ImportError, match="PT dispatch authority is unavailable"):
        spawn._pt_dispatch_authority()


def test_complete_but_broken_authority_is_not_silently_replaced(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A selected checkout's operational failures remain visible and fail closed."""
    root = _checkout(tmp_path / "broken")
    (root / "orchestrator/state_dir.py").write_text('raise RuntimeError("broken authority")\n')
    monkeypatch.setenv("PERPETUATOOLSROOT", str(root))
    _checkout(tmp_path / "Perpetua-Tools")
    with pytest.raises(RuntimeError, match="broken authority"):
        spawn._pt_dispatch_authority()


@pytest.mark.parametrize("name,relative", [
    ("perpetua_tools", "src/perpetua_tools/__init__.py"),
    ("perpetua_tools.model_governance", "src/perpetua_tools/model_governance.py"),
])
def test_cached_governance_from_other_checkout_is_refused(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    name: str, relative: str,
) -> None:
    """Selected guard/state cannot authorize with another checkout's cached policy."""
    root = _checkout(tmp_path / "selected")
    foreign = ModuleType(name)
    foreign.__file__ = str(tmp_path / "other" / relative)
    monkeypatch.setitem(sys.modules, name, foreign)
    monkeypatch.setenv("PERPETUATOOLSROOT", str(root))
    with pytest.raises(ImportError, match="governance origin"):
        spawn._pt_dispatch_authority()
    assert sys.modules[name] is foreign
