"""F-C1: start.ps1 must heal declared-dependency drift in the PT venv."""
from __future__ import annotations

import re
from pathlib import Path

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


def test_pt_probe_gates_cryptography_on_portal_tls():
    body = _func(_text(), "Test-PtVenvHealthy")
    assert "PORTAL_TLS_ENABLED" in body
    assert "-RequireCryptography" in body
    assert "Test-VenvDeclaredDeps" in body


def test_heal_uses_new_probe_and_fails_loudly():
    body = _func(_text(), "Heal-PtVenv")
    assert body.count("Test-PtVenvHealthy $venvPy") == 3
    assert "Bootstrap-TestImports $venvPy" not in body
    assert "still unusable after install" in body and "exit 1" in body


def test_orama_probe_also_checks_declared_deps():
    text = _text()
    assert text.count("Test-VenvDeclaredDeps $VenvPythonMarker") == 2


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
