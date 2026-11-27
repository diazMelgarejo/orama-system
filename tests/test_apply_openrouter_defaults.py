"""apply-openrouter-free-defaults.sh is a dry run unless told to write, and never copies the key into a file."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("jq") is None, reason="needs bash and jq")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply-openrouter-free-defaults.sh"
SECRET = "openrouter-literal-that-must-never-be-written"
LIVE = {"agents": {"defaults": {"model": {"primary": "p/m", "fallbacks": ["google/gemini-x"]}}}}


def _files(tmp_path: Path) -> tuple[Path, Path]:
    live = tmp_path / "home" / ".openclaw" / "openclaw.json"
    template = tmp_path / "root" / "alphaclaw-observability" / "config" / "openclaw.json"
    for path in (live, template):
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(LIVE), encoding="utf-8")
    return live, template


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # OPENCLAW_ROOT keeps companion-template detection inside the temp tree.
    env = {"HOME": str(tmp_path / "home"), "OPENCLAW_ROOT": str(tmp_path / "root"),
           "PATH": f"{Path(shutil.which('jq')).parent}{os.pathsep}/usr/bin:/bin", "OPENROUTER_API_KEY": SECRET}
    return subprocess.run(["/bin/bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("mode", [["--apply-live"], ["--repo-only"], ["--apply-live", "--dry-run", "--write"]],
                         ids=["live", "repo", "dry-run-wins"])
def test_nothing_is_changed_without_write(tmp_path: Path, mode: list[str]) -> None:
    live, template = _files(tmp_path)
    before = live.read_bytes(), template.read_bytes()
    done = _run(tmp_path, *mode)
    assert done.returncode == 0, done.stderr
    assert (live.read_bytes(), template.read_bytes()) == before
    assert not list(tmp_path.rglob("*.bak.*"))
    assert "DRY-RUN" in done.stdout


def test_write_patches_fallbacks_and_never_writes_the_key(tmp_path: Path) -> None:
    live, template = _files(tmp_path)
    done = _run(tmp_path, "--apply-live", "--write")
    assert done.returncode == 0, done.stderr
    live_cfg, template_cfg = json.loads(live.read_text()), json.loads(template.read_text())
    assert "openrouter/openrouter/free" in live_cfg["agents"]["defaults"]["model"]["fallbacks"]
    assert live_cfg["agents"]["defaults"]["model"]["primary"] == "p/m"
    assert "env" not in live_cfg, "the live config gets the key from the shell environment, not from a copy"
    assert template_cfg["env"]["OPENROUTER_API_KEY"] == "${OPENROUTER_API_KEY}"
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert SECRET not in path.read_text(errors="ignore"), path
    assert SECRET not in done.stdout + done.stderr


def test_an_existing_live_env_entry_is_left_alone(tmp_path: Path) -> None:
    live, _ = _files(tmp_path)
    live.write_text(json.dumps({**LIVE, "env": {"OPENROUTER_API_KEY": "operator-set-value"}}), encoding="utf-8")
    assert _run(tmp_path, "--apply-live", "--write").returncode == 0
    assert json.loads(live.read_text())["env"] == {"OPENROUTER_API_KEY": "operator-set-value"}
