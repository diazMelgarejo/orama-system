"""F-C1: start.ps1 must heal declared-dependency drift in the PT venv."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"


def _text() -> str:
    """Return the text of start.ps1 stripped of UTF-8 BOM."""
    return START_PS1.read_bytes().decode("utf-8-sig")


def _func(text: str, name: str) -> str:
    """Extract a function definition by name from PowerShell script text."""
    start = text.index(f"function {name} {{")
    nxt = re.search(r"^(function |# ── )", text[start + 10 :], re.M)
    return text[start : start + 10 + nxt.start()] if nxt else text[start:]


def test_deps_probe_runs_pip_check_and_cryptography() -> None:
    """Check that Test-VenvDeclaredDeps runs pip check and cryptography."""
    body = _func(_text(), "Test-VenvDeclaredDeps")
    assert "'pip', 'check'" in body
    assert "import cryptography" in body
    assert "-Project" in body and ".ToLower().Replace('_', '-')" in body
    assert "_Warn 'bootstrap' \"pip check (unrelated to" in body
    assert "$script:BootstrapOutput = $own" in body
    assert "No module named pip" in body


def test_pt_probe_gates_cryptography_on_portal_tls() -> None:
    """Check that Test-PtVenvHealthy gates cryptography on PORTAL_TLS_ENABLED."""
    body = _func(_text(), "Test-PtVenvHealthy")
    assert "PORTAL_TLS_ENABLED" in body
    assert "-RequireCryptography" in body
    assert "-Project 'perpetua-tools'" in body


def test_heal_uses_new_probe_and_fails_loudly() -> None:
    """Check that Heal-PtVenv calls Test-PtVenvHealthy and shows output on failure."""
    body = _func(_text(), "Heal-PtVenv")
    assert body.count("Test-PtVenvHealthy $venvPy") == 3
    assert "Bootstrap-TestImports $venvPy" not in body
    i = body.index("still unusable after install")
    assert "Bootstrap-ShowOutput" in body[i - 120 : i]
    assert "lacks perpetua-tools/requests/uvicorn" not in body


def test_orama_probe_also_checks_declared_deps() -> None:
    """Check that orama-system bootstrap also validates declared dependencies."""
    text = _text()
    assert text.count("Test-VenvDeclaredDeps $VenvPythonMarker -Project 'orama-system'") == 2


def test_read_only_modes_skip_probe() -> None:
    """Check that read-only launcher modes skip the declared-dependency probe."""
    text = _text()
    assert "$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)" in text
    assert "if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }" in text
    assert "if (-not $ReadOnlyMode) {\n    if (-not ((Bootstrap-TestImports $VenvPythonMarker" in text.replace("\r\n", "\n")
    # The probe functions are only reachable through Heal-PtVenv / the guarded block.
    callers = [m.start() for m in re.finditer(r"Test-PtVenvHealthy \$venvPy", text)]
    heal = text.index("function Heal-PtVenv {")
    assert all(c > heal for c in callers)


def test_file_keeps_bom_and_crlf() -> None:
    """Ensure start.ps1 maintains UTF-8 BOM and CRLF line endings."""
    raw = START_PS1.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in raw.replace(b"\r\n", b"")


def _venv_python(venv_dir: Path) -> Path:
    """Return the python executable in the given venv."""
    return venv_dir / "Scripts" / "python.exe" if os.name == "nt" else venv_dir / "bin" / "python"


def _venv_site_packages(venv_dir: Path) -> Path:
    """Return the site-packages directory of the given venv."""
    py = _venv_python(venv_dir)
    r = subprocess.run(
        [str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(r.stdout.strip())


def _run_probe(python_exe: Path, project: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Execute Test-VenvDeclaredDeps in an isolated PowerShell child process."""
    text = _text()
    stub = 'function _Warn { param([string]$Stage, [string]$Msg) Write-Host ("WARN " + $Msg) }\n'
    fn = stub + _func(text, "Bootstrap-RunPython") + _func(text, "Test-VenvDeclaredDeps")
    script = tmp_path / "probe.ps1"
    body = (
        "$script:BootstrapOutput=@()\n"
        + fn
        + "\n$r = Test-VenvDeclaredDeps '"
        + str(python_exe).replace("'", "''")
        + "' -Project '"
        + project
        + "'\n"
        + 'Write-Output "RESULT=$r"\n'
    )
    script.write_text(body, encoding="utf-8-sig")
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.fixture(scope="module")
def isolated_probe_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create an isolated venv offline for Test-VenvDeclaredDeps behavior tests."""
    venv_dir = tmp_path_factory.mktemp("probe-venv")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    return venv_dir


needs_powershell = pytest.mark.skipif(
    shutil.which("powershell.exe") is None,
    reason="needs Windows PowerShell",
)


@needs_powershell
def test_unrelated_broken_package_warns_but_passes(
    isolated_probe_venv: Path, tmp_path: Path
) -> None:
    """Verify unrelated broken package passes with warning, while own broken package fails."""
    py = _venv_python(isolated_probe_venv)
    site = _venv_site_packages(isolated_probe_venv)
    di = site / "zzfakebroken-1.0.dist-info"
    di.mkdir(exist_ok=True)
    (di / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: zzfakebroken\nVersion: 1.0\nRequires-Dist: nonexistent-pkg-zzz\n",
        encoding="utf-8",
    )
    try:
        r = _run_probe(py, "zz-other-project", tmp_path)
        assert "RESULT=True" in r.stdout, r.stdout + r.stderr
        assert "unrelated to zz-other-project" in r.stdout + r.stderr
        r2 = _run_probe(py, "zzfakebroken", tmp_path)
        assert "RESULT=False" in r2.stdout, r2.stdout + r2.stderr
    finally:
        shutil.rmtree(di, ignore_errors=True)


@needs_powershell
def test_probe_fails_when_pip_unusable(tmp_path: Path) -> None:
    """Verify probe returns False when pip is missing or exits with code 2."""
    nopip_dir = tmp_path / "nopip-venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(nopip_dir)], check=True)
    nopip_py = _venv_python(nopip_dir)
    r_nopip = _run_probe(nopip_py, "any-project", tmp_path)
    assert "RESULT=False" in r_nopip.stdout, r_nopip.stdout + r_nopip.stderr

    stub_cmd = tmp_path / "stub_exit2.cmd"
    stub_cmd.write_text("@echo off\r\nexit /b 2\r\n", encoding="ascii")
    r_exit2 = _run_probe(stub_cmd, "any-project", tmp_path)
    assert "RESULT=False" in r_exit2.stdout, r_exit2.stdout + r_exit2.stderr


@needs_powershell
def test_probe_fails_on_unparseable_exit_1(tmp_path: Path) -> None:
    """Verify probe returns False on exit code 1 with unparseable or empty output."""
    stub_unparseable = tmp_path / "stub_unparseable.cmd"
    stub_unparseable.write_text(
        "@echo off\r\necho Fatal Python error: memory corruption detected\r\nexit /b 1\r\n",
        encoding="ascii",
    )
    r_unparseable = _run_probe(stub_unparseable, "any-project", tmp_path)
    assert "RESULT=False" in r_unparseable.stdout, r_unparseable.stdout + r_unparseable.stderr

    stub_empty = tmp_path / "stub_empty.cmd"
    stub_empty.write_text("@echo off\r\nexit /b 1\r\n", encoding="ascii")
    r_empty = _run_probe(stub_empty, "any-project", tmp_path)
    assert "RESULT=False" in r_empty.stdout, r_empty.stdout + r_empty.stderr
