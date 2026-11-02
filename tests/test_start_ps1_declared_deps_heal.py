"""F-C1: start.ps1 must heal declared-dependency drift in the PT venv."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import venv
from pathlib import Path

import pytest

START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"
INSTALL_PS1 = START_PS1.with_name("install.ps1")
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")


def _text() -> str:
    """Read the launcher without its UTF-8 BOM."""
    return START_PS1.read_bytes().decode("utf-8-sig")


def _func(text: str, name: str) -> str:
    """Extract one top-level PowerShell function."""
    start = text.index(f"function {name} {{")
    nxt = re.search(r"^(function |# ── )", text[start + 10 :], re.M)
    return text[start : start + 10 + nxt.start()] if nxt else text[start:]


def test_deps_probe_runs_pip_check_and_cryptography() -> None:
    """Keep declared dependency and optional TLS checks wired together."""
    body = _func(_text(), "Test-VenvDeclaredDeps")
    assert "'pip', 'check'" in body
    assert "import cryptography" in body
    assert "-Project" in body and ".ToLower().Replace('_', '-')" in body
    assert "_Warn 'bootstrap' \"pip check (unrelated to" in body
    assert "$script:BootstrapOutput = $own" in body


def test_pt_probe_gates_cryptography_on_portal_tls() -> None:
    """Require cryptography only when Portal TLS is enabled."""
    body = _func(_text(), "Test-PtVenvHealthy")
    assert "PORTAL_TLS_ENABLED" in body
    assert "-RequireCryptography" in body
    assert "-Project 'perpetua-tools'" in body


def test_heal_uses_new_probe_and_fails_loudly() -> None:
    """Keep the health probe on every repair decision."""
    body = _func(_text(), "Heal-PtVenv")
    assert body.count("Test-PtVenvHealthy $venvPy") == 3
    assert "Bootstrap-TestImports $venvPy" not in body
    i = body.index("still unusable after install")
    assert "Bootstrap-ShowOutput" in body[i - 120 : i]
    assert "lacks perpetua-tools/requests/uvicorn" not in body


def test_orama_probe_also_checks_declared_deps() -> None:
    """Gate both initial startup and post-install validation."""
    text = _text()
    assert text.count("Test-VenvDeclaredDeps $VenvPythonMarker -Project 'orama-system'") == 2


def test_read_only_modes_skip_probe() -> None:
    """Preserve read-only launcher behavior."""
    text = _text()
    assert "$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)" in text
    assert "if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }" in text
    assert "if (-not $ReadOnlyMode) {\n    if (-not ((Bootstrap-TestImports $VenvPythonMarker" in text.replace("\r\n", "\n")
    # The probe functions are only reachable through Heal-PtVenv / the guarded block.
    callers = [m.start() for m in re.finditer(r"Test-PtVenvHealthy \$venvPy", text)]
    heal = text.index("function Heal-PtVenv {")
    assert all(c > heal for c in callers)


@pytest.mark.parametrize("path", [START_PS1, INSTALL_PS1])
def test_file_keeps_bom_and_crlf(path: Path) -> None:
    """Preserve Windows script encoding and line endings."""
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in raw.replace(b"\r\n", b"")


def _run_ps(body: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run an isolated script on either local PowerShell runtime."""
    if POWERSHELL is None:
        pytest.skip("requires PowerShell")
    script = tmp_path / "probe.ps1"
    script.write_text(body, encoding="utf-8-sig")
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True, text=True, check=False, timeout=120,
    )


