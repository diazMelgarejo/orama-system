"""Installed PT authority must be bound to distribution-owned module files."""

import builtins
from importlib import metadata
import json
from pathlib import Path
from types import ModuleType
from typing import Any
import sys

import pytest

from test_spawn_authority_discovery import _checkout, spawn as spawn
from test_spawn_dispatch_governance import _load_spawn


def test_import_does_not_require_an_editable_toml_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python 3.10 import/status paths need neither optional TOML parser."""
    original_import = builtins.__import__
    seen: list[str] = []

    def legacy_import(name: str, *args: Any, **kwargs: Any) -> Any:
        """Model the older standard library without changing the host interpreter."""
        if name in ("tomllib", "tomli"):
            seen.append(name)
            raise ModuleNotFoundError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", legacy_import)
    module = _load_spawn()
    assert callable(module._pt_dispatch_authority)
    assert seen == []


def _installation(site: Path) -> Path:
    """Create a wheel-shaped installation with real discoverable distribution metadata."""
    _checkout(site)
    (site / "src/perpetua_tools").rename(site / "perpetua_tools")
    info = site / "perpetua_tools-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: perpetua-tools\nVersion: 1.0\n")
    files = [p.relative_to(site).as_posix() for p in site.rglob("*.py")]
    (info / "RECORD").write_text("".join(f"{name},,\n" for name in files))
    return site


def test_installed_distribution_loads_without_checkout(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A metadata-owned installed authority works without any checkout candidates."""
    site = _installation(tmp_path / "site")
    monkeypatch.syspath_prepend(str(site))
    assert metadata.distribution("perpetua-tools").metadata["Name"] == "perpetua-tools"
    first = spawn._pt_dispatch_authority()
    assert first[2]() == str(site)
    assert spawn._pt_dispatch_authority()[0] is first[0]
    assert spawn.duplicate_dispatch_error_type().__module__ == first[0].__module__


def test_installation_cannot_load_unowned_authority_files(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An importable guard absent from the PT distribution record is not PT authority."""
    site = _installation(tmp_path / "site")
    record = site / "perpetua_tools-1.0.dist-info/RECORD"
    record.write_text(record.read_text().replace("orchestrator/dispatch_guard.py,,\n", ""))
    monkeypatch.syspath_prepend(str(site))
    with pytest.raises(ImportError, match="PT dispatch authority is unavailable"):
        spawn._pt_dispatch_authority()


def test_installed_authority_ignores_foreign_cached_orchestrator(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generic package collision cannot replace metadata-selected dispatch modules."""
    site = _installation(tmp_path / "site")
    foreign = ModuleType("orchestrator")
    foreign.__path__ = []
    monkeypatch.setitem(sys.modules, "orchestrator", foreign)
    monkeypatch.syspath_prepend(str(site))
    assert spawn._pt_dispatch_authority()[2]() == str(site)
    assert sys.modules["orchestrator"] is foreign


def test_installed_authority_refuses_foreign_cached_policy(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distribution metadata does not permit mixing an installed guard with foreign policy."""
    site = _installation(tmp_path / "site")
    foreign = ModuleType("perpetua_tools.model_governance")
    foreign.__file__ = str(tmp_path / "other/model_governance.py")
    monkeypatch.setitem(sys.modules, foreign.__name__, foreign)
    monkeypatch.syspath_prepend(str(site))
    with pytest.raises(ImportError, match="governance origin"):
        spawn._pt_dispatch_authority()


def test_selected_checkout_failure_does_not_fall_back_to_installation(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An installed authority cannot hide a selected checkout's operational refusal."""
    root = _checkout(tmp_path / "broken")
    (root / "orchestrator/state_dir.py").write_text('raise RuntimeError("broken authority")\n')
    monkeypatch.setenv("PERPETUATOOLSROOT", str(root))
    monkeypatch.syspath_prepend(str(_installation(tmp_path / "site")))
    with pytest.raises(RuntimeError, match="broken authority"):
        spawn._pt_dispatch_authority()


@pytest.mark.parametrize("project_name", ["perpetua-tools", "unrelated-project"])
@pytest.mark.parametrize("parser_mode", ["native", "compatibility", "missing"])
def test_editable_installation_verifies_recorded_source_project(
    spawn: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    project_name: str, parser_mode: str,
) -> None:
    """Editable metadata binds a complete PT project, not an arbitrary importable tree."""
    source = _checkout(tmp_path / "editable")
    (source / "pyproject.toml").write_text(f'[project]\nname = "{project_name}"\n')
    info = tmp_path / "site/perpetua_tools-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: perpetua-tools\nVersion: 1.0\n")
    (info / "direct_url.json").write_text(json.dumps({"url": source.as_uri(), "dir_info": {"editable": True}}))
    (info / "RECORD").write_text("perpetua_tools-1.0.dist-info/direct_url.json,,\n")
    monkeypatch.syspath_prepend(str(info.parent))
    if parser_mode != "native":
        parser = __import__("tomllib") if sys.version_info >= (3, 11) else __import__("tomli")
        original_import = builtins.__import__

        def parser_import(name: str, *args: Any, **kwargs: Any) -> Any:
            """Exercise compatibility parsing and explicit optional-dependency refusal."""
            if name == "tomllib" or (name == "tomli" and parser_mode == "missing"):
                raise ModuleNotFoundError(name)
            if name == "tomli":
                return parser
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", parser_import)
    if parser_mode == "missing":
        with pytest.raises(ImportError, match="editable parsing requires tomli"):
            spawn._pt_dispatch_authority()
        return
    if project_name == "perpetua-tools":
        assert spawn._pt_dispatch_authority()[2]() == str(source)
    else:
        with pytest.raises(ImportError, match="editable ownership"):
            spawn._pt_dispatch_authority()
