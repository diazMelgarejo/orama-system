import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "scripts/git").mkdir(parents=True)
    shutil.copy(ROOT / "scripts/git/markdown_lint.py", tmp_path / "scripts/git")
    shutil.copy(ROOT / ".markdownlint-cli2.jsonc", tmp_path)
    (tmp_path / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def commit(repo):
    git(repo, "add", "-f", ".")
    git(repo, "commit", "-qm", "fixture")
    return git(repo, "rev-parse", "HEAD")


def run(repo, *args):
    return subprocess.run(["python3", "scripts/git/markdown_lint.py", *args], cwd=repo,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def test_debt_scan_rejects_zero_files(repo):
    result = run(repo, "debt")
    assert result.returncode != 0
    assert "selected zero" in result.stdout


def test_real_scan_counts_first_party_and_excludes_vendor_and_environments(repo):
    for name in ("good.md", "vendor/bad.md", ".venv/bad.md", "venv/bad.md",
                 ".tox/bad.md", ".nox/bad.md", "nested/vendor/bad.md"):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Good\n" if name == "good.md" else "# Bad\n\n" + "word " * 30 + "\n")
    commit(repo)
    result = run(repo, "debt")
    assert result.returncode == 0, result.stdout
    assert "Linting: 1 file(s)" in result.stdout


def test_changed_scan_fails_on_new_violation_and_skips_no_changes(repo):
    (repo / "good.md").write_text("# Good\n")
    base = commit(repo)
    assert "lint skipped" in run(repo, "changed", "--base", base).stdout
    (repo / "good.md").write_text("# Good\n\n" + "word " * 30 + "\n")
    commit(repo)
    result = run(repo, "changed", "--base", base)
    assert result.returncode != 0
    assert "Linting: 1 file(s)" in result.stdout
    assert "MD013" in result.stdout


def test_zero_linter_count_fails_closed(repo):
    (repo / "good.md").write_text("# Good\n")
    commit(repo)
    (repo / "node_modules").unlink()
    binary = repo / "node_modules/.bin/markdownlint-cli2"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\necho 'Linting: 0 file(s)'\n")
    os.chmod(binary, 0o755)
    package = repo / "node_modules/markdownlint-cli2/package.json"
    package.parent.mkdir()
    package.write_text('{"version": "0.17.2"}')
    result = run(repo, "debt")
    assert result.returncode != 0
    assert "expected 1 files" in result.stdout
