"""Tests for hermes-harness spawn lifecycle script."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SPAWN_SH = ROOT / "bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh"
RESOLVE_SH = ROOT / "bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"
FAKE_PERP = ROOT / "tests/fixtures/hermes_harness_stub.py"


def _run_spawn(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env or {})
    return subprocess.run(
        ["bash", str(SPAWN_SH), *args],
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture
def isolated_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    harness_home = tmp_path / "hermes-home"
    harness_home.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(harness_home))
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path / "pt"))
    pt_root = tmp_path / "pt"
    pt_src = pt_root / "src"
    pt_src.mkdir(parents=True)
    (pt_root / ".git").mkdir()
    (pt_root / "orchestrator").mkdir()
    (pt_root / "orchestrator" / "fastapi_app.py").write_text(
        "# PT root marker for resolve_perp_harness.sh\n",
        encoding="utf-8",
    )
    (pt_src / "hermes_harness.py").write_text(
        textwrap.dedent(
            """\
            import sys
            import time
            if __name__ == "__main__":
                time.sleep(30)
                sys.exit(0)
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_resolve_perp_harness_fails_without_pt_root() -> None:
    proc = subprocess.run(
        ["bash", "-c", f'source "{RESOLVE_SH}"; resolve_perp_harness_script'],
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if not k.startswith("PERPETUA")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "not resolved" in proc.stderr.lower() or "not found" in proc.stderr.lower()


def test_invalid_session_id_rejected(isolated_runtime: Path) -> None:
    proc = _run_spawn(
        "status",
        env={
            "HERMES_SPAWN_SESSION": "../evil",
            "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
            "HOME": str(isolated_runtime),
            "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
            "HERMES_HOME": str(isolated_runtime / "hermes-home"),
        },
    )
    assert proc.returncode != 0
    assert "HERMES_SPAWN_SESSION" in proc.stderr


def test_status_exits_when_no_pid_file(isolated_runtime: Path) -> None:
    proc = _run_spawn(
        "status",
        env={
            "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
            "HOME": str(isolated_runtime),
            "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
            "HERMES_HOME": str(isolated_runtime / "hermes-home"),
        },
    )
    assert proc.returncode == 1
    assert "No active Hermes session" in proc.stdout


def test_pid_dir_uses_numeric_uid(isolated_runtime: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "../../traversal")
    proc = _run_spawn(
        "status",
        env={
            "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
            "HOME": str(isolated_runtime),
            "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
            "HERMES_HOME": str(isolated_runtime / "hermes-home"),
        },
    )
    uid = str(os.getuid())
    pid_dir = isolated_runtime / "runtime" / f"hermes-spawn-{uid}"
    assert pid_dir.exists()
    assert proc.returncode == 1


def test_lock_without_metadata_is_busy(isolated_runtime: Path) -> None:
    uid = os.getuid()
    pid_dir = isolated_runtime / "runtime" / f"hermes-spawn-{uid}"
    pid_dir.mkdir(parents=True)
    lock_dir = pid_dir / "default.lock"
    lock_dir.mkdir()
    proc = _run_spawn(
        "start",
        "hello",
        env={
            "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
            "HOME": str(isolated_runtime),
            "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
            "HERMES_HOME": str(isolated_runtime / "hermes-home"),
        },
    )
    assert proc.returncode != 0
    assert "without owner metadata" in proc.stderr


def test_start_writes_pid_and_status_ok(isolated_runtime: Path) -> None:
    env = {
        "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
        "HOME": str(isolated_runtime),
        "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
        "HERMES_HOME": str(isolated_runtime / "hermes-home"),
    }
    start = _run_spawn("start", "smoke task", env=env, timeout=60)
    assert start.returncode == 0, start.stderr
    assert "Hermes started" in start.stdout
    status = _run_spawn("status", env=env)
    assert status.returncode == 0
    assert "Hermes running" in status.stdout
    stop = _run_spawn("stop", env=env)
    assert stop.returncode == 0


def test_stop_cleans_stale_pid_file(isolated_runtime: Path) -> None:
    uid = os.getuid()
    pid_dir = isolated_runtime / "runtime" / f"hermes-spawn-{uid}"
    pid_dir.mkdir(parents=True)
    pid_file = pid_dir / "default.pid"
    pid_file.write_text("999999 stale\n", encoding="utf-8")
    env = {
        "PERPETUA_TOOLS_ROOT": str(isolated_runtime / "pt"),
        "HOME": str(isolated_runtime),
        "XDG_RUNTIME_DIR": str(isolated_runtime / "runtime"),
        "HERMES_HOME": str(isolated_runtime / "hermes-home"),
    }
    proc = _run_spawn("stop", env=env)
    assert proc.returncode == 0
    assert not pid_file.exists() or "No active" in proc.stderr
