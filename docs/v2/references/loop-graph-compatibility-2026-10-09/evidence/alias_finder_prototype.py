"""Self-contained throwaway alias evidence; never intercepts real frameworks.

Run in a disposable process: python -I alias_finder_prototype.py.
Fake-package mechanics only, not LangGraph or installer parity.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.metadata as md
import importlib.util
import json
from pathlib import Path
import pickle
import sys
import tempfile
from types import ModuleType
from typing import Any

from packaging.specifiers import SpecifierSet


class CompatGapError(ImportError):
    """Unsupported fake module; production must name a real matrix row."""


class AliasLoader(importlib.abc.Loader):
    """Reuse the native object without damaging native import metadata."""

    def __init__(self, native: str) -> None:
        self.native = native
        self.attributes: dict[str, Any] = {}

    def create_module(self, spec: Any) -> ModuleType:
        module = importlib.import_module(self.native)
        self.attributes = {name: getattr(module, name) for name in (
            "__name__", "__spec__", "__package__", "__loader__",
        )}
        return module

    def exec_module(self, module: ModuleType) -> None:
        # Import machinery assigns the alias spec even to a reused object.
        for name, value in self.attributes.items():
            setattr(module, name, value)


class Distribution(md.Distribution):
    """Synthetic interpreter metadata only, NOT an installed pip distribution."""

    def read_text(self, filename: str) -> str | None:
        if filename == "METADATA":
            return "Metadata-Version: 2.1\nName: fakegraph\nVersion: 1.0.3+orama.1\n"
        return None

    def locate_file(self, path: str) -> Path:
        return Path(path)


class AliasFinder(importlib.abc.MetaPathFinder):
    """Own fakegraph only; missing native modules must not fall through."""

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        if fullname != "fakegraph" and not fullname.startswith("fakegraph."):
            return None
        native = "orama_native." + fullname
        try:
            spec = importlib.util.find_spec(native)
        except ModuleNotFoundError as error:
            if error.name and (native == error.name or native.startswith(error.name + ".")):
                raise CompatGapError(f"{fullname}: blocked fake matrix row") from error
            raise  # Broken dependencies must not masquerade as missing modules.
        if spec is None:
            raise CompatGapError(f"{fullname}: blocked fake matrix row")
        return importlib.util.spec_from_loader(
            fullname, AliasLoader(native),
            is_package=spec.submodule_search_locations is not None,
        )

    def find_distributions(self, context: Any = None) -> Any:
        if context is None or context.name in (None, "fakegraph"):
            return iter([Distribution()])
        return iter([])


def activate() -> AliasFinder:
    """Refuse late activation rather than replacing loaded modules."""
    if any(name == "fakegraph" or name.startswith("fakegraph.") for name in sys.modules):
        raise RuntimeError("late activation: fakegraph already imported")
    finder = AliasFinder()
    sys.meta_path.insert(0, finder)
    return finder


def main() -> None:
    """Create temporary fixtures, assert claims, and remove interpreter state."""
    original_path = sys.path[:]
    finder: AliasFinder | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="fake-alias-") as temporary:
            package = Path(temporary) / "orama_native" / "fakegraph"
            package.mkdir(parents=True)
            (package.parent / "__init__.py").write_text("", encoding="utf-8")
            (package / "__init__.py").write_text("VERSION = 'native-fixture'\n", encoding="utf-8")
            (package / "graph.py").write_text("class StateGraph:\n    pass\n", encoding="utf-8")
            sys.path.insert(0, temporary)
            finder = activate()
            alias = importlib.import_module("fakegraph.graph")
            native = importlib.import_module("orama_native.fakegraph.graph")
            assert alias is native
            assert alias.StateGraph is native.StateGraph
            assert importlib.import_module("fakegraph").VERSION == "native-fixture"
            assert native.__spec__.name == "orama_native.fakegraph.graph"
            assert pickle.loads(pickle.dumps(alias.StateGraph())).__class__ is native.StateGraph
            try:
                importlib.import_module("fakegraph.missing.child")
            except CompatGapError:
                pass
            else:
                raise AssertionError("missing module fell through")
            version = md.version("fakegraph")
            assert version == "1.0.3+orama.1"
            assert all(version in SpecifierSet(value) for value in ("==1.0.3", ">=1.0", "<1.0.4"))
            try:
                activate()
            except RuntimeError:
                pass
            else:
                raise AssertionError("late activation accepted")
    finally:
        if finder is not None:
            sys.meta_path.remove(finder)
        sys.path[:] = original_path
        for name in list(sys.modules):
            if name == "fakegraph" or name.startswith(("fakegraph.", "orama_native")):
                del sys.modules[name]
    print(json.dumps({"target": "fakegraph-only", "checks": 9, "status": "pass"}))


if __name__ == "__main__":
    main()
