"""Python bytecode is never tracked, including inside the lib directories .gitignore re-includes.

Several `!…/lib/**` negations re-include whole helper directories. A later rule must keep
`__pycache__` and compiled files ignored inside them; without it a test run's bytecode was
committed once (scripts/lib/__pycache__/spawn_detached.cpython-313.pyc).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# One path inside each directory that .gitignore re-includes with a `**` negation, plus one plain path.
BYTECODE_PATHS = (
    "scripts/lib/__pycache__/helper.cpython-313.pyc",
    "bin/orama-system/scripts/lib/__pycache__/helper.cpython-313.pyc",
    "bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/lib/__pycache__/helper.cpython-313.pyc",
    "bin/agents/__pycache__/biafra_cycle.cpython-313.pyc",
    "scripts/lib/helper.pyo",
)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
@pytest.mark.parametrize("path", BYTECODE_PATHS)
def test_bytecode_is_ignored_even_inside_reincluded_lib_directories(path: str) -> None:
    """Check that git ignores the bytecode path, whatever negations precede the bytecode rules."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=ROOT, capture_output=True, check=False,
    )
    assert result.returncode == 0, f"{path} is not ignored by .gitignore"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_the_reincluded_lib_sources_stay_tracked() -> None:
    """Check that the bytecode rule does not hide the helper sources the negations exist to keep."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "scripts/lib/get-best-python.ps1"],
        cwd=ROOT, capture_output=True, check=False,
    )
    assert result.returncode == 1, "scripts/lib sources must stay tracked"
