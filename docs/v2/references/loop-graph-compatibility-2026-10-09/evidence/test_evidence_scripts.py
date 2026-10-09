"""Portable subprocess checks for the throwaway evidence, not real-framework parity."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EvidenceTests(unittest.TestCase):
    """Evidence must work from another directory and fail loudly on regressions."""

    def test_alias_prototype_is_self_contained_and_asserted(self) -> None:
        """Missing fixtures or false identity assertions make this test fail."""
        script = Path(__file__).with_name("alias_finder_prototype.py")
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run(
                [sys.executable, "-I", str(script)], cwd=cwd,
                capture_output=True, text=True, timeout=15, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["target"], "fakegraph-only")
        self.assertEqual(evidence["checks"], 9)
        self.assertEqual(evidence["status"], "pass")


if __name__ == "__main__":
    unittest.main()
