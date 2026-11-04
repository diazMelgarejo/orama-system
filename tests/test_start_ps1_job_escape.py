#!/usr/bin/env python3
"""start.ps1 relaunches outside a breakaway-denying job object and runs the latest origin/main.

Static checks run everywhere. The behavioural checks extract the launcher functions from
start.ps1 with the PowerShell parser and run them under Windows PowerShell, so they are
skipped on other hosts.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"
FUNCTIONS = ("Update-RunCheckout", "Get-LauncherJobState", "ConvertTo-LauncherLiteral", "Invoke-LauncherRelaunch")

WINDOWS_PS = shutil.which("powershell.exe") if sys.platform == "win32" else None
needs_windows = pytest.mark.skipif(WINDOWS_PS is None, reason="needs Windows PowerShell")


def _text() -> str:
    """Return start.ps1 as text."""
    return START_PS1.read_text(encoding="utf-8-sig")


def test_escape_block_runs_before_environment_loading_and_only_for_service_start_modes():
    """The block sits after mode parsing and before .env loading, and skips read-only and discover modes."""
    text = _text()
    read_only = text.index("$ReadOnlyMode = [bool]")
    block = text.index("$StartsServices = -not ($ReadOnlyMode -or $Discover)")
    env_load = text.index("$LoadLocalPs1 = Join-Path $RepoRoot")
    assert read_only < block < env_load
    guard = text[block:text.index("\n", text.index("if ($StartsServices", block))]
    assert "$env:OS -eq 'Windows_NT'" in guard
    assert "$env:ORAMA_START_RELAUNCHED -ne '1'" in guard


def test_relaunch_passes_environment_out_of_band_and_script_ends_with_success_exit():
    """Secrets travel in the WMI environment block, not the command line; the relayed exit code is explicit."""
    text = _text()
    assert "EnvironmentVariables = [string[]]$envList.ToArray()" in text
    assert "-EncodedCommand {1}' -f $hostExe, $encoded" in text
    assert text.rstrip().endswith("exit 0")


def test_opt_outs_are_documented_in_the_block():
    """Both behaviours can be switched off per run."""
    text = _text()
    assert "$env:ORAMA_START_UPDATE -ne '0'" in text
    assert "$env:ORAMA_JOB_ESCAPE -ne '0'" in text


def _functions_script(tmp_path: Path) -> Path:
    """Write the launcher functions, extracted from start.ps1 by the PowerShell parser, to a file."""
    out = tmp_path / "launcher_functions.ps1"
    names = ",".join(f"'{n}'" for n in FUNCTIONS)
    extract = (
        "$ast = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{START_PS1}', [ref]$null, [ref]$null); "
        "$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true) "
        f"| Where-Object {{ $_.Name -in @({names}) }}; "
        f"($fns | ForEach-Object {{ $_.Extent.Text }}) -join \"`r`n`r`n\" | Set-Content -LiteralPath '{out}' -Encoding UTF8"
    )
    subprocess.run([WINDOWS_PS, "-NoProfile", "-Command", extract], check=True, timeout=60)
    body = out.read_text(encoding="utf-8-sig")
    for name in FUNCTIONS:
        assert f"function {name}" in body
    return out


def _ps(script: str, cwd: Path, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a PowerShell script text and capture its output."""
    return subprocess.run(
        [WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
    )


def _git(cwd: Path, *args: str) -> str:
    """Run git in cwd and return stripped stdout."""
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def run_checkout(tmp_path: Path):
    """Create an origin repo with two commits on main and a clone detached at the first one."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@example.test")
    _git(origin, "config", "user.name", "t")
    (origin / "f.txt").write_text("1\n")
    _git(origin, "add", "f.txt")
    _git(origin, "commit", "-q", "-m", "one")
    first = _git(origin, "rev-parse", "HEAD")
    (origin / "f.txt").write_text("2\n")
    _git(origin, "commit", "-q", "-am", "two")
    second = _git(origin, "rev-parse", "HEAD")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    _git(clone, "checkout", "-q", "--detach", first)
    return clone, first, second


def _update(tmp_path: Path, clone: Path) -> tuple[str, str]:
    """Run Update-RunCheckout on clone; return (result, HEAD after)."""
    fns = _functions_script(tmp_path)
    proc = _ps(f". '{fns}'; $r = Update-RunCheckout -Dir '{clone}' -Label 'orama'; \"RESULT=$r\"", tmp_path)
    assert proc.returncode == 0, proc.stderr
    result = [line for line in proc.stdout.splitlines() if line.startswith("RESULT=")][-1]
    return result, _git(clone, "rev-parse", "HEAD")


@needs_windows
def test_update_moves_a_clean_detached_run_checkout_to_origin_main(tmp_path, run_checkout):
    """A clean detached checkout behind origin/main is moved to it."""
    clone, _first, second = run_checkout
    result, head = _update(tmp_path, clone)
    assert result == "RESULT=True"
    assert head == second


@needs_windows
def test_update_leaves_branch_dirty_and_diverged_checkouts_alone(tmp_path, run_checkout):
    """Branch checkouts, uncommitted changes and commits not on main are never moved."""
    clone, first, _second = run_checkout

    _git(clone, "checkout", "-q", "-b", "work")
    assert _update(tmp_path, clone) == ("RESULT=False", first)

    _git(clone, "checkout", "-q", "--detach", first)
    (clone / "f.txt").write_text("local edit\n")
    assert _update(tmp_path, clone) == ("RESULT=False", first)

    _git(clone, "checkout", "-q", "--", "f.txt")
    _git(clone, "config", "user.email", "t@example.test")
    _git(clone, "config", "user.name", "t")
    (clone / "g.txt").write_text("pr\n")
    _git(clone, "add", "g.txt")
    _git(clone, "commit", "-q", "-m", "pr commit")
    local = _git(clone, "rev-parse", "HEAD")
    assert _update(tmp_path, clone) == ("RESULT=False", local)


@needs_windows
def test_job_state_is_reported(tmp_path):
    """The job probe compiles and returns one of its documented states."""
    fns = _functions_script(tmp_path)
    proc = _ps(f". '{fns}'; Get-LauncherJobState", tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() in {"NotInJob", "InJobBreakawayOk", "InJobNoBreakaway", "Unknown"}


@needs_windows
def test_wmi_relaunch_leaves_the_job_relays_output_args_env_and_exit_code(tmp_path):
    """The child runs outside any job, sees the same arguments and environment, and its output and exit code come back."""
    fns = _functions_script(tmp_path)
    wrapper = tmp_path / "wrapper.ps1"
    log_dir = tmp_path / "logs"
    wrapper.write_text(
        f". '{fns}'\r\n"
        "if ($env:ORAMA_START_RELAUNCHED -eq '1') {\r\n"
        "    Write-Host \"child-ok state=$(Get-LauncherJobState) args=$($args -join '|') marker=$env:JE_TEST_MARKER\"\r\n"
        "    exit 7\r\n"
        "}\r\n"
        f"$r = Invoke-LauncherRelaunch -ScriptPath $PSCommandPath -Arguments @($args) -OutsideJob $true -LogDir '{log_dir}'\r\n"
        "exit $r\r\n",
        encoding="utf-8-sig",
    )
    env = {**os.environ, "JE_TEST_MARKER": "marker-42"}
    env.pop("ORAMA_START_RELAUNCHED", None)
    proc = subprocess.run(
        [WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper), "--no-open", "it's"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 7, proc.stdout + proc.stderr
    assert "child-ok state=NotInJob args=--no-open|it's marker=marker-42" in proc.stdout
    assert (log_dir / "launcher.rc").read_text().strip() == "7"
