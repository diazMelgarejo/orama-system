"""Portable subprocess evidence checks; fake-package identity is not framework parity."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_alias_prototype_is_self_contained_and_asserted(tmp_path: Path) -> None:
    """Run from another directory and fail on absent fixtures or identity regressions."""
    script = Path(__file__).with_name("alias_finder_prototype.py").resolve()
    result = subprocess.run(
        [sys.executable, "-I", str(script)], cwd=tmp_path,
        capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["target"] == "fakegraph-only"
    assert evidence["checks"] == 9
    assert evidence["status"] == "pass"
