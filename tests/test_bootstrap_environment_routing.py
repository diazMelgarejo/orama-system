"""The start-up bootstrap reports OpenClaw routing drift and never writes the config.

It used to rewrite agent routing on every start, putting manual-only local routes back. Changes now go
through the staged restore loop: start-up only reports, and prints the command that renders a patch.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash start-up script")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/bootstrap-environment.sh"
OLD_PRIMARY = "lmstudio-mac/qwen3.5-9b-mlx"


def _routing_function() -> str:
    """The routing function alone: sourcing the whole script would run every bootstrap step."""
    match = re.search(r"^report_gateway_routing\(\) \{\n.*?^\}\n", SCRIPT.read_text(encoding="utf-8"), re.S | re.M)
    assert match, "bootstrap-environment.sh has no report_gateway_routing function"
    return match.group(0)


def _run(home: Path) -> subprocess.CompletedProcess[str]:
    program = f'set -uo pipefail\nREPO="{ROOT}"\nlog(){{ printf "[bootstrap-env] %s\\n" "$*"; }}\n' \
              f"{_routing_function()}report_gateway_routing\n"
    env = {"HOME": str(home), "PATH": f"{Path(sys.executable).parent}{os.pathsep}/usr/bin:/bin",
           "PERPETUA_TOOLS_ROOT": str(home / "no-perpetua-tools")}
    return subprocess.run(["/bin/bash", "-c", program], env=env, capture_output=True, text=True, timeout=60)


def _config(home: Path, body: str) -> Path:
    path = home / ".openclaw" / "openclaw.json"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")
    return path


LIST_SHAPE = {"agents": {"list": [
    {"id": "orchestrator", "model": {"primary": OLD_PRIMARY}},
    {"id": "coder", "model": {"primary": "ollama/qwen3.5:9b-mlx"}},
    {"id": "autoresearcher", "model": {"primary": OLD_PRIMARY}},
]}}
ENTRIES_SHAPE = {"agents": {"entries": {"main": {}}, "defaults": {"model": {"primary": OLD_PRIMARY}}}}


@pytest.mark.parametrize("config", [LIST_SHAPE, ENTRIES_SHAPE], ids=["list", "entries"])
def test_drift_is_reported_and_the_config_is_left_byte_identical(tmp_path: Path, config: dict) -> None:
    path = _config(tmp_path, json.dumps(config))
    before = path.read_bytes()
    done = _run(tmp_path)
    assert done.returncode == 0, done.stderr
    assert path.read_bytes() == before
    assert "drift" in done.stdout
    assert "--render-patch" in done.stdout


def test_an_unreadable_config_is_reported_without_a_traceback_or_a_write(tmp_path: Path) -> None:
    path = _config(tmp_path, "{ not json")
    done = _run(tmp_path)
    assert done.returncode == 0
    assert path.read_text(encoding="utf-8") == "{ not json"
    assert "cannot read" in done.stdout
    assert "Traceback" not in done.stdout + done.stderr


def test_an_absent_config_is_skipped(tmp_path: Path) -> None:
    done = _run(tmp_path)
    assert done.returncode == 0 and "skip" in done.stdout
    assert not (tmp_path / ".openclaw").exists()


def test_the_bootstrap_script_hard_codes_no_agent_routes() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "lmstudio-mac" not in script and "lmstudio-win" not in script
    assert re.search(r"^report_gateway_routing$", script, re.M), "start-up does not call the report"
