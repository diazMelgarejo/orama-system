"""Start-up scripts may warm the local model, but it must unload after five idle minutes."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDLE = "5m"
SETTING = re.compile(r"""(?:OLLAMA_KEEP_ALIVE|keep_alive)\\?["']?\s*[:= ]\s*\\?["']?(-?\d+[smh]?)""")


def _settings() -> dict[str, list[str]]:
    out = subprocess.run(["git", "ls-files", "-z", "--", "*.sh", "*.ps1", "*.py"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    found: dict[str, list[str]] = {}
    for name in out.split("\0"):
        path = ROOT / name
        if not name or name.startswith(("tests/", "scripts/tests/", "docs/")) or not path.is_file():
            continue
        values = SETTING.findall(path.read_text(encoding="utf-8", errors="ignore"))
        if values:
            found[name] = values
    return found


def test_the_pattern_reads_each_way_of_setting_the_keep_alive() -> None:
    for line, value in (
        ("launchctl setenv OLLAMA_KEEP_ALIVE 30m", "30m"), ("export OLLAMA_KEEP_ALIVE=24h", "24h"),
        ('-d \'{"model":"m","keep_alive":"30m"}\'', "30m"), ('-d "{\\"model\\":\\"m\\",\\"keep_alive\\":-1}"', "-1"),
        ('_info "ollama" "warming (keep_alive=-1)..."', "-1"),
    ):
        assert SETTING.findall(line) == [value], line


def test_every_tracked_script_lets_the_model_unload_after_five_idle_minutes() -> None:
    found = _settings()
    assert {"start.sh", "scripts/bootstrap-environment.sh"} <= set(found)
    assert {name: values for name, values in found.items() if set(values) != {IDLE}} == {}
