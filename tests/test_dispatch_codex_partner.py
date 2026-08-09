"""Tests for dispatch_codex_partner.py (offline / dry-run)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "dispatch_codex_partner.py"
)


@pytest.fixture
def dispatch(monkeypatch):
    spec = importlib.util.spec_from_file_location("dispatch_codex_partner", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_build_pytest_prompt_uses_repo_relative_paths(dispatch):
    assert "tests/foo.py" in dispatch.build_pytest_prompt(["tests/foo.py"])
    assert "C:" not in dispatch.build_pytest_prompt(["tests/foo.py"])


def test_fanout_command_uses_cd_not_absolute_test_path(dispatch, monkeypatch, capsys):
    root = Path("/orama/repo")
    monkeypatch.setattr(dispatch.canaries, "_ensure_windows_partner_path", lambda: None)
    monkeypatch.setattr(dispatch.canaries, "_resolve_partner_cli", lambda _: "/bin/codex")
    monkeypatch.setattr(dispatch, "resolve_orama_repo_root", lambda: root)

    rc = dispatch.main(["--dry-run", "--pytest", "tests/test_verify_partner_canaries.py"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "repo_root=" + str(root) in out
    assert "-C" in out and str(root) in out
    assert "tests/test_verify_partner_canaries.py" in out
    assert "C:\\Users" not in out
    assert "dangerously-bypass-approvals-and-sandbox" in out


def test_interactive_profile_uses_ask_for_approval_never(dispatch, monkeypatch, capsys):
    root = Path("/orama/repo")
    monkeypatch.setattr(dispatch.canaries, "_ensure_windows_partner_path", lambda: None)
    monkeypatch.setattr(dispatch.canaries, "_resolve_partner_cli", lambda _: "/bin/codex")
    monkeypatch.setattr(dispatch, "resolve_orama_repo_root", lambda: root)

    rc = dispatch.main(["--dry-run", "--profile", "interactive", "hello"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ask-for-approval" in out
    assert "never" in out
    assert "danger-full-access" in out


def test_resolve_orama_repo_root_env_override(dispatch, monkeypatch, tmp_path):
    monkeypatch.setenv("ORAMA_SYSTEM_PATH", str(tmp_path))
    assert dispatch.resolve_orama_repo_root() == tmp_path.resolve()


def test_build_pytest_prompt_names_no_interpreter(dispatch):
    """uv run --no-sync -m pytest, never python/python3 -- sidesteps the
    Windows python.org-installer-vs-python3.exe-stub ambiguity entirely."""
    prompt = dispatch.build_pytest_prompt(["tests/foo.py"])
    assert "uv run --no-sync -m pytest" in prompt
    assert "python3" not in prompt
    assert " python " not in prompt


def _fanout_or_bounded_dispatch_calls_subprocess_with(dispatch, monkeypatch, profile, expected_stdin):
    root = Path("/orama/repo")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(dispatch.canaries, "_ensure_windows_partner_path", lambda: None)
    monkeypatch.setattr(dispatch.canaries, "_resolve_partner_cli", lambda _: "/bin/codex")
    monkeypatch.setattr(dispatch, "resolve_orama_repo_root", lambda: root)
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)

    rc = dispatch.main(["--profile", profile, "hello"])
    assert rc == 0
    assert captured.get("stdin") is expected_stdin


def test_fanout_dispatch_closes_stdin(dispatch, monkeypatch):
    """Non-interactive dispatch must never inherit an open, unfed parent
    stdin -- see codex-cli-v142-dispatch.md's Stdin hygiene section for the
    live hang this regression-guards against."""
    _fanout_or_bounded_dispatch_calls_subprocess_with(dispatch, monkeypatch, "fanout", dispatch.subprocess.DEVNULL)


def test_bounded_dispatch_closes_stdin(dispatch, monkeypatch):
    _fanout_or_bounded_dispatch_calls_subprocess_with(dispatch, monkeypatch, "bounded", dispatch.subprocess.DEVNULL)


def test_interactive_dispatch_keeps_real_stdin(dispatch, monkeypatch):
    """A human is present at a TTY for the interactive profile -- closing
    stdin here would break the ability to type into Codex at all."""
    _fanout_or_bounded_dispatch_calls_subprocess_with(dispatch, monkeypatch, "interactive", None)
