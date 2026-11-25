"""install-shell-hooks.sh provisions and re-creates the shell-safety hooks in a Claude home."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "bin/orama-system/skills/shell-hygiene/hooks"
GOTCHAS = HOOKS / "shell-gotchas.py"
INSTALL = ROOT / "bin/orama-system/scripts/install-shell-hooks.sh"


def _install(home: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(INSTALL), mode, "--claude-home", str(home)], capture_output=True, text=True)


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


def test_installer_is_bash_3_2_clean() -> None:
    """The installer and the first-run script must parse under the macOS system bash."""
    for script in (INSTALL, ROOT / "bin/orama-system/scripts/first-run-install.sh"):
        assert subprocess.run(["/bin/bash", "-n", str(script)], capture_output=True).returncode == 0, script
