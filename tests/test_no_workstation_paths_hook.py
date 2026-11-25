"""Exercise the write hook against new paths and repository ignore rules."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


HOOK = (
    Path(__file__).resolve().parents[1]
    / "bin/orama-system/skills/shell-hygiene/hooks/no-workstation-paths.py"
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("target", "expected"),
    [("nested/new/config.txt", 2), ("nested/ignored/config.txt", 0), ("../scratch/config.txt", 0)],
)
def test_hook_resolves_missing_target_parents(tmp_path: Path, target: str, expected: int) -> None:
    """Use the complete destination for repository membership and ignore matching."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("/nested/ignored/\n", encoding="utf-8")
    payload = {"tool_input": {"file_path": target, "content": "/Users/" + "Example/config"}}
    result = subprocess.run(
        [sys.executable, str(HOOK)], cwd=repo, input=json.dumps(payload),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == expected, result.stderr
    assert ("BLOCKED" in result.stderr) == (expected == 2)
    assert not (repo / "nested").exists()
