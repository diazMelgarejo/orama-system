"""Bind dispatch authority to the first complete explicitly discovered checkout."""

from collections.abc import Iterator
from contextlib import contextmanager
import importlib
import importlib.metadata
from pathlib import Path
from types import ModuleType
import sys

import pytest

from test_spawn_dispatch_governance import _load_spawn


@contextmanager
def _isolated_governance_cache() -> Iterator[None]:
    """Isolate synthetic policy imports, restoring every inherited module identity."""
    def policy_module(name: str) -> bool:
        """Match only the absolute policy package and its descendants."""
        return name == "perpetua_tools" or name.startswith("perpetua_tools.")

    with pytest.MonkeyPatch.context() as cache:
        for name in tuple(sys.modules):
            if policy_module(name):
                cache.delitem(sys.modules, name)
        try:
            yield
        finally:
            for name in tuple(sys.modules):
                if policy_module(name):
                    del sys.modules[name]


@pytest.fixture
def spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """Isolate synthetic checkouts from workstation paths and inherited policies."""
    for key in ("PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.delenv(key, raising=False)
    module = _load_spawn()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path / "orama-system")
    monkeypatch.setattr(sys, "path", sys.path.copy())
    with _isolated_governance_cache():
        try:
            yield module
        finally:
            # Test-local cache patches must unwind before inherited modules return.
            monkeypatch.undo()


@pytest.mark.parametrize("exceptional", [False, True])
def test_policy_cache_restores_originals_and_discards_synthetic_modules(
    monkeypatch: pytest.MonkeyPatch, exceptional: bool,
) -> None:
    """Normal and exceptional exits preserve preloaded policy objects exactly."""
    package = ModuleType("perpetua_tools")
    policy = ModuleType("perpetua_tools.model_governance")
    monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(sys.modules, policy.__name__, policy)
    original = {name: module for name, module in sys.modules.items()
                if name == "perpetua_tools" or name.startswith("perpetua_tools.")}
    try:
        with _isolated_governance_cache():
            assert not any(name in sys.modules for name in original)
            sys.modules[package.__name__] = ModuleType(package.__name__)
            sys.modules["perpetua_tools.synthetic_child"] = ModuleType("perpetua_tools.synthetic_child")
            if exceptional:
                raise RuntimeError("synthetic test failure")
    except RuntimeError as exc:
        assert exceptional and str(exc) == "synthetic test failure"
    restored = {name: module for name, module in sys.modules.items()
                if name == "perpetua_tools" or name.startswith("perpetua_tools.")}
    assert restored.keys() == original.keys()
    assert all(restored[name] is module for name, module in original.items())


def test_spawn_fixture_preserves_cache_after_complete_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The later monkeypatch finalizer cannot remove restored inherited modules."""
    originals = {name: ModuleType(name) for name in (
        "perpetua_tools", "perpetua_tools.model_governance",
    )}
    for name, module in originals.items():
        monkeypatch.setitem(sys.modules, name, module)
    local = pytest.MonkeyPatch()
    fixture = spawn.__wrapped__(tmp_path, local)
    try:
        next(fixture)
        for name in originals:
            assert name not in sys.modules
            local.setitem(sys.modules, name, ModuleType(name))
        with pytest.raises(StopIteration):
            next(fixture)
        local.undo()
        assert all(sys.modules.get(name) is module for name, module in originals.items())
    finally:
        fixture.close()
        local.undo()


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


def test_missing_candidates_refuse_ambient_authority(
    spawn: ModuleType, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An installed or cached unrelated orchestrator is never a discovery fallback."""
    package = ModuleType("orchestrator")
    package.__path__ = []
    guard = ModuleType("orchestrator.dispatch_guard")
    guard.DispatchGuard = object()
    guard.DispatchRequest = object()
    state = ModuleType("orchestrator.state_dir")
    state.resolve_default_state_dir = object()
    for module in (package, guard, state):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    assert importlib.import_module(guard.__name__) is guard
    assert importlib.import_module(state.__name__) is state

    def no_distribution(_name: str) -> None:
        """Model a machine with no installed PT, whatever this environment has."""
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(spawn.importlib.metadata, "distribution", no_distribution)
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


def test_selected_policy_precedes_foreign_search_path_entry(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The selected policy directory wins even when a foreign one is earlier on sys.path.

    A cold policy import triggered while loading the guard resolves to the selected
    checkout, not to a foreign directory that was added to sys.path first.
    """
    selected = _checkout(tmp_path / "selected")
    foreign = _checkout(tmp_path / "foreign")
    guard = selected / "orchestrator/dispatch_guard.py"
    guard.write_text(guard.read_text() + "import perpetua_tools.model_governance\n")
    monkeypatch.setenv("PERPETUATOOLSROOT", str(selected))
    monkeypatch.setattr(sys, "path", [str(foreign / "src"), str(selected / "src"), *sys.path])
    assert "perpetua_tools.model_governance" not in sys.modules
    spawn._pt_dispatch_authority()
    loaded = Path(sys.modules["perpetua_tools.model_governance"].__file__).resolve()
    assert loaded == (selected / "src/perpetua_tools/model_governance.py").resolve()
    assert sys.path.index(str(selected / "src")) < sys.path.index(str(foreign / "src"))
