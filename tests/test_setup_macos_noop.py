"""setup_macos.py runs on every start: its patches stay, and are harmless when there is nothing to patch.

The discovery-hub install changes a file the live stack runs, so it only happens when asked for.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup_macos.py"
NEW_SHAPE = {"agents": {"entries": {"main": {}}, "defaults": {"model": {"primary": "wandb/m"}}},
             "models": {"providers": {"ollama": {"models": [{"id": "m"}]}}}}


def _load(argv: list[str], home: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """A fresh module whose every target lives under a throwaway home."""
    monkeypatch.setattr(sys, "argv", ["setup_macos.py", *argv])
    spec = importlib.util.spec_from_file_location("setup_macos_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, relative in (
        ("OPENCLAW_JSON", ".openclaw/openclaw.json"),
        ("ALPHACLAW_JS", ".alphaclaw/node_modules/@chrysb/alphaclaw/bin/alphaclaw.js"),
        ("GATEWAY_JS", ".alphaclaw/node_modules/@chrysb/alphaclaw/lib/server/gateway.js"),
        ("MARKER_FILE", ".alphaclaw/.macos-patches.json"),
        ("OPENCLAW_SCRIPTS", ".openclaw/scripts"),
        ("DISCOVER_HUB_DST", ".openclaw/scripts/discover.py"),
    ):
        monkeypatch.setattr(module, name, home / relative)

    def never(*_args, **_kwargs):
        raise AssertionError("a no-op step must not restart OpenClaw")

    monkeypatch.setattr(module, "_restart_openclaw_if_running", never)
    return module


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_the_config_steps_leave_the_current_config_shape_alone_without_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load([], tmp_path, monkeypatch)
    module.OPENCLAW_JSON.parent.mkdir(parents=True)
    module.OPENCLAW_JSON.write_text(json.dumps(NEW_SHAPE), encoding="utf-8")
    before = _files(tmp_path)
    module.step_openclaw_json()
    module.step_mac_agent_thinking()
    assert _files(tmp_path) == before
    assert module._warnings == [] and module._fixes == []


def test_absent_alphaclaw_files_are_skipped_quietly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load([], tmp_path, monkeypatch)
    module.step_patch_alphaclaw()
    module.step_patch_gateway()
    assert _files(tmp_path) == {}
    assert module._warnings == [] and module._fixes == []


def test_already_patched_alphaclaw_files_stay_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load([], tmp_path, monkeypatch)
    module.ALPHACLAW_JS.parent.mkdir(parents=True)
    module.GATEWAY_JS.parent.mkdir(parents=True)
    module.ALPHACLAW_JS.write_text("\n".join(p["detect"] for p in module.ALL_PATCHES), encoding="utf-8")
    module.GATEWAY_JS.write_text(module._P_GATEWAY["detect"], encoding="utf-8")
    before = module.ALPHACLAW_JS.read_bytes(), module.GATEWAY_JS.read_bytes()
    module.step_patch_alphaclaw()
    module.step_patch_gateway()
    assert (module.ALPHACLAW_JS.read_bytes(), module.GATEWAY_JS.read_bytes()) == before
    assert module._fixes == []


def test_the_bundled_sources_are_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load([], tmp_path, monkeypatch)
    assert module.DISCOVER_HUB_SRC.is_file()
    module.step_self_discovery_skill()
    assert module._warnings == []


@pytest.mark.parametrize("existing", [None, "# the operator's own hub\n"], ids=["absent", "different"])
def test_the_discovery_hub_is_not_installed_unless_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, existing: str | None
) -> None:
    module = _load(["--quiet"], tmp_path, monkeypatch)
    if existing is not None:
        module.DISCOVER_HUB_DST.parent.mkdir(parents=True)
        module.DISCOVER_HUB_DST.write_text(existing, encoding="utf-8")
    before = _files(tmp_path)
    module.step_install_discover_hub()
    assert _files(tmp_path) == before
    assert "--install-discover-hub" in capsys.readouterr().out
    assert module._warnings == []


def test_asking_installs_the_hub_and_keeps_the_previous_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load(["--install-discover-hub"], tmp_path, monkeypatch)
    module.DISCOVER_HUB_DST.parent.mkdir(parents=True)
    module.DISCOVER_HUB_DST.write_text("# old hub\n", encoding="utf-8")
    module.step_install_discover_hub()
    assert module.DISCOVER_HUB_DST.read_bytes() == module.DISCOVER_HUB_SRC.read_bytes()
    kept = list(module.DISCOVER_HUB_DST.parent.glob("discover.py.before-setup-*"))
    assert [p.read_text(encoding="utf-8") for p in kept] == ["# old hub\n"]