def _run_probe(
    project: str, python: Path, tmp_path: Path, runner: str | None = None,
    require_crypto: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Exercise the production probe with real or fault-injected Python calls."""
    stub = 'function _Warn { param([string]$Stage, [string]$Msg) Write-Host ("WARN " + $Msg) }' + "\n"
    fn = stub + (runner or _func(_text(), "Bootstrap-RunPython")) + _func(_text(), "Test-VenvDeclaredDeps")
    exe = str(python).replace("'", "''")
    body = (
        "$script:BootstrapOutput=@()\n" + fn
        + "\n$r = Test-VenvDeclaredDeps '" + exe + "' -Project '" + project + "'"
        + (" -RequireCryptography" if require_crypto else "") + "\n"
        + 'Write-Output "RESULT=$r"\n'
        + '$script:BootstrapOutput | ForEach-Object { Write-Output "DETAIL=$_" }\n'
    )
    return _run_ps(body, tmp_path)


@pytest.fixture
def probe_python(tmp_path: Path) -> Path:
    """Create a disposable pip-enabled venv instead of using ambient TEMP state."""
    if POWERSHELL is None:
        pytest.skip("requires PowerShell")
    root = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(root)
    py = root / ("Scripts/python.exe" if (root / "Scripts").exists() else "bin/python")
    site = subprocess.run([str(py), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
                          capture_output=True, text=True, check=True).stdout.strip()
    for name, requires in [("zzfakebroken", "Requires-Dist: zz-not-installed-dep\n"), ("zz-other-project", "")]:
        di = Path(site) / f"{name.replace('-', '_')}-1.0.dist-info"
        di.mkdir()
        (di / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n{requires}", encoding="utf-8")
    return py


def test_unrelated_broken_package_warns_but_passes(tmp_path: Path, probe_python: Path) -> None:
    """Real pip conflicts warn for unrelated packages but block the owner."""
    r = _run_probe("zz-other-project", probe_python, tmp_path)
    assert "RESULT=True" in r.stdout, r.stdout + r.stderr
    assert "unrelated to zz-other-project" in r.stdout + r.stderr
    r2 = _run_probe("zzfakebroken", probe_python, tmp_path)
    assert "RESULT=False" in r2.stdout, r2.stdout + r2.stderr


def test_missing_project_metadata_fails(tmp_path: Path, probe_python: Path) -> None:
    """A project absent from the venv cannot pass a scoped check."""
    r = _run_probe("orama-system", probe_python, tmp_path)
    assert "RESULT=False" in r.stdout, r.stdout + r.stderr
    assert "orama-system" in r.stdout


@pytest.mark.parametrize("remove_pip", [False, True])
def test_real_completed_or_unavailable_pip(tmp_path: Path, probe_python: Path, remove_pip: bool) -> None:
    """Exercise clean pip completion and a real missing-pip module failure."""
    site = subprocess.run(
        [str(probe_python), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    shutil.rmtree(Path(site) / "zzfakebroken-1.0.dist-info")
    if remove_pip:
        shutil.rmtree(Path(site) / "pip")
    r = _run_probe("zz-other-project", probe_python, tmp_path)
    assert f"RESULT={not remove_pip}" in r.stdout, r.stdout + r.stderr
    if remove_pip:
        assert "No module named pip" in r.stdout


@pytest.mark.parametrize("stage", ["metadata", "check", "crypto"])
def test_execution_exception_fails_closed(tmp_path: Path, stage: str) -> None:
    """An invocation exception must produce false and preserve diagnostics."""
    runner = f"""function Bootstrap-RunPython {{
        param([string]$Python, [string[]]$PyArgs)
        if (('{stage}' -eq 'metadata' -and $PyArgs -contains $Project) -or
            ('{stage}' -eq 'check' -and $PyArgs -contains 'check') -or
            ('{stage}' -eq 'crypto' -and $PyArgs -contains 'import cryptography')) {{
            throw 'cannot execute Python'
        }}
        $script:BootstrapOutput = @('No broken requirements found.')
        return 0
    }}
    """
    r = _run_probe("orama-system", START_PS1, tmp_path, runner, require_crypto=True)
    assert "RESULT=False" in r.stdout, r.stdout + r.stderr
    assert "cannot execute Python" in r.stdout


@pytest.mark.parametrize("code,lines", [
    (1, []), (1, ["No module named pip"]),
    (1, ["Traceback (most recent call last):", "RuntimeError: broken metadata"]),
    (2, ["other 1.0 requires missing, which is not installed."]),
    (1, ["other 1.0 requires missing, which is not installed.", "ERROR: failed check"]),
    (0, []), (0, ["unexpected output"]),
])
def test_incomplete_check_fails_closed(tmp_path: Path, code: int, lines: list[str]) -> None:
    """Only completed pip diagnostics may take the unrelated-conflict exception."""
    payload = json.dumps(lines).replace("'", "''")
    runner = f"""function Bootstrap-RunPython {{
        param([string]$Python, [string[]]$PyArgs)
        if ($PyArgs -contains 'check') {{
            $script:BootstrapOutput = @('{payload}' | ConvertFrom-Json)
            return {code}
        }}
        return 0
    }}
    """
    r = _run_probe("orama-system", START_PS1, tmp_path, runner)
    assert "RESULT=False" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("code,line", [
    (0, "No broken requirements found."),
    (1, "other 1.0 requires missing, which is not installed."),
    (1, "other 1.0 has requirement dep<2, but you have dep 3."),
])
def test_completed_check_passes(tmp_path: Path, code: int, line: str) -> None:
    """Recognize healthy completion and both standard pip conflict forms."""
    runner = f"""function Bootstrap-RunPython {{
        param([string]$Python, [string[]]$PyArgs)
        $script:BootstrapOutput = @('{line}')
        if ($PyArgs -contains 'check') {{ return {code} }}
        return 0
    }}
    """
    r = _run_probe("orama-system", START_PS1, tmp_path, runner)
    assert "RESULT=True" in r.stdout, r.stdout + r.stderr


def test_crypto_failure_still_blocks(tmp_path: Path, probe_python: Path) -> None:
    """A completed unrelated conflict does not bypass the TLS import gate."""
    r = _run_probe("zz-other-project", probe_python, tmp_path, require_crypto=True)
    assert "RESULT=False" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("metadata,exit_code", [(True, 0), (True, 37), (False, 0), (True, None)])
def test_installer_requires_editable_project(tmp_path: Path, metadata: bool, exit_code: int | None) -> None:
    """Run the installer project step, checking arguments and fatal failures."""
    text = INSTALL_PS1.read_text(encoding="utf-8-sig")
    start = text.index("_Step 'Installing orama-system distribution...'")
    end = text.index("_Step 'Installing Windows-specific requirements...'")
    if metadata:
        (tmp_path / "pyproject.toml").touch()
    root = str(tmp_path).replace("'", "''")
    r = _run_ps(f"""
        $ErrorActionPreference = 'Stop'
        $RepoRoot = '{root}'
        $VenvPython = '{"MissingPythonExecutable" if exit_code is None else "FakePython"}'
        $LASTEXITCODE = 0
        function _Step {{ param([string]$Msg) }}
        function _OK {{ param([string]$Msg) Write-Output 'INSTALLED' }}
        function _Err {{ param([string]$Msg) throw $Msg }}
        function FakePython {{
            Write-Host ('ARGS=' + ($args -join '|'))
            $global:LASTEXITCODE = {exit_code}
        }}
        {text[start:end]}
    """, tmp_path)
    if metadata and exit_code == 0:
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"ARGS=-m|pip|install|-e|{tmp_path}" in r.stdout
        assert "INSTALLED" in r.stdout
    else:
        assert r.returncode != 0, r.stdout + r.stderr
        assert "INSTALLED" not in r.stdout
        assert ("pyproject.toml" if not metadata else "editable install failed") in r.stderr
        if exit_code == 37:
            assert "37" in r.stderr
