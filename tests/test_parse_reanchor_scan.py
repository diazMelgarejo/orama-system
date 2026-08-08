"""Tests for parse-reanchor-scan.py."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "scripts" / "git" / "parse-reanchor-scan.py"

SAMPLE = """
  origin/stale-branch  MERGED/in-main (tip twin abcdef123; work already in main)
  origin/feature-x  NEEDS-REANCHOR: graft 2 unique commit(s) onto twin deadbeef0
        (verify which are truly missing:  git cherry -v origin/main ff00ff00ff00ff00ff00ff00ff00ff00ff00ff0 deadbeef0123456789deadbeef0123456789deadbeef )
  origin/orphan  NO-TWIN (no tree match in origin/main) -> investigate
        (verify with: git cherry -v origin/main tipsha)
"""


def test_parse_reanchor_scan_categories(tmp_path: Path):
    sample_path = tmp_path / "scan.txt"
    sample_path.write_text(SAMPLE, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(PARSER), str(sample_path)],
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    )
    data = json.loads(proc.stdout)
    assert data["merged"] == ["stale-branch"]
    assert len(data["needs"]) == 1
    assert data["needs"][0]["branch"] == "feature-x"
    assert data["no_twin"] == ["orphan"]
