#!/usr/bin/env python3
"""Fail when [project.optional-dependencies] uses unpinned >= specifiers (T4-A)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"


def _is_unpinned(entry: str) -> bool:
    """True when a requirement uses lone >= without ==, ~=, or upper bound."""
    if "==" in entry or "~=" in entry:
        return False
    if ">=" not in entry:
        return False
    # environment markers after semicolon are not version bounds
    spec = entry.split(";", 1)[0].strip()
    if "<" in spec or "," in spec.split(">=", 1)[-1]:
        return False
    return True


def main() -> int:
    if not PYPROJECT.is_file():
        print(f"missing {PYPROJECT}", file=sys.stderr)
        return 1

    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    optional = data.get("project", {}).get("optional-dependencies", {})
    violations: list[str] = []

    for group, deps in optional.items():
        for entry in deps:
            entry = entry.strip()
            if not entry or entry.startswith("#"):
                continue
            if _is_unpinned(entry):
                violations.append(f"[{group}] unpinned optional dependency: {entry}")

    if violations:
        print("Unpinned >= specifiers in [project.optional-dependencies]:", file=sys.stderr)
        print("\n".join(f"  - {v}" for v in violations), file=sys.stderr)
        return 1

    print("OK: optional-dependencies use pinned or bounded specifiers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
