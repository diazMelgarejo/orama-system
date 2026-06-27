#!/usr/bin/env python3
"""Fail when [project.optional-dependencies] uses unpinned >= specifiers (T4-A)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

# package>=X.Y without upper bound or exact pin
_UNPINNED_RE = re.compile(r"^[a-zA-Z0-9_.\-\[\]]+>=(?!.*[<=>~]=)")


def main() -> int:
    if not PYPROJECT.is_file():
        print(f"missing {PYPROJECT}", file=sys.stderr)
        return 1

    text = PYPROJECT.read_text(encoding="utf-8")
    in_optional = False
    violations: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[project.optional-dependencies]"):
            in_optional = True
            continue
        if in_optional and stripped.startswith("[") and stripped.endswith("]"):
            in_optional = False
            continue
        if not in_optional:
            continue
        if stripped.startswith("#") or "=" not in stripped:
            continue
        _, rhs = stripped.split("=", 1)
        rhs = rhs.strip()
        if not rhs.startswith("["):
            continue
        for entry in re.findall(r'"([^"]+)"', rhs):
            entry = entry.strip()
            if ">=" in entry and "==" not in entry and "~=" not in entry and "," not in entry.split(">=")[-1]:
                if _UNPINNED_RE.match(entry) or (">=" in entry and "<" not in entry):
                    violations.append(f"unpinned optional dependency: {entry}")

    if violations:
        print("Unpinned >= specifiers in [project.optional-dependencies]:", file=sys.stderr)
        print("\n".join(f"  - {v}" for v in violations), file=sys.stderr)
        return 1

    print("OK: optional-dependencies use pinned or bounded specifiers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
