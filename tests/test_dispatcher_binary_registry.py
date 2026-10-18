"""Executable preflight checks must resolve configuration without launching agents."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from bin.agents import dispatcher


pytestmark = pytest.mark.integration


def _executable(tmp_path: Path, name: str) -> Path:
    """Create a harmless executable fixture, including names containing spaces."""
    if os.name == "nt":
        name += ".cmd"
    binary = tmp_path / name
    binary.write_text("@exit /b 99\n" if os.name == "nt" else "#!/bin/sh\nexit 99\n", encoding="utf-8")
    binary.chmod(0o700)
    return binary


def test_explicit_path_overrides_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit executable wins even when the registered override is invalid."""
    binary = _executable(tmp_path, "custom agent")
    monkeypatch.setenv("CODEX_BIN", str(tmp_path / "missing"))
    assert dispatcher.resolve_binary_path("Codex", str(binary)) == str(binary)


def test_environment_overrides_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The registered environment override wins over executable discovery."""
    binary = _executable(tmp_path, "custom codex")
    monkeypatch.setenv("CODEX_BIN", str(binary))
    monkeypatch.setenv("PATH", "")
    assert dispatcher.resolve_binary_path("codex") == str(binary)


@pytest.mark.parametrize("name,command", [("antigravity", "agy"), ("cursor", "cursor-agent"), ("ollama", "ollama")])
def test_path_discovery_uses_actual_command_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, command: str
) -> None:
    """Public agent labels may differ from the installed executable name."""
    binary = _executable(tmp_path, command)
    monkeypatch.delenv(dispatcher.BINARY_REGISTRY[name].env_var, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert Path(dispatcher.resolve_binary_path(name)).samefile(binary)


@pytest.mark.parametrize("configured", ["", "missing", "not executable", "directory", "nul\x00value"])
def test_invalid_override_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured: str
) -> None:
    """Broken configuration must be reported instead of selecting another binary."""
    _executable(tmp_path, "codex")
    (tmp_path / "not executable").write_text("data", encoding="utf-8")
    (tmp_path / "directory").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path))
    if "\x00" in configured:
        with pytest.raises(ValueError, match="CODEX_BIN|executable"):
            dispatcher.resolve_binary_path("codex", configured)
        return
    monkeypatch.setenv("CODEX_BIN", str(tmp_path / configured) if configured else "")
    with pytest.raises(ValueError, match="CODEX_BIN|executable"):
        dispatcher.resolve_binary_path("codex")


def test_unknown_agent_cannot_be_authorized_by_explicit_path(tmp_path: Path) -> None:
    """An explicit executable does not silently register an unsupported adapter."""
    with pytest.raises(ValueError, match="Unknown binary"):
        dispatcher.resolve_binary_path("unknown-agent", str(_executable(tmp_path, "custom")))


def test_preflight_reports_json_without_execution(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Preflight returns the executable, without invoking its deliberately failing body."""
    binary = _executable(tmp_path, "offline agent")
    assert dispatcher.main(["--check-binary", "codex", "--binary-path", str(binary)]) == 0
    assert json.loads(capsys.readouterr().out) == {"binary": "codex", "path": str(binary)}


def test_failed_preflight_has_actionable_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing executable is a failed check with the registered repair knob."""
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    assert dispatcher.main(["--check-binary", "codex"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "CODEX_BIN" in captured.err


def test_registry_entries_are_immutable() -> None:
    """Callers cannot alter the discovery policy for another caller."""
    with pytest.raises(TypeError):
        dispatcher.BINARY_REGISTRY["new-agent"] = dispatcher.BINARY_REGISTRY["codex"]


@pytest.mark.parametrize("suffix,accepted", [(".txt", False), (".CMD", True), ("", False)])
def test_windows_explicit_paths_respect_executable_suffixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str, accepted: bool
) -> None:
    """Old Windows which implementations must not certify arbitrary regular files."""
    binary = tmp_path / f"custom{suffix}"
    binary.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE;.CMD")
    monkeypatch.setattr(dispatcher.shutil, "which", lambda candidate: str(binary))
    if accepted:
        assert dispatcher.resolve_binary_path("codex", str(binary)) == str(binary)
    else:
        with pytest.raises(ValueError, match="executable"):
            dispatcher.resolve_binary_path("codex", str(binary))
