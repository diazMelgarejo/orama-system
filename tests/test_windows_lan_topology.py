"""Static and light behaviour checks for the Windows launcher LAN topology logic.

Covers: honest peer-probe result (F25), node detection ordering and local-node
identification (F3/F15/F6/F9), loopback/5 s LM Studio probe (F14) and the
non-hardcoded banner version.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"
TEXT = START_PS1.read_text(encoding="utf-8-sig")
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def _function_text(name: str) -> str:
    """Return the full source of ``function <name>`` (brace matched)."""
    match = re.search(rf"^function {re.escape(name)}\b[^\n]*\{{", TEXT, re.MULTILINE)
    assert match, f"function {name} not found"
    depth = 0
    for index in range(match.end() - 1, len(TEXT)):
        char = TEXT[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return TEXT[match.start() : index + 1]
    raise AssertionError(f"unterminated function {name}")


def test_pinned_probe_call_site_unchanged() -> None:
    assert "} elseif (Invoke-LanPeerProbe) {" in TEXT
    assert "Invoke-LanPeerSession -LanArgs @('should-retry')" in TEXT
    assert "Invoke-LanPeerSession -LanArgs @('record-success')" in TEXT


def test_probe_output_captured_and_scalar_bool_returned() -> None:
    body = _function_text("Invoke-LanPeerProbe")
    # The probe call is captured, never left as a bare statement.
    assert re.search(r"\$out\s*=\s*&\s*\$UsPython\s+\$probe\s+--json.*2>&1", body)
    returns = re.findall(r"^\s*return\s+(.+)$", body, re.MULTILINE)
    assert returns[-1].strip() == "($probeExit -eq 0)"
    assert "$probeExit = $LASTEXITCODE" in body
    session = _function_text("Invoke-LanPeerSession")
    assert re.search(r"return \[bool\]\(\$LASTEXITCODE -eq 0\)", session)


def test_discovery_runs_after_node_detection() -> None:
    detect = TEXT.index("# ── Dual Windows node detection")
    export_3080 = TEXT.index("$env:WIN_3080_IP = $Win3080Ip")
    call = TEXT.index("\nInvoke-DiscoverEndpoints\r\n") if "\nInvoke-DiscoverEndpoints\r\n" in TEXT else TEXT.index("\nInvoke-DiscoverEndpoints\n")
    assert detect < export_3080 < call
    assert TEXT.index("$env:WIN_5080_IP = $Win5080Ip") < call


def test_local_identification_uses_all_local_ipv4_and_default_route() -> None:
    assert "Get-NetIPAddress -AddressFamily IPv4" in TEXT
    assert "Get-NetRoute -DestinationPrefix '0.0.0.0/0'" in TEXT
    assert "System.Net.Sockets.Socket" not in TEXT
    assert "config is stale" in TEXT
    assert "$WinSiblingIp = 'unknown'" in TEXT


def test_lmstudio_probe_uses_loopback_object_and_5s_timeout() -> None:
    body = _function_text("Test-LmStudioUp")
    assert "http://localhost" not in body
    assert "-TimeoutSec 5" in body
    assert "$TopoLoopback" in body
    assert "[System.Net.IPAddress]::Loopback.IPAddressToString" in TEXT


def test_banner_version_not_hardcoded() -> None:
    banner = TEXT[TEXT.index("# ── Banner") : TEXT.index("# ── Helper: start a service")]
    assert "v1.1.0.0" not in banner
    assert "Topo-GetVersion" in banner
    assert "(this machine)" in banner
    assert re.search(r"orama-system\s+v\d", banner) is None


def test_topology_region_has_no_ipv4_literals() -> None:
    start = TEXT.index("# ── Topology helpers")
    end = TEXT.index("# ── Helper: start a service")
    region = TEXT[start:end]
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", region.replace("0.0.0.0/0", ""))


@pytest.mark.skipif(POWERSHELL is None, reason="powershell not available")
def test_failed_probe_returns_false_and_ok_probe_returns_true(tmp_path: Path) -> None:
    if not str(POWERSHELL).lower().endswith(".exe") and not shutil.which("cmd"):
        pytest.skip("needs Windows PowerShell")
    funcs = _function_text("Topo-WriteProbeOutput") + "\n" + _function_text("Invoke-LanPeerProbe")
    fake_fail = tmp_path / "fail.cmd"
    fake_fail.write_text('@echo {"ok": false, "token": "abc"}\r\n@exit /b 1\r\n')
    fake_ok = tmp_path / "ok.cmd"
    fake_ok.write_text('@echo {"ok": true}\r\n@exit /b 0\r\n')
    script = tmp_path / "t.ps1"
    script.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "Set-StrictMode -Version Latest",
                f"$RepoRoot = '{ROOT}'",
                f"$LogDir = '{tmp_path / 'logs'}'",
                "$PtDir = $null",
                "function Sync-ControlPlaneToken {}",
                "function _Info { }",
                "function _Warn { }",
                funcs,
                f"$UsPython = '{fake_fail}'",
                "$r1 = Invoke-LanPeerProbe",
                "Write-Output ('FAIL type=' + $r1.GetType().Name + ' value=' + $r1)",
                f"$UsPython = '{fake_ok}'",
                "$r2 = Invoke-LanPeerProbe",
                "Write-Output ('OK type=' + $r2.GetType().Name + ' value=' + $r2)",
            ]
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = proc.stdout
    assert "FAIL type=Boolean value=False" in out, out + proc.stderr
    assert "OK type=Boolean value=True" in out, out + proc.stderr
    assert "abc" not in out  # token-like values are masked
