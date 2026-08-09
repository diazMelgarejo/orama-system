"""Tests for hermes-status health rollup."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
STATUS_PY = ROOT / "bin/orama-system/skills/hermes-harness/scripts/hermes_status.py"


def _load_status_module() -> types.ModuleType:
    """
    Load the Hermes status module from its repository path.
    
    Returns:
    	types.ModuleType: The dynamically loaded Hermes status module.
    """
    spec = importlib.util.spec_from_file_location("hermes_status", STATUS_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_status_includes_appendix_c_stubs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = _load_status_module()
    pt_path = str(tmp_path / "pt")
    monkeypatch.setattr(mod, "check_pt_root", lambda _r: ("ok", {"path": pt_path}))
    monkeypatch.setattr(mod, "check_spawn_session", lambda _r: ("ok", {"running": False}))
    monkeypatch.setattr(
        mod,
        "check_partner_canaries",
        lambda _r, skip_live=False, canary_timeout=30: ("ok", {"canaries": []}, []),
    )
    monkeypatch.setattr(mod, "check_profiles", lambda: ("ok", {"count": 1}, []))

    result = mod.build_status(tmp_path, skip_canaries=True)
    subs = result["data"]["subsystems"]
    for stub in mod.APPENDIX_C_STUBS:
        assert subs[stub] == "not_yet_implemented"


def test_build_status_partial_when_canaries_degraded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = _load_status_module()
    pt_path = str(tmp_path / "pt")
    monkeypatch.setattr(mod, "check_pt_root", lambda _r: ("ok", {"path": pt_path}))
    monkeypatch.setattr(mod, "check_spawn_session", lambda _r: ("ok", {"running": False}))
    monkeypatch.setattr(
        mod,
        "check_partner_canaries",
        lambda _r, skip_live=False, canary_timeout=30: (
            "degraded",
            {"canaries": [{"name": "LM Studio", "status": "FAIL", "required": True}]},
            ["required canary failed"],
        ),
    )
    monkeypatch.setattr(mod, "check_profiles", lambda: ("ok", {"count": 1}, []))

    result = mod.build_status(tmp_path, skip_canaries=False)
    assert result["status"] == "partial"
    assert result["data"]["subsystems"]["partner_canaries"] == "degraded"


def test_check_pt_root_uses_adjacent_resolver_not_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, git_bin: str
) -> None:
    mod = _load_status_module()
    repo_root = tmp_path / "orama-system"
    repo_root.mkdir()
    subprocess.run([git_bin, "init", "-q"], cwd=repo_root, check=True)
    malicious_resolver = repo_root / "bin/orama-system/skills/hermes-harness/scripts"
    malicious_resolver.mkdir(parents=True)
    (malicious_resolver / "resolve_perp_harness.sh").write_text(
        "return 42\n",
        encoding="utf-8",
    )

    pt_root = tmp_path / "Perpetua-Tools"
    pt_root.mkdir()
    subprocess.run([git_bin, "init", "-q"], cwd=pt_root, check=True)
    (pt_root / "orchestrator").mkdir()
    (pt_root / "orchestrator" / "fastapi_app.py").write_text("# fixture\n", encoding="utf-8")
    (repo_root / ".paths").write_text(f'PT_DIR="{pt_root}"\n', encoding="utf-8")

    monkeypatch.setenv("ORAMA_SYSTEM_PATH", str(repo_root))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for key in (
        "PERPETUA_TOOLS_PATH",
        "PT_DIR",
        "PT_HOME",
        "PERPETUA_TOOLS_ROOT",
        "PERPETUATOOLSROOT",
    ):
        monkeypatch.delenv(key, raising=False)

    status, data = mod.check_pt_root(repo_root)
    assert status == "ok"
    assert data["path"] == str(pt_root)


def test_main_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load_status_module()
    monkeypatch.setattr(
        mod,
        "build_status",
        lambda *a, **k: mod._canonical_result(status="ok", data={"subsystems": {"pt_root": "ok"}}),
    )
    rc = mod.main(["--json", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["command"] == "hermes-status"
    assert payload["status"] == "ok"
