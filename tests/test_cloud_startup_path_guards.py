"""Tests for cloud path normalization and dirty-guard soft skip on VM boot."""
from __future__ import annotations

import os
import shlex
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
    """Run bash."""
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
    """Init repo."""
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
    """Commit file."""
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
    """Check: normalize expands literal tilde."""
    home = tmp_path / "home"
    home.mkdir()
    out = tmp_path / "out.txt"
    home_q = shlex.quote(home.as_posix())
    repo_root_q = shlex.quote((tmp_path / "orama").as_posix())
    normalize_q = shlex.quote(NORMALIZE.as_posix())
    out_q = shlex.quote(out.as_posix())
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        export HOME={home_q}
        export OPENCLAW_HOME='~/oc-home'
        export PERPETUA_TOOLS_PATH='~/oc-home/pt-tools'
        export ALPHACLAW_INSTALL_DIR='~/oc-home/ac-tools'
        export ORAMA_SYSTEM_PATH='~/oc-home/orama'
        export REPO_ROOT={repo_root_q}
        # shellcheck source=/dev/null
        source {normalize_q}
        normalize_cloud_openclaw_paths
        {{
          printf '%s\\n' "$OPENCLAW_HOME"
          printf '%s\\n' "$PERPETUA_TOOLS_PATH"
          printf '%s\\n' "$ALPHACLAW_INSTALL_DIR"
          printf '%s\\n' "$ORAMA_SYSTEM_PATH"
        }} > {out_q}
        """
    )
    result = _run_bash(script)
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == (home / "oc-home").as_posix()
    assert lines[1] == (home / "oc-home" / "pt-tools").as_posix()
    assert lines[2] == (home / "oc-home" / "ac-tools").as_posix()
    assert lines[3] == (home / "oc-home" / "orama").as_posix()


def test_normalize_rejects_openclaw_home_inside_repo(tmp_path: Path) -> None:
    """Check: normalize rejects openclaw home inside repo."""
    home = tmp_path / "home"
    home.mkdir()
    repo = tmp_path / "orama"
    repo.mkdir()
    nested = repo / "~" / "oc-home"
    out = tmp_path / "out.txt"
    home_q = shlex.quote(home.as_posix())
    nested_q = shlex.quote(nested.as_posix())
    repo_q = shlex.quote(repo.as_posix())
    normalize_q = shlex.quote(NORMALIZE.as_posix())
    out_q = shlex.quote(out.as_posix())
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        export HOME={home_q}
        export OPENCLAW_HOME={nested_q}
        export REPO_ROOT={repo_q}
        # shellcheck source=/dev/null
        source {normalize_q}
        normalize_cloud_openclaw_paths
        printf '%s\\n' "$OPENCLAW_HOME" > {out_q}
        """
    )
    result = _run_bash(script)
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8").strip() == (home / "openclaw-v1").as_posix()


def test_normalize_rederives_junk_sibling_paths(tmp_path: Path) -> None:
    """Check: normalize rederives junk sibling paths."""
    home = tmp_path / "home"
    home.mkdir()
    repo = tmp_path / "orama-system"
    repo.mkdir()
    junk_orama = repo / "~" / "openclaw-v1" / "orama-system"
    junk_pt = repo / "~" / "openclaw-v1" / "Perpetua-Tools"
    out = tmp_path / "out.txt"
    home_q = shlex.quote(home.as_posix())
    junk_orama_q = shlex.quote(junk_orama.as_posix())
    junk_pt_q = shlex.quote(junk_pt.as_posix())
    nested_oc_q = shlex.quote((repo / "~" / "openclaw-v1").as_posix())
    repo_q = shlex.quote(repo.as_posix())
    normalize_q = shlex.quote(NORMALIZE.as_posix())
    out_q = shlex.quote(out.as_posix())
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        export HOME={home_q}
        export OPENCLAW_HOME={nested_oc_q}
        export ORAMA_SYSTEM_PATH={junk_orama_q}
        export PERPETUA_TOOLS_PATH={junk_pt_q}
        export ALPHACLAW_INSTALL_DIR='~/openclaw-v1/AlphaClaw'
        export REPO_ROOT={repo_q}
        # shellcheck source=/dev/null
        source {normalize_q}
        normalize_cloud_openclaw_paths
        {{
          printf '%s\\n' "$OPENCLAW_HOME"
          printf '%s\\n' "$ORAMA_SYSTEM_PATH"
          printf '%s\\n' "$PERPETUA_TOOLS_PATH"
          printf '%s\\n' "$ALPHACLAW_INSTALL_DIR"
        }} > {out_q}
        """
    )
    result = _run_bash(script)
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == (home / "openclaw-v1").as_posix()
    assert lines[1] == repo.as_posix()
    assert lines[2] == (home / "openclaw-v1" / "Perpetua-Tools").as_posix()
    assert lines[3] == (home / "openclaw-v1" / "AlphaClaw").as_posix()


def _seed_guard_sync_scripts(canon: Path, *extra: str) -> Path:
    """Seed guard sync scripts."""
    names = (
        "guard-sync-manifest.sh",
        "check-guard-sync-divergence.sh",
        "sync-attribution-guard-scripts.sh",
        *extra,
    )
    for name in names:
        src = ROOT / "scripts/git" / name
        _commit_file(canon, f"scripts/git/{name}", src.read_bytes(), f"add {name}")
    return canon / "scripts/git/sync-attribution-guard-scripts.sh"


def test_guard_sync_on_dirty_skip_exits_dirty_status(tmp_path: Path) -> None:
    """Check: guard sync on dirty skip exits dirty status."""
    workspace = tmp_path / "ws"
    canon = workspace / "orama"
    sibling = workspace / "ac"
    rel = "scripts/git/audit_engine.py"
    body = "# v1\n"

    for repo in (canon, sibling):
        _init_repo(repo)
        if repo == canon:
            sync_script = _seed_guard_sync_scripts(canon)
        else:
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
        ["bash", str(sync_script), str(sibling)],
        cwd=canon,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "GUARD_SYNC_ON_DIRTY=skip" in result.stderr
    assert (sibling / rel).read_text(encoding="utf-8") == "# dirty local\n"


def test_sync_real_failure_is_not_treated_as_dirty_skip(tmp_path: Path) -> None:
    """Check: sync real failure is not treated as dirty skip."""
    workspace = tmp_path / "ws"
    canon = workspace / "orama"
    sibling = workspace / "ac"
    _init_repo(canon)
    _init_repo(sibling)
    sync_script = _seed_guard_sync_scripts(canon, "cursor-hooks-id.sh")
    _commit_file(sibling, "README.md", "sibling\n")

    blocked = sibling / "scripts/git/cursor-hooks-id.sh"
    blocked.parent.mkdir(parents=True, exist_ok=True)
    blocked.mkdir()

    env = os.environ.copy()
    env["GUARD_SYNC_ON_DIRTY"] = "skip"
    env["GUARD_SYNC_SKIP_DIVERGENCE_CHECK"] = "1"
    env["WORKSPACE_ROOT"] = str(workspace)
    result = subprocess.run(
        ["bash", str(sync_script), str(sibling)],
        cwd=canon,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "not a safe regular-file destination" in result.stderr


def test_apply_skips_nested_checkout(tmp_path: Path) -> None:
    """Check: apply skips nested checkout."""
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
