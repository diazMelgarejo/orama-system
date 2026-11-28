"""openclaw_bootstrap proposes a config from the OpenClaw defaults and writes it only when told to."""
from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openclaw_bootstrap as bootstrap  # noqa: E402

W_AND_B = "wandb/deepseek-ai/DeepSeek-V4.1-Flash-1017"
SECRET = "xai-literal-that-must-never-be-written"


@pytest.fixture(autouse=True)
def hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A throwaway home, the vendored defaults only, and no provider key."""
    monkeypatch.setattr(bootstrap.Path, "home", lambda: tmp_path)
    for name in ("PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"):
        monkeypatch.setenv(name, str(tmp_path / "no-perpetua-tools"))
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    return tmp_path


def _paths(home: Path) -> tuple[Path, Path]:
    return home / ".openclaw", home / ".openclaw" / "openclaw.json"


def _proposal(output: str) -> dict:
    return json.loads(output[output.index("\n{") + 1: output.rindex("\n}") + 2])


def test_without_write_the_proposal_is_printed_and_nothing_is_created(hermetic: Path, capsys) -> None:
    config_dir, config_file = _paths(hermetic)
    assert bootstrap._write_openclaw_config(config_dir, config_file) is False
    assert not config_dir.exists()
    out = capsys.readouterr().out
    proposed = _proposal(out)
    assert proposed["agents"]["defaults"]["model"]["primary"] == W_AND_B
    assert proposed["gateway"]["bind"] == "loopback" and proposed["gateway"]["mode"] == "local"
    assert "--write" in out and "lmstudio" not in out


def test_without_write_an_existing_config_is_left_byte_identical(hermetic: Path) -> None:
    config_dir, config_file = _paths(hermetic)
    config_dir.mkdir()
    config_file.write_text('{"mine": true}', encoding="utf-8")
    assert bootstrap._write_openclaw_config(config_dir, config_file) is False
    assert config_file.read_text(encoding="utf-8") == '{"mine": true}'
    assert [p.name for p in config_dir.iterdir()] == ["openclaw.json"]


def test_write_creates_a_private_config_with_secrets_by_reference_only(
    hermetic: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    config_dir, config_file = _paths(hermetic)
    assert bootstrap._write_openclaw_config(config_dir, config_file, write=True) is True
    text = config_file.read_text(encoding="utf-8")
    assert SECRET not in text + capsys.readouterr().out
    assert json.loads(text)["models"]["providers"]["xai"]["apiKey"] == {
        "source": "env", "provider": "default", "id": "XAI_API_KEY"}
    assert "lmstudio" not in text
    if sys.platform != "win32":
        assert stat.S_IMODE(config_file.stat().st_mode) == 0o600


def test_write_keeps_a_backup_of_the_config_it_replaces(hermetic: Path) -> None:
    config_dir, config_file = _paths(hermetic)
    config_dir.mkdir()
    config_file.write_text('{"mine": true}', encoding="utf-8")
    assert bootstrap._write_openclaw_config(config_dir, config_file, write=True) is True
    backups = list(config_dir.glob("openclaw.json.before-bootstrap-*"))
    assert [b.read_text(encoding="utf-8") for b in backups] == ['{"mine": true}']


def test_the_list_shape_is_available_for_older_openclaw(hermetic: Path, capsys) -> None:
    config_dir, config_file = _paths(hermetic)
    bootstrap._write_openclaw_config(config_dir, config_file, shape="list")
    agents = _proposal(capsys.readouterr().out)["agents"]
    assert "list" in agents and "entries" not in agents


def test_unavailable_defaults_fail_closed(hermetic: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def unavailable():
        raise bootstrap.DefaultsUnavailable("fail closed: nothing to read")

    monkeypatch.setattr(bootstrap, "_resolve_defaults", unavailable)
    config_dir, config_file = _paths(hermetic)
    assert bootstrap._write_openclaw_config(config_dir, config_file, write=True) is False
    assert not config_file.exists()
    assert "fail closed" in capsys.readouterr().out


def test_the_runtime_payload_is_not_applied_without_write(hermetic: Path) -> None:
    payload = {"gateway": {"openclaw_config": {"gateway": {"port": 18789}}}}
    result = bootstrap.apply_runtime_payload(payload)
    assert result["applied"] is False
    assert not (hermetic / ".openclaw" / "openclaw.json").exists()


def test_the_command_line_offers_write_and_defaults_to_not_writing() -> None:
    assert bootstrap.build_parser().parse_args(["--bootstrap"]).write is False
    assert bootstrap.build_parser().parse_args(["--bootstrap", "--force", "--write"]).write is True


def test_the_script_hard_codes_no_local_route_or_lan_address() -> None:
    source = (ROOT / "scripts" / "openclaw_bootstrap.py").read_text(encoding="utf-8")
    assert "lmstudio-" not in source and "192.168." not in source
