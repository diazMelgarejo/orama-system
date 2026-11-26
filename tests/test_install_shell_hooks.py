"""install-shell-hooks.sh provisions and re-creates the shell-safety hooks in a Claude home."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "/bin/bash"
HOOKS = ROOT / "bin/orama-system/skills/shell-hygiene/hooks"
GOTCHAS = HOOKS / "shell-gotchas.py"
INSTALL = ROOT / "bin/orama-system/scripts/install-shell-hooks.sh"


def _install(home: Path, mode: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(INSTALL), mode, "--claude-home", str(home), *extra], capture_output=True, text=True)


def _gotchas_command(home: Path) -> str:
    return next(c for c in _commands(home) if "shell-gotchas.py" in c)


def _settings(home: Path) -> dict:
    return json.loads((home / "settings.json").read_text(encoding="utf-8"))


def _commands(home: Path) -> list[str]:
    return [h["command"] for g in _settings(home)["hooks"]["PreToolUse"] for h in g["hooks"]]


def test_check_reports_drift_on_an_empty_home_and_changes_nothing(tmp_path: Path) -> None:
    done = _install(tmp_path, "--check")
    assert done.returncode == 1 and "DRIFT" in done.stdout
    assert list(tmp_path.iterdir()) == []


def test_apply_provisions_then_is_idempotent_and_check_passes(tmp_path: Path) -> None:
    first = _install(tmp_path, "--apply")
    assert first.returncode == 0 and "installed hooks/shell-gotchas.py" in first.stdout
    assert (tmp_path / "hooks/shell-gotchas.py").read_bytes() == GOTCHAS.read_bytes()
    assert (tmp_path / "hooks/no-workstation-paths.py").read_bytes() == (HOOKS / "no-workstation-paths.py").read_bytes()
    assert any("shell-gotchas.py" in c for c in _commands(tmp_path))
    again = _install(tmp_path, "--apply")
    assert "nothing changed" in again.stdout
    assert _install(tmp_path, "--check").returncode == 0


def test_apply_merges_without_clobbering_and_retires_the_legacy_hook(tmp_path: Path) -> None:
    """Other settings and other hooks survive; the superseded registration is removed; a backup exists."""
    (tmp_path / "settings.json").write_text(json.dumps({
        "model": "keep-me",
        "hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /x/zsh-reserved-vars.py"},
                                         {"type": "command", "command": "other-hook"}]},
            {"matcher": "Read", "hooks": [{"type": "command", "command": "reader"}]},
        ], "SessionStart": [{"hooks": [{"type": "command", "command": "start"}]}]},
    }), encoding="utf-8")
    done = _install(tmp_path, "--apply")
    assert done.returncode == 0 and "retired the zsh-reserved-vars.py registration" in done.stdout
    data = _settings(tmp_path)
    commands = _commands(tmp_path)
    assert data["model"] == "keep-me" and "SessionStart" in data["hooks"]
    assert "other-hook" in commands and "reader" in commands
    assert not any("zsh-reserved-vars" in c for c in commands)
    assert list(tmp_path.glob("settings.json.bak-*"))


def test_existing_registration_is_recognised_not_duplicated(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": 'python3 "$HOME/.claude/hooks/no-workstation-paths.py"'}]},
    ]}}), encoding="utf-8")
    _install(tmp_path, "--apply")
    assert sum("no-workstation-paths.py" in c for c in _commands(tmp_path)) == 1


def test_drifted_hook_file_is_detected_and_repaired(tmp_path: Path) -> None:
    _install(tmp_path, "--apply")
    (tmp_path / "hooks/shell-gotchas.py").write_text("# tampered\n", encoding="utf-8")
    assert _install(tmp_path, "--check").returncode == 1
    assert _install(tmp_path, "--apply").returncode == 0
    assert (tmp_path / "hooks/shell-gotchas.py").read_bytes() == GOTCHAS.read_bytes()


def test_invalid_settings_json_is_left_untouched(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text("{ not json", encoding="utf-8")
    done = _install(tmp_path, "--apply")
    assert done.returncode != 0 and "not valid JSON" in done.stderr
    assert (tmp_path / "settings.json").read_text(encoding="utf-8") == "{ not json"
    assert not (tmp_path / "hooks").exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="requires native macOS /bin/bash 3.2")
def test_installer_is_bash_3_2_clean() -> None:
    """On macOS, both scripts must parse under the system bash; other hosts need their own receipt."""
    for script in (INSTALL, ROOT / "bin/orama-system/scripts/first-run-install.sh"):
        assert subprocess.run(["/bin/bash", "-n", str(script)], capture_output=True).returncode == 0, script


def test_help_prints_only_the_header_comment_never_script_code() -> None:
    """--help and usage errors show documentation lines only: no `set -euo` or other code leaks in."""
    for args in (["--help"], ["--bogus"]):
        done = subprocess.run(["bash", str(INSTALL), *args], capture_output=True, text=True)
        text = done.stdout + done.stderr
        assert "install-shell-hooks.sh" in text and "--mode enforce" in text
        assert "set -euo" not in text and "SCRIPT_DIR" not in text


def test_fresh_apply_registers_warn_and_mode_is_preserved_until_changed(tmp_path: Path) -> None:
    """New installs start in warn; --mode enforce promotes; a later plain --apply keeps enforce."""
    _install(tmp_path, "--apply")
    assert _gotchas_command(tmp_path).startswith("SHELL_GOTCHAS_MODE=warn ")
    promoted = _install(tmp_path, "--apply", "--mode", "enforce")
    assert promoted.returncode == 0 and "registered shell-gotchas.py in enforce mode" in promoted.stdout
    assert not _gotchas_command(tmp_path).startswith("SHELL_GOTCHAS_MODE=")
    again = _install(tmp_path, "--apply")
    assert "nothing changed" in again.stdout and not _gotchas_command(tmp_path).startswith("SHELL_GOTCHAS_MODE=")
    assert _install(tmp_path, "--check").returncode == 0


def test_check_reports_drift_when_the_registered_mode_differs_from_the_requested_one(tmp_path: Path) -> None:
    _install(tmp_path, "--apply", "--mode", "enforce")
    drift = _install(tmp_path, "--check", "--mode", "warn")
    assert drift.returncode == 1 and "DRIFT" in drift.stdout and "enforce mode, not --mode warn" in drift.stdout
    assert _install(tmp_path, "--check", "--mode", "enforce").returncode == 0


def test_apply_writes_through_symlinks_and_keeps_the_links(tmp_path: Path) -> None:
    """Dotfiles symlinks stay intact; hosts without symlink privilege skip this capability receipt."""
    home, dotfiles = tmp_path / "home", tmp_path / "dotfiles"
    (home / "hooks").mkdir(parents=True)
    dotfiles.mkdir()
    (dotfiles / "settings.json").write_text(json.dumps({"model": "keep-me"}), encoding="utf-8")
    (dotfiles / "shell-gotchas.py").write_text("# stale\n", encoding="utf-8")
    try:
        (home / "settings.json").symlink_to(dotfiles / "settings.json")
        (home / "hooks" / "shell-gotchas.py").symlink_to(dotfiles / "shell-gotchas.py")
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1314:
            raise
        pytest.skip(f"symlink creation unavailable without Windows symlink privilege: {exc}")
    done = _install(home, "--apply")
    assert done.returncode == 0, done.stderr
    assert (home / "settings.json").is_symlink() and (home / "hooks" / "shell-gotchas.py").is_symlink()
    assert json.loads((dotfiles / "settings.json").read_text(encoding="utf-8"))["model"] == "keep-me"
    assert any("shell-gotchas.py" in c for c in _commands(home))
    assert (dotfiles / "shell-gotchas.py").read_bytes() == GOTCHAS.read_bytes()


def test_relative_custom_home_is_absolute_and_shell_quoted(tmp_path: Path) -> None:
    home = tmp_path / "claude $literal ' space"
    relative = os.path.relpath(home, Path.cwd())
    done = _install(Path(relative), "--apply")
    assert done.returncode == 0, done.stderr
    command = _gotchas_command(home)
    assert shlex.split(command)[-1] == str(home / "hooks/shell-gotchas.py")
    result = subprocess.run([BASH, "-c", command], cwd="/", input='{}', capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert _install(Path(relative), "--check").returncode == 0


@pytest.mark.parametrize("settings", [
    [], {"hooks": None}, {"hooks": {"PreToolUse": None}},
    {"hooks": {"PreToolUse": [None]}},
    {"hooks": {"PreToolUse": [{"hooks": None}]}},
    {"hooks": {"PreToolUse": [{"hooks": [None]}]}},
    {"hooks": {"PreToolUse": [{"hooks": [{"command": None}]}]}},
])
def test_invalid_settings_structure_is_rejected_before_writes(tmp_path: Path, settings: object) -> None:
    path = tmp_path / "settings.json"
    original = json.dumps(settings)
    path.write_text(original, encoding="utf-8")
    done = _install(tmp_path, "--apply")
    assert done.returncode != 0 and "invalid hooks.PreToolUse structure" in done.stderr
    assert path.read_text(encoding="utf-8") == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.json"]


@pytest.mark.parametrize("warn", [True, False])
def test_stale_registration_is_repaired_preserving_mode(tmp_path: Path, warn: bool) -> None:
    assert _install(tmp_path, "--apply").returncode == 0
    settings = _settings(tmp_path)
    entry = next(h for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]
                 if "shell-gotchas.py" in h["command"])
    entry["command"] = ("SHELL_GOTCHAS_MODE=warn " if warn else "") + "python3 /removed/hooks/shell-gotchas.py"
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    assert _install(tmp_path, "--check").returncode == 1
    assert _install(tmp_path, "--apply").returncode == 0
    assert _gotchas_command(tmp_path).startswith("SHELL_GOTCHAS_MODE=warn ") == warn
    assert shlex.split(_gotchas_command(tmp_path))[-1] == str(tmp_path / "hooks/shell-gotchas.py")
    assert _install(tmp_path, "--check").returncode == 0


def test_check_does_not_run_drifted_hook(tmp_path: Path) -> None:
    assert _install(tmp_path, "--apply").returncode == 0
    hook = tmp_path / "hooks/shell-gotchas.py"
    marker = tmp_path / "executed"
    hook.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8")
    assert _install(tmp_path, "--check").returncode == 1
    assert not marker.exists()
    assert _install(tmp_path, "--apply").returncode == 0
    assert hook.read_bytes() == GOTCHAS.read_bytes()


def test_install_preserves_custom_hooks_that_mention_a_managed_filename(tmp_path: Path) -> None:
    """The installer owns only direct registrations of the bundled Python scripts."""
    custom = {"type": "command", "command": "echo shell-gotchas.py"}
    settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [custom]}]}}
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    done = _install(tmp_path, "--apply")
    assert done.returncode == 0, done.stderr
    assert custom["command"] in _commands(tmp_path)
    assert _install(tmp_path, "--check").returncode == 0
