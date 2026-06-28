"""Windows platform lane — operator scripts and Win-specific portal modules."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_WINDOWS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _WINDOWS_DIR.parents[1]


def repo_root() -> Path:
    return _REPO_ROOT


def load_module(module_name: str):
    """Load a sibling module from platform/windows/ (e.g. peer_inbox_portal)."""
    import sys

    path = _WINDOWS_DIR / f"{module_name}.py"
    if not path.is_file():
        raise ImportError(f"platform/windows/{module_name}.py not found")
    spec = importlib.util.spec_from_file_location(
        f"orama_platform_windows_{module_name}",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load platform/windows/{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    win_dir = str(_WINDOWS_DIR)
    inserted = win_dir not in sys.path
    if inserted:
        sys.path.insert(0, win_dir)
    try:
        spec.loader.exec_module(mod)
    finally:
        if inserted:
            sys.path.remove(win_dir)
    return mod
