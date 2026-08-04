"""Tests for cloud path normalization and dirty-guard soft skip on VM boot."""
from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NORMALIZE = ROOT / "scripts/cursor/lib-normalize-cloud-paths.sh"
SYNC = ROOT / "scripts/git/sync-attribution-guard-scripts.sh"

pytestmark = pytest.mark.unit


def _run_bash(script: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    # Isolate from cloud VM path pollution.
    for key in (
        "OPENCLAW_HOME",
        "ORAMA_SYSTEM_PATH",
        "PERPETUA_TOOLS_PATH",
        "ALPHACLAW_INSTALL_DIR",
        "REPO_ROOT",
    ):
        full_env.pop(key, None)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=full_env,
        cwd=ROOT,
    )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _commit_file(repo: Path, rel: str, content: str | bytes, msg: str = "init") -> None:
    dest = repo / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        dest.write_bytes(content)
    else:
        dest.write_text(content, encoding="utf-8")
    if rel.endswith(".sh"):
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
    subprocess.run(["git", "add", rel], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_normalize_expands_literal_tilde(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    out = tmp_path / "out.txt"
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        export HOME={home}
        export OPENCLAW_HOME='~/oc-home'
        export PERPETUA_TOOLS_PATH='~/oc-home/pt-tools'
        export ALPHACLAW_INSTALL_DIR='~/oc-home/ac-tools'
        export ORAMA_SYSTEM_PATH='~/oc-home/orama'
        export REPO_ROOT={tmp_path / "orama"}
        # shellcheck source=/dev/null
        source "{NORMALIZE}"
        normalize_cloud_openclaw_paths
        {{
          printf '%s\\n' "$OPENCLAW_HOME"
          printf '%s\\n' "$PERPETUA_TOOLS_PATH"
          printf '%s\\n' "$ALPHACLAW_INSTALL_DIR"
          printf '%s\\n' "$ORAMA_SYSTEM_PATH"
        }} > "{out}"
        """
    )
    result = _run_bash(script)
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == str(home / "oc-home")
    assert lines[1] == str(home / "oc-home" / "pt-tools")
    assert lines[2] == str(home / "oc-home" / "ac-tools")
    assert lines[3] == str(home / "oc-home" / "orama")


def test_normalize_rejects_openclaw_home_inside_repo(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repo = tmp_path / "orama"
    repo.mkdir()
    nested = repo / "~" / "oc-home"
    out = tmp_path / "out.txt"
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        export HOME={home}
        export OPENCLAW_HOME={nested}
        export REPO_ROOT={repo}
        # shellcheck source=/dev/null
        source "{NORMALIZE}"
        normalize_cloud_openclaw_paths
        printf '%s\\n' "$OPENCLAW_HOME" > "{out}"
        """
    )
    result = _run_bash(script)
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8").strip() == str(home / "openclaw-v1")


def test_guard_sync_on_dirty_skip_exits_zero(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    canon = workspace / "orama"
    sibling = workspace / "ac"
    rel = "scripts/git/audit_engine.py"
    body = "# v1\n"

    for repo in (canon, sibling):
        _init_repo(repo)
        for name in (
            "guard-sync-manifest.sh",
            "check-guard-sync-divergence.sh",
            "sync-attribution-guard-scripts.sh",
        ):
            src = ROOT / "scripts/git" / name
            _commit_file(repo, f"scripts/git/{name}", src.read_bytes(), f"add {name}")
        _commit_file(repo, rel, body, "init audit")

    (sibling / rel).write_text("# dirty local\n", encoding="utf-8")

    env = os.environ.copy()
    env["GUARD_SYNC_ON_DIRTY"] = "skip"
    env["GUARD_SYNC_SKIP_DIVERGENCE_CHECK"] = "1"
    env["WORKSPACE_ROOT"] = str(workspace)
    result = subprocess.run(
        ["bash", str(SYNC), str(sibling)],
        cwd=canon,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GUARD_SYNC_ON_DIRTY=skip" in result.stderr
    assert (sibling / rel).read_text(encoding="utf-8") == "# dirty local\n"


def test_apply_skips_nested_checkout(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    outer = workspace / "orama"
    nested = outer / "junk" / "ac"
    _init_repo(outer)
    _init_repo(nested)
    _commit_file(outer, "README.md", "outer\n")
    _commit_file(nested, "README.md", "nested\n")

    for name in (
        "apply-attribution-guard-all-repos.sh",
        "sync-attribution-guard-scripts.sh",
        "disable-cursor-commit-attribution.sh",
        "cursor-hooks-id.sh",
        "guard-sync-manifest.sh",
        "check-guard-sync-divergence.sh",
    ):
        src = ROOT / "scripts/git" / name
        _commit_file(outer, f"scripts/git/{name}", src.read_bytes(), f"add {name}")

    env = os.environ.copy()
    for key in (
        "OPENCLAW_HOME",
        "ORAMA_SYSTEM_PATH",
        "PERPETUA_TOOLS_PATH",
        "ALPHACLAW_INSTALL_DIR",
    ):
        env.pop(key, None)
    env["OPENCLAW_HOME"] = str(outer / "junk")
    env["ORAMA_SYSTEM_PATH"] = str(outer)
    env["ALPHACLAW_INSTALL_DIR"] = str(nested)
    env["PERPETUA_TOOLS_PATH"] = str(outer)
    env["GUARD_SYNC_ON_DIRTY"] = "skip"
    env["GUARD_SYNC_SKIP_DIVERGENCE_CHECK"] = "1"
    env["HOME"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir()

    result = subprocess.run(
        ["bash", str(outer / "scripts/git/apply-attribution-guard-all-repos.sh")],
        cwd=outer,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipping nested git checkout" in result.stderr
