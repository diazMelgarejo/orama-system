"""Start-up never loads a local model itself: it asks the Perpetua-Tools one-model gate, or loads nothing."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOADS = re.compile(r"/api/(generate|chat|embed|embeddings)|/api/v1/models/load|\blms\s+load\b|\bollama\s+run\b")
LIMITS = ("OLLAMA_MAX_LOADED_MODELS=1", "OLLAMA_NUM_PARALLEL=1", "OLLAMA_KEEP_ALIVE=5m")


def _tracked_scripts() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "--", "*.sh", "*.ps1"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [n for n in out.split("\0") if n and not n.startswith(("tests/", "scripts/tests/", "docs/"))]


def _function(script: str, name: str) -> str:
    text = (ROOT / script).read_text(encoding="utf-8")
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.M | re.S)
    assert match, f"{script} has no {name} function"
    return match.group()


def test_no_startup_script_loads_a_model_directly() -> None:
    offenders = {}
    for name in _tracked_scripts():
        lines = [line.strip() for line in (ROOT / name).read_text(encoding="utf-8", errors="ignore").splitlines()
                 if LOADS.search(line) and not line.lstrip().startswith("#")]
        if lines and name in ("start.sh", "scripts/bootstrap-environment.sh"):
            offenders[name] = lines
    assert offenders == {}


def test_startup_starts_ollama_with_the_one_model_limits() -> None:
    serve = [line for line in (ROOT / "start.sh").read_text(encoding="utf-8").splitlines()
             if "ollama serve >>" in line]
    assert serve and all(setting in serve[0] for setting in LIMITS), serve


@pytest.mark.parametrize(
    "script, name", [("start.sh", "_ollama_warm_via_gate"), ("scripts/bootstrap-environment.sh", "ensure_ollama_warm")]
)
def test_without_the_gate_nothing_is_loaded(tmp_path: Path, script: str, name: str) -> None:
    calls = tmp_path / "calls"
    harness = f"""
set -u
_info() {{ echo "info $*"; }}; _warn() {{ echo "warn $*"; }}; log() {{ echo "log $*"; }}
curl() {{ echo curl >> "{calls}"; }}; python3() {{ echo python >> "{calls}"; }}
PT_DIR=""; PT_PYTHON=""; LOG_DIR="{tmp_path}"; PT_ROOT="{tmp_path}/absent"; unset PERPETUA_TOOLS_ROOT
{_function(script, name)}
{name} qwen3.5:9b-mlx; wait
"""
    done = subprocess.run(["/bin/bash", "-c", harness], capture_output=True, text=True, check=True, timeout=20)

    assert "gate unavailable" in done.stdout
    assert not calls.exists()


@pytest.mark.parametrize(
    "script, name", [("start.sh", "_ollama_warm_via_gate"), ("scripts/bootstrap-environment.sh", "ensure_ollama_warm")]
)
def test_with_the_gate_the_load_is_requested_only_through_it(tmp_path: Path, script: str, name: str) -> None:
    module = tmp_path / "pt" / "src" / "perpetua_tools"
    module.mkdir(parents=True)
    calls = tmp_path / "calls"
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "local_model_gate.py").write_text(
        f"import sys\nopen({str(calls)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n", encoding="utf-8")
    harness = f"""
set -u
_info() {{ :; }}; _warn() {{ :; }}; log() {{ :; }}; curl() {{ echo curl >> "{calls}"; }}
PT_DIR="{tmp_path}/pt"; PT_PYTHON=""; LOG_DIR="{tmp_path}"; PT_ROOT="{tmp_path}/pt"; unset PERPETUA_TOOLS_ROOT
{_function(script, name)}
{name} qwen3.5:9b-mlx; wait
"""
    subprocess.run(["/bin/bash", "-c", harness], capture_output=True, text=True, check=True, timeout=20)

    seen = calls.read_text(encoding="utf-8").splitlines()
    assert "ensure ollama qwen3.5:9b-mlx" in seen
    assert "curl" not in seen


# ------------------------------------------------------------- the limits are lost at reboot, so every launch sets them


def test_start_sets_the_limits_before_any_ollama_setting_can_skip_them() -> None:
    body = _function("start.sh", "_ollama_ensure_ready")
    assert body.index("_ollama_apply_limits") < body.index("OLLAMA_AUTO_START")


def test_start_sets_the_three_limits_in_the_login_session(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    harness = f"""
set -u
_info() {{ :; }}; _warn() {{ :; }}; launchctl() {{ echo "$*" >> "{calls}"; }}
{_function("start.sh", "_ollama_apply_limits")}
_ollama_apply_limits; echo "$OLLAMA_MAX_LOADED_MODELS $OLLAMA_NUM_PARALLEL $OLLAMA_KEEP_ALIVE"
"""
    done = subprocess.run(["/bin/bash", "-c", harness], capture_output=True, text=True, check=True, timeout=20)

    assert done.stdout.split() == ["1", "1", "5m"]
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "setenv OLLAMA_MAX_LOADED_MODELS 1", "setenv OLLAMA_NUM_PARALLEL 1", "setenv OLLAMA_KEEP_ALIVE 5m"]


@pytest.mark.parametrize("report, warned", [
    ('"OLLAMA_MAX_LOADED_MODELS is not 1 in the running Ollama server"', True), ('"limit_problems": []', False)])
def test_start_warns_when_the_running_server_lacks_the_limits(tmp_path: Path, report: str, warned: bool) -> None:
    module = tmp_path / "pt" / "src" / "perpetua_tools"
    module.mkdir(parents=True)
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "local_model_gate.py").write_text(f"print({report!r})\n", encoding="utf-8")
    harness = f"""
set -u
_info() {{ :; }}; _warn() {{ echo "WARN $*"; }}; PT_DIR="{tmp_path}/pt"; PT_PYTHON=""
{_function("start.sh", "_ollama_check_limits")}
_ollama_check_limits
"""
    done = subprocess.run(["/bin/bash", "-c", harness], capture_output=True, text=True, check=True, timeout=20)

    assert ("reopen Ollama" in done.stdout) is warned


def test_windows_start_sets_the_limits_for_the_process_and_the_account() -> None:
    text = (ROOT / "platform/windows/start.ps1").read_text(encoding="utf-8")
    body = re.search(r"^function Set-OllamaOneModelLimits \{.*?^\}", text, re.M | re.S).group()

    for needle in ("OLLAMA_MAX_LOADED_MODELS = '1'", "OLLAMA_NUM_PARALLEL = '1'", "OLLAMA_KEEP_ALIVE = '5m'",
                   "'Process'", "'User'"):
        assert needle in body
    calls = [m.start() for m in re.finditer(r"^Set-OllamaOneModelLimits\s*$", text, re.M)]
    assert len(calls) == 1 and calls[0] > text.index("if ($Status) {"), "status runs must not write settings"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is not installed")
def test_windows_limit_function_runs_and_sets_this_process() -> None:
    text = (ROOT / "platform/windows/start.ps1").read_text(encoding="utf-8")
    body = re.search(r"^function Set-OllamaOneModelLimits \{.*?^\}", text, re.M | re.S).group()
    script = body + '\nSet-OllamaOneModelLimits\n"$env:OLLAMA_MAX_LOADED_MODELS $env:OLLAMA_NUM_PARALLEL $env:OLLAMA_KEEP_ALIVE"'

    done = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, check=True, timeout=90)

    assert done.stdout.strip().splitlines()[-1] == "1 1 5m"
