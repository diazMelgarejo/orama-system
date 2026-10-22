"""Executable preflight checks must resolve configuration without launching agents."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from bin.agents import dispatcher


pytestmark = pytest.mark.integration


EXPECTED_COMMANDS = {
    "antigravity": "agy",
    "gemini": "gemini",
    "codex": "codex",
    "cursor": "cursor-agent",
    "claude": "claude",
    "ollama": "ollama",
    "windsurf": "windsurf",
    "cline": "cline",
    "kimi": "kimi",
}


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


def test_registry_matches_documented_agents() -> None:
    """The registry, its expected commands and the operator README cannot drift apart."""
    registry = {name: entry.command for name, entry in dispatcher.BINARY_REGISTRY.items()}
    assert registry == EXPECTED_COMMANDS
    readme = (Path(dispatcher.__file__).parent / "README.md").read_text(encoding="utf-8").lower()
    for name, command in EXPECTED_COMMANDS.items():
        if name != command:
            assert f"`{name}` to `{command}`" in readme
        else:
            assert name in readme
    assert "(`cline`" in readme and "(`kimi`" in readme


@pytest.mark.parametrize("name,command", sorted(EXPECTED_COMMANDS.items()))
def test_path_discovery_uses_actual_command_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, command: str
) -> None:
    """Public agent labels may differ from the installed executable name."""
    binary = _executable(tmp_path, command)
    monkeypatch.delenv(dispatcher.BINARY_REGISTRY[name].env_var, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert Path(dispatcher.resolve_binary_path(name)).samefile(binary)


@pytest.mark.parametrize("route", ["environment", "explicit"])
@pytest.mark.parametrize("configured", ["", "missing", "not executable", "directory", "nul\x00value"])
def test_invalid_override_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured: str, route: str
) -> None:
    """Broken configuration must be reported instead of selecting another binary."""
    _executable(tmp_path, "codex")
    (tmp_path / "not executable").write_text("data", encoding="utf-8")
    (tmp_path / "directory").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path))
    nul = "\x00" in configured
    if nul and route == "environment":
        pytest.skip("an environment variable cannot hold a NUL")
    value = configured if nul or not configured else str(tmp_path / configured)
    if route == "environment":
        monkeypatch.setenv("CODEX_BIN", value)
        explicit = None
    else:
        monkeypatch.setenv("CODEX_BIN", str(tmp_path / "codex"))  # a valid fallback that must stay unused
        explicit = value
    with pytest.raises(ValueError, match="CODEX_BIN|executable"):
        dispatcher.resolve_binary_path("codex", explicit)


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
    monkeypatch.setattr(dispatcher.shutil, "which", lambda candidate, path=None: str(binary))
    if accepted:
        assert dispatcher.resolve_binary_path("codex", str(binary)) == str(binary)
    else:
        with pytest.raises(ValueError, match="executable"):
            dispatcher.resolve_binary_path("codex", str(binary))


def test_bare_name_found_only_through_working_directory_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A local command is ignored when no non-empty PATH directory contains it."""
    _executable(tmp_path, "codex")
    other = tmp_path / "bin"
    other.mkdir()
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(other))
    with pytest.raises(ValueError, match="unavailable"):
        dispatcher.resolve_binary_path("codex")


def test_bare_name_skips_working_directory_and_uses_later_path_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A local shadow cannot block the same command in an approved PATH directory."""
    _executable(tmp_path, "codex")
    trusted = tmp_path / "trusted-bin"
    trusted.mkdir()
    binary = _executable(trusted, "codex")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep + str(trusted))
    assert Path(dispatcher.resolve_binary_path("codex")).samefile(binary)


def test_windows_bare_name_uses_path_entry_after_working_directory_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows bare-name lookup ignores a working-directory shadow and honors PATHEXT."""
    shadow = tmp_path / "codex.CMD"
    shadow.write_text("fixture", encoding="utf-8")
    trusted = tmp_path / "trusted-bin"
    trusted.mkdir()
    binary = trusted / "codex.CMD"
    binary.write_text("fixture", encoding="utf-8")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE;.CMD")
    monkeypatch.setenv("PATH", str(trusted))
    assert Path(dispatcher.resolve_binary_path("codex")).samefile(binary)


def test_windows_bare_dotted_name_uses_pathext_in_trusted_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-executable dotted command still receives the PATHEXT fallback."""
    trusted = tmp_path / "trusted-bin"
    trusted.mkdir()
    binary = trusted / "codex.v2.CMD"
    binary.write_text("fixture", encoding="utf-8")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE;.CMD")
    monkeypatch.setenv("PATH", str(trusted))
    assert Path(dispatcher.resolve_binary_path("codex", "codex.v2")).samefile(binary)


def test_windows_drive_qualified_name_is_not_a_bare_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive-qualified Windows names cannot escape the configured PATH entries."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert not dispatcher._is_bare_command(r"C:codex.exe")


def test_empty_path_entry_does_not_search_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A leading empty PATH entry reads as the current directory in a shell and is not trusted."""
    _executable(tmp_path, "codex")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep + str(tmp_path / "elsewhere"))
    with pytest.raises(ValueError, match="unavailable"):
        dispatcher.resolve_binary_path("codex")


def test_quoted_path_entries_resolve_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows PATH entries are often quoted; a valid hit must resolve, not be refused."""
    binary = _executable(tmp_path, "codex")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.setenv("PATH", f'"{tmp_path}"')
    assert Path(dispatcher.resolve_binary_path("codex")).samefile(binary)


def test_unset_path_falls_back_to_the_default_search_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unset PATH uses os.defpath for both lookup and the PATH-only guard."""
    monkeypatch.delenv("PATH", raising=False)
    assert dispatcher._search_path() == os.defpath


def test_relative_pathname_resolves_against_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate with a separator is a pathname, so the result depends on where it runs."""
    binary = _executable(tmp_path, "agent")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "")
    assert Path(dispatcher.resolve_binary_path("codex", f".{os.sep}{binary.name}")).samefile(binary)
    monkeypatch.chdir(tmp_path.parent)
    with pytest.raises(ValueError, match="executable"):
        dispatcher.resolve_binary_path("codex", f".{os.sep}{binary.name}")


def test_home_directory_is_expanded_in_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``~`` in an override resolves to the home directory before lookup."""
    binary = _executable(tmp_path, "agent")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    resolved = dispatcher.resolve_binary_path("codex", f"~{os.sep}{binary.name}")
    assert Path(resolved).samefile(binary)


def test_unknown_agent_on_command_line_is_rejected_before_resolution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The parser rejects an unregistered agent: exit 2, usage on stderr, nothing on stdout."""
    with pytest.raises(SystemExit) as exit_info:
        dispatcher.main(["--check-binary", "not-an-agent"])
    captured = capsys.readouterr()
    assert exit_info.value.code == 2
    assert "invalid choice" in captured.err
    assert captured.out == ""

def test_windows_candidates_use_pathext_spelling_in_configured_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """File names are built from PATHEXT as configured, so case-sensitive filesystems match.

    The probe records the names tried, which keeps the check independent of whether the
    host filesystem folds case (a lower-cased ``.cmd`` passes on macOS and fails on Linux).
    """
    tried: list[str] = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("PATHEXT", ".EXE;.Cmd")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(Path, "is_file", lambda self: tried.append(self.name) or False)
    assert dispatcher._find_bare_command("codex") is None
    assert tried == ["codex.EXE", "codex.Cmd", "codex"]
    tried.clear()
    assert dispatcher._find_bare_command("codex.EXE") is None
    assert tried == ["codex.EXE", "codex.EXE.EXE", "codex.EXE.Cmd"]
