"""Tests for the W&B Cline launcher (bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py).

The launcher builds a throwaway Cline config that Cline 3.0.74 accepts (tokenSource "manual",
millisecond-Z updatedAt), refuses effort levels other than medium/high/low, keeps the key out of
argv, and deletes the config afterwards. A stub `cline` on PATH records what it was given.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MODULE = (Path(__file__).resolve().parent.parent / "bin" / "orama-system" / "skills"
           / "cline-wandb" / "scripts" / "launch_cline_wandb.py")
_spec = importlib.util.spec_from_file_location("launch_cline_wandb", _MODULE)
launcher = importlib.util.module_from_spec(_spec)
sys.modules["launch_cline_wandb"] = launcher
_spec.loader.exec_module(launcher)

FAKE_KEY = "wandb-test-key-0123456789"
_TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")


def test_timestamp_uses_javascript_iso_format() -> None:
    assert _TS.match(launcher.cline_timestamp())


def test_config_entry_is_cline_3_0_74_compatible() -> None:
    cfg = launcher.build_config(FAKE_KEY, launcher.DEFAULT_MODEL, "high", 30000)
    entry = cfg["providers"]["openai-compatible"]
    assert entry["tokenSource"] == "manual"
    assert _TS.match(entry["updatedAt"])
    settings = entry["settings"]
    assert settings["model"] == "deepseek-ai/DeepSeek-V4.1-Flash-1017"
    assert settings["baseUrl"] == "https://api.inference.wandb.ai/v1"
    assert settings["reasoning"] == {"enabled": True, "effort": "high"}
    assert cfg["lastUsedProvider"] == "openai-compatible"


def test_efforts_are_medium_high_low_only() -> None:
    assert launcher.EFFORTS == ("medium", "high", "low")


@pytest.mark.parametrize("bad", ["max", "xhigh", "none"])
def test_forbidden_effort_is_refused(bad: str) -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args(["--effort", bad, "--", "task"])


def test_prompt_is_required() -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args([])


def test_default_effort_is_high_because_medium_is_rejected_on_v4_1() -> None:
    assert launcher.parse_args(["--", "task"]).effort == "high"


def test_key_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    assert launcher.read_key() == FAKE_KEY


def test_key_falls_back_to_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(launcher.KEYVAR, raising=False)
    env_file = tmp_path / ".env.wandb"
    env_file.write_text(f"# comment\nexport {launcher.KEYVAR}='{FAKE_KEY}'\n")
    assert launcher.read_key(env_file=str(env_file)) == FAKE_KEY


def test_missing_key_exits_without_echoing_anything_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(launcher.KEYVAR, raising=False)
    with pytest.raises(SystemExit) as exc:
        launcher.read_key(env_file=str(tmp_path / "missing"))
    assert launcher.KEYVAR in str(exc.value)


@pytest.fixture
def stub_cline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Put a fake `cline` first on PATH; it records argv and a copy of the config it was given."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    record = tmp_path / "record"
    record.mkdir()
    script = bindir / "cline"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{record}/argv.txt"\n'
        'while [ $# -gt 0 ]; do if [ "$1" = "--config" ]; then CFG="$2"; fi; shift; done\n'
        f'cp "$CFG/data/settings/providers.json" "{record}/providers.json"\n'
        f'echo "$CFG" > "{record}/cfgdir.txt"\n'
        f'stat -f "%Lp" "$CFG" > "{record}/dirmode.txt" 2>/dev/null || stat -c "%a" "$CFG" > "{record}/dirmode.txt"\n'
        f'stat -f "%Lp" "$CFG/data/settings/providers.json" > "{record}/filemode.txt" 2>/dev/null '
        f'|| stat -c "%a" "$CFG/data/settings/providers.json" > "{record}/filemode.txt"\n'
        "exit 0\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(launcher.KEYVAR, FAKE_KEY)
    return {"record": record}


def test_run_passes_explicit_route_and_keeps_key_out_of_argv(stub_cline: dict[str, Path]) -> None:
    rc = launcher.main(["--effort", "medium", "--model", "deepseek-ai/DeepSeek-V4-Flash-0731", "--", "do the task"])
    record = stub_cline["record"]
    argv = (record / "argv.txt").read_text().splitlines()
    assert rc == 0
    assert argv[:1] == ["--config"] and argv[2:4] == ["-P", "openai-compatible"]
    assert ["-m", "deepseek-ai/DeepSeek-V4-Flash-0731"] == argv[4:6]
    assert ["--thinking", "medium"] == argv[6:8]
    assert argv[-1] == "do the task"
    assert FAKE_KEY not in "\n".join(argv)


def test_config_is_private_and_removed_afterwards(stub_cline: dict[str, Path]) -> None:
    launcher.main(["--", "task"])
    record = stub_cline["record"]
    assert (record / "dirmode.txt").read_text().strip() == "700"
    assert (record / "filemode.txt").read_text().strip() == "600"
    cfgdir = Path((record / "cfgdir.txt").read_text().strip())
    assert not cfgdir.exists()
    seen = json.loads((record / "providers.json").read_text())
    assert seen["providers"]["openai-compatible"]["tokenSource"] == "manual"


def test_never_touches_the_operators_real_cline_directory(stub_cline: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".cline").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    launcher.main(["--", "task"])
    assert list((home / ".cline").iterdir()) == []
