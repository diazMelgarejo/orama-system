"""Tests for scripts/git/check_tdd_commit.sh (web/src TDD gate)."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/check_tdd_commit.sh"


def _git(tmp_path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tdd@test.local")
    _git(tmp_path, "config", "user.name", "tdd-test")


def _run_hook(tmp_path: Path, message: str) -> subprocess.CompletedProcess[str]:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), str(msg)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_check_tdd_commit_bash_syntax():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True, cwd=ROOT)


def test_check_tdd_commit_allows_tdd_skip(tmp_path: Path):
    _init_repo(tmp_path)
    src = tmp_path / "web" / "src"
    src.mkdir(parents=True)
    (src / "Widget.tsx").write_text("export function Widget() { return null; }\n")
    _git(tmp_path, "add", ".")
    result = _run_hook(tmp_path, "style: tweak\n\ntdd-skip: pure style\n")
    assert result.returncode == 0, result.stderr


def test_check_tdd_commit_blocks_prod_without_test(tmp_path: Path):
    _init_repo(tmp_path)
    src = tmp_path / "web" / "src"
    src.mkdir(parents=True)
    (src / "Widget.tsx").write_text("export function Widget() { return null; }\n")
    _git(tmp_path, "add", ".")
    result = _run_hook(tmp_path, "feat: widget\n")
    assert result.returncode == 1
    assert "TDD gate" in result.stderr


def test_check_tdd_commit_allows_prod_with_test(tmp_path: Path):
    _init_repo(tmp_path)
    src = tmp_path / "web" / "src"
    src.mkdir(parents=True)
    (src / "Widget.tsx").write_text("export function Widget() { return null; }\n")
    (src / "Widget.test.tsx").write_text("import { describe, it } from 'vitest';\n")
    _git(tmp_path, "add", ".")
    result = _run_hook(tmp_path, "feat: widget + test\n")
    assert result.returncode == 0, result.stderr


def test_check_tdd_commit_ignores_non_web_changes(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("# hi\n")
    _git(tmp_path, "add", ".")
    result = _run_hook(tmp_path, "docs: readme\n")
    assert result.returncode == 0, result.stderr
