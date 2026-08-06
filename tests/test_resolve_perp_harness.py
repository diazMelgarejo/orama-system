"""Tests for bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESOLVE_SCRIPT = (
    REPO_ROOT / "bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"
)


def _run_resolver(
    *,
    func: str = "resolve_pt_root",
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    for key in (
        "PERPETUA_TOOLS_PATH",
        "PT_HOME",
        "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT",
        "ORAMA_SYSTEM_PATH",
        "HOME",
    ):
        run_env.pop(key, None)
    if env:
        run_env.update(env)
    run_env.setdefault("HOME", "/tmp")
    return subprocess.run(
        ["bash", "-c", f'source "{RESOLVE_SCRIPT}"; {func}'],
        cwd=str(cwd or REPO_ROOT),
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_pt_root(tmp_path: Path, name: str = "Perpetua-Tools") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "orchestrator").mkdir()
    (root / "orchestrator" / "fastapi_app.py").write_text("# fixture\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "hermes_harness.py").write_text("# fixture\n", encoding="utf-8")
    return root


def test_resolve_perp_harness_fails_without_pt_root(tmp_path: Path) -> None:
    """Resolver must fail when no PT checkout exists in an isolated HOME."""
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    orama = tmp_path / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()

    result = _run_resolver(
        func="resolve_perp_harness_script",
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
        },
        cwd=orama,
    )
    assert result.returncode != 0
    assert "not resolved" in result.stderr.lower()


@pytest.mark.parametrize(
    "env_key",
    [
        "PERPETUA_TOOLS_PATH",
        "PT_HOME",
        "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT",
    ],
)
def test_resolve_perp_harness_env_var_precedence(tmp_path: Path, env_key: str) -> None:
    pt = _make_pt_root(tmp_path)
    result = _run_resolver(env={env_key: str(pt)})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(pt.resolve())


def test_resolve_perp_harness_env_precedence_order(tmp_path: Path) -> None:
    primary = _make_pt_root(tmp_path, "primary-pt")
    secondary = _make_pt_root(tmp_path, "secondary-pt")
    result = _run_resolver(
        env={
            "PERPETUA_TOOLS_PATH": str(primary),
            "PT_HOME": str(secondary),
        }
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(primary.resolve())


def test_resolve_perp_harness_paths_file_pt_dir(tmp_path: Path) -> None:
    pt = _make_pt_root(tmp_path)
    orama = tmp_path / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()
    (orama / ".paths").write_text(f'PT_DIR="{pt}"\n', encoding="utf-8")

    result = _run_resolver(
        env={"ORAMA_SYSTEM_PATH": str(orama)},
        cwd=orama,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(pt.resolve())


def test_resolve_perp_harness_mother_repo_crawl(tmp_path: Path) -> None:
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    pt = _make_pt_root(isolated_home)
    orama = isolated_home / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()

    result = _run_resolver(
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
        },
        cwd=orama,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(pt.resolve())


def test_resolve_perp_harness_home_crawl(tmp_path: Path) -> None:
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    pt = _make_pt_root(isolated_home)
    orama = isolated_home / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()

    result = _run_resolver(
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
        },
        cwd=orama,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(pt.resolve())


def test_resolve_perp_harness_rejects_incomplete_marker(tmp_path: Path) -> None:
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    orama = isolated_home / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()
    incomplete = isolated_home / "incomplete-pt"
    incomplete.mkdir()
    (incomplete / ".git").mkdir()
    (incomplete / "orchestrator").mkdir()

    result = _run_resolver(
        func="resolve_perp_harness_script",
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
            "PERPETUA_TOOLS_PATH": str(incomplete),
        },
        cwd=orama,
    )
    assert result.returncode != 0
    assert "not resolved" in result.stderr.lower()


def test_resolve_perp_harness_rejects_symlink_root(tmp_path: Path) -> None:
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    orama = isolated_home / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()
    # Real PT checkout lives outside HOME so crawl cannot bypass the symlink env var.
    real = _make_pt_root(tmp_path, "real-pt")
    link = isolated_home / "pt-link"
    link.symlink_to(real)

    result = _run_resolver(
        func="resolve_perp_harness_script",
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
            "PERPETUA_TOOLS_PATH": str(link),
        },
        cwd=orama,
    )
    assert result.returncode != 0
    assert "not resolved" in result.stderr.lower()


def test_resolve_perp_harness_rejects_symlink_even_when_real_target_is_crawlable(
    tmp_path: Path,
) -> None:
    """The scenario the isolated symlink test above deliberately excludes
    (placing real-pt outside HOME so crawl can't reach it at all, which
    fixed CI flakiness but also stopped exercising this case): an explicit
    PERPETUA_TOOLS_PATH pointing at a symlink must fail closed even when
    the *same real target* is also legitimately reachable via the normal
    crawl fallback (e.g. a user symlinks ~/pt -> ~/repos/Perpetua-Tools
    while ~/repos is itself a real crawl root). Without the fail-closed
    fix in resolve_pt_root, an explicit-but-rejected override used to
    silently fall through to crawl discovery and resolve anyway --
    defeating the point of rejecting the symlink in the first place.
    """
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    orama = isolated_home / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()
    # Real PT checkout lives inside HOME this time -- deliberately
    # crawl-reachable, unlike the test above.
    real = _make_pt_root(isolated_home, "real-pt")
    link = isolated_home / "pt-link"
    link.symlink_to(real)

    result = _run_resolver(
        func="resolve_perp_harness_script",
        env={
            "HOME": str(isolated_home),
            "ORAMA_SYSTEM_PATH": str(orama),
            "PERPETUA_TOOLS_PATH": str(link),
        },
        cwd=orama,
    )
    assert result.returncode != 0
    assert "not resolved" in result.stderr.lower()


def test_resolve_pt_root_cached_within_session(tmp_path: Path) -> None:
    pt = _make_pt_root(tmp_path)
    run_env = os.environ.copy()
    for key in (
        "PERPETUA_TOOLS_PATH",
        "PT_HOME",
        "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT",
        "ORAMA_SYSTEM_PATH",
        "HOME",
    ):
        run_env.pop(key, None)
    run_env["PERPETUA_TOOLS_PATH"] = str(pt)
    run_env["HOME"] = "/tmp"
    # Two resolve_pt_root calls in one shell must share the session-local cache.
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{RESOLVE_SCRIPT}"; '
            'a="$(resolve_pt_root)"; b="$(resolve_pt_root)"; '
            'printf "%s\\n%s\\n" "$a" "$b"',
        ],
        cwd=str(REPO_ROOT),
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0] == lines[1] == str(pt.resolve())


def test_resolve_perp_harness_fails_on_ambiguous_crawl(tmp_path: Path) -> None:
    orama = tmp_path / "orama-system"
    orama.mkdir()
    (orama / ".git").mkdir()
    _make_pt_root(orama.parent, "Perpetua-Tools-a")
    _make_pt_root(orama.parent, "Perpetua-Tools-b")

    result = _run_resolver(
        env={
            "HOME": str(tmp_path / "empty-home"),
            "ORAMA_SYSTEM_PATH": str(orama),
        },
        cwd=orama,
    )
    assert result.returncode != 0
    assert "ambiguous" in result.stderr.lower()
