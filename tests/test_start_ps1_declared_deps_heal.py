"""F-C1: start.ps1 must heal declared-dependency drift in the PT venv."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"


def _text() -> str:
    return START_PS1.read_bytes().decode("utf-8-sig")


def _func(text: str, name: str) -> str:
    start = text.index(f"function {name} {{")
    nxt = re.search(r"^(function |# ── )", text[start + 10 :], re.M)
    return text[start : start + 10 + nxt.start()] if nxt else text[start:]


def test_deps_probe_runs_pip_check_and_cryptography():
    body = _func(_text(), "Test-VenvDeclaredDeps")
    assert "'pip', 'check'" in body
    assert "import cryptography" in body
    assert "-Project" in body and ".ToLower().Replace('_', '-')" in body
    assert "_Warn 'bootstrap' \"pip check (unrelated to" in body
    assert "$script:BootstrapOutput = $own" in body


def test_pt_probe_gates_cryptography_on_portal_tls():
    body = _func(_text(), "Test-PtVenvHealthy")
    assert "PORTAL_TLS_ENABLED" in body
    assert "-RequireCryptography" in body
    assert "-Project 'perpetua-tools'" in body


def test_heal_uses_new_probe_and_fails_loudly():
    body = _func(_text(), "Heal-PtVenv")
    assert body.count("Test-PtVenvHealthy $venvPy") == 3
    assert "Bootstrap-TestImports $venvPy" not in body
    i = body.index("still unusable after install")
    assert "Bootstrap-ShowOutput" in body[i - 120 : i]
    assert "lacks perpetua-tools/requests/uvicorn" not in body


def test_orama_probe_also_checks_declared_deps():
    text = _text()
    assert text.count("Test-VenvDeclaredDeps $VenvPythonMarker -Project 'orama-system'") == 2


def test_read_only_modes_skip_probe():
    text = _text()
    assert "$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)" in text
    assert "if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }" in text
    assert "if (-not $ReadOnlyMode) {\n    if (-not ((Bootstrap-TestImports $VenvPythonMarker" in text.replace("\r\n", "\n")
    # The probe functions are only reachable through Heal-PtVenv / the guarded block.
    callers = [m.start() for m in re.finditer(r"Test-PtVenvHealthy \$venvPy", text)]
    heal = text.index("function Heal-PtVenv {")
    assert all(c > heal for c in callers)


def test_file_keeps_bom_and_crlf():
    raw = START_PS1.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in raw.replace(b"\r\n", b"")


PROBE_VENV = Path(os.environ.get("TEMP", "/tmp")) / "x1or-probe-venv"


def _run_probe(project: str, tmp_path: Path) -> subprocess.CompletedProcess:
    text = _text()
    stub = 'function _Warn { param([string]$Stage, [string]$Msg) Write-Host ("WARN " + $Msg) }' + "\n"
    fn = stub + _func(text, "Bootstrap-RunPython") + _func(text, "Test-VenvDeclaredDeps")
    script = tmp_path / "probe.ps1"
    exe = str(PROBE_VENV / "Scripts" / "python.exe")
    body = (
        "$script:BootstrapOutput=@()\n" + fn
        + "\n$r = Test-VenvDeclaredDeps '" + exe + "' -Project '" + project + "'\n"
        + 'Write-Output "RESULT=$r"\n'
    )
    script.write_text(body, encoding="utf-8-sig")
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True, text=True, check=False, timeout=120,
    )


@pytest.mark.skipif(
    shutil.which("powershell.exe") is None or not (PROBE_VENV / "Scripts" / "python.exe").exists(),
    reason="needs Windows PowerShell and the throwaway probe venv",
)
def test_unrelated_broken_package_warns_but_passes(tmp_path):
    py = PROBE_VENV / "Scripts" / "python.exe"
    site = subprocess.run([str(py), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
                          capture_output=True, text=True, check=True).stdout.strip()
    di = Path(site) / "zzfakebroken-1.0.dist-info"
    di.mkdir(exist_ok=True)
    (di / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: zzfakebroken\nVersion: 1.0\nRequires-Dist: zz-not-installed-dep\n")
    try:
        r = _run_probe("zz-other-project", tmp_path)
        assert "RESULT=True" in r.stdout, r.stdout + r.stderr
        assert "unrelated to zz-other-project" in r.stdout + r.stderr
        r2 = _run_probe("zzfakebroken", tmp_path)
        assert "RESULT=False" in r2.stdout, r2.stdout + r2.stderr
    finally:
        shutil.rmtree(di, ignore_errors=True)
