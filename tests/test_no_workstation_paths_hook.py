"""Exercise the write hook against new paths and repository ignore rules."""

import json
import runpy
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


@pytest.mark.unit
def test_hook_normalizes_git_root_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    alias = tmp_path / "repo-alias"
    alias.symlink_to(repo, target_is_directory=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    hook = runpy.run_path(str(HOOK))
    original_run = subprocess.run

    def git_with_aliased_root(*args, **kwargs):
        result = original_run(*args, **kwargs)
        if args[0][-1] == "--show-toplevel" and result.returncode == 0:
            result.stdout = str(alias) + "\n"
        return result

    monkeypatch.setattr(subprocess, "run", git_with_aliased_root)
    assert hook["repository_target"](str(alias / "nested" / "config.txt")) == (
        str(repo.resolve()), "nested/config.txt"
    )
