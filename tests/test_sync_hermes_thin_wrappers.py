"""Tests for sync_hermes_thin_wrappers.py — the hermes thin-wrapper sync helper.

Covers:
  - resolve_repo_root(): git success path and fallback to parents[5]
  - main(): missing installer → returns 2; argument routing (--verify-only,
    --dry-run, default --install); --hermes-home passthrough; subprocess
    returncode propagation.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = (
    ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "sync_hermes_thin_wrappers.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("sync_hermes_thin_wrappers", SYNC_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sw():
    return _load_module()


# ── resolve_repo_root ─────────────────────────────────────────────────────────

def test_resolve_repo_root_returns_path_on_git_success(sw):
    """When git succeeds, the returned value must be the path from git output."""
    fake_root = "/some/repo/root"
    with patch("subprocess.check_output", return_value=fake_root + "\n"):
        result = sw.resolve_repo_root()
    assert result == Path(fake_root)


def test_resolve_repo_root_fallback_on_called_process_error(sw):
    """CalledProcessError (not a git repo) must fall through to parents[5]."""
    with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(128, "git")):
        result = sw.resolve_repo_root()
    # Expect a Path object derived from the script file's parent hierarchy
    assert isinstance(result, Path)
    # The fallback is script.parents[5] — it should be an ancestor of the script
    script = Path(SYNC_SCRIPT).resolve()
    expected = script.parents[5]
    assert result == expected


def test_resolve_repo_root_fallback_on_file_not_found(sw):
    """FileNotFoundError (git not on PATH) must also trigger the fallback."""
    with patch("subprocess.check_output", side_effect=FileNotFoundError):
        result = sw.resolve_repo_root()
    assert isinstance(result, Path)
    script = Path(SYNC_SCRIPT).resolve()
    expected = script.parents[5]
    assert result == expected


def test_resolve_repo_root_strips_trailing_newline(sw):
    """Git output often ends with '\\n'; must not appear in the resulting Path."""
    fake_root = "/some/repo/root"
    with patch("subprocess.check_output", return_value=fake_root + "\n"):
        result = sw.resolve_repo_root()
    assert str(result) == fake_root


# ── main() — installer presence check ────────────────────────────────────────

def test_main_returns_2_when_installer_missing(sw, tmp_path, monkeypatch, capsys):
    """If the canonical installer does not exist, main() must return 2."""
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)
    # tmp_path has no installer
    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py"]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv
    assert rc == 2
    err = capsys.readouterr().err
    assert "ERROR" in err
    assert "canonical installer not found" in err


# ── main() — argument routing ─────────────────────────────────────────────────

def _make_fake_installer(tmp_path: Path) -> Path:
    """Create a stub installer script at the canonical path."""
    installer_dir = (
        tmp_path
        / "bin"
        / "orama-system"
        / "skills"
        / "hermes-harness"
        / "scripts"
    )
    installer_dir.mkdir(parents=True)
    installer = installer_dir / "install_hermes_thin_skills.py"
    installer.write_text("# stub installer\n")
    return installer


def test_main_default_passes_install_flag(sw, tmp_path, monkeypatch):
    """With no flags, main() must pass --install to the installer."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py"]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    cmd_args = run_mock.call_args[0][0]
    assert "--install" in cmd_args
    assert "--verify" not in cmd_args
    assert "--dry-run" not in cmd_args


def test_main_verify_only_passes_verify_flag(sw, tmp_path, monkeypatch):
    """--verify-only must translate to --verify for the installer."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py", "--verify-only"]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv

    cmd_args = run_mock.call_args[0][0]
    assert "--verify" in cmd_args
    assert "--install" not in cmd_args


def test_main_dry_run_passes_dry_run_flag(sw, tmp_path, monkeypatch):
    """--dry-run must pass --dry-run to the installer."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py", "--dry-run"]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv

    cmd_args = run_mock.call_args[0][0]
    assert "--dry-run" in cmd_args
    assert "--install" not in cmd_args
    assert "--verify" not in cmd_args


def test_main_hermes_home_is_forwarded(sw, tmp_path, monkeypatch):
    """--hermes-home DIR must be passed via HERMES_HOME env to the installer subprocess."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    hermes_home = str(tmp_path / "my-hermes-home")
    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py", "--hermes-home", hermes_home]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv

    _, kwargs = run_mock.call_args
    assert kwargs["env"]["HERMES_HOME"] == hermes_home
    cmd_args = run_mock.call_args[0][0]
    assert "--hermes-home" not in cmd_args


def test_main_no_hermes_home_when_not_provided(sw, tmp_path, monkeypatch):
    """When --hermes-home is absent, subprocess env must not override HERMES_HOME."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py"]
    try:
        sw.main()
    finally:
        sys.argv = old_argv

    cmd_args = run_mock.call_args[0][0]
    assert "--hermes-home" not in cmd_args
    _, kwargs = run_mock.call_args
    assert "HERMES_HOME" not in kwargs.get("env", {})


def test_main_propagates_installer_returncode(sw, tmp_path, monkeypatch):
    """main() must return whatever returncode the installer subprocess returns."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=3))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py"]
    try:
        rc = sw.main()
    finally:
        sys.argv = old_argv

    assert rc == 3


def test_main_command_uses_current_interpreter(sw, tmp_path, monkeypatch):
    """The subprocess command must use sys.executable, not a hardcoded 'python'."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(sw.subprocess, "run", run_mock)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py"]
    try:
        sw.main()
    finally:
        sys.argv = old_argv

    cmd_args = run_mock.call_args[0][0]
    assert cmd_args[0] == sys.executable


def test_main_mutual_exclusion_dry_run_and_verify_only(sw, tmp_path, monkeypatch):
    """--dry-run and --verify-only are mutually exclusive; argparse rejects both."""
    _make_fake_installer(tmp_path)
    monkeypatch.setattr(sw, "resolve_repo_root", lambda: tmp_path)

    old_argv = sys.argv
    sys.argv = ["sync_hermes_thin_wrappers.py", "--verify-only", "--dry-run"]
    try:
        with pytest.raises(SystemExit) as exc_info:
            sw.main()
    finally:
        sys.argv = old_argv

    assert exc_info.value.code == 2  # argparse exits 2 on usage error