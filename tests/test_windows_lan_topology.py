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
    """Pinned call sites of the LAN peer probe/session helpers stay intact."""
    assert "} elseif (Invoke-LanPeerProbe) {" in TEXT
    assert "Invoke-LanPeerSession -LanArgs @('should-retry')" in TEXT
    assert "Invoke-LanPeerSession -LanArgs @('record-success')" in TEXT


def test_probe_output_captured_and_scalar_bool_returned() -> None:
    """Probe output is captured and the function returns a scalar bool."""
    body = _function_text("Invoke-LanPeerProbe")
    # The probe call is captured, never left as a bare statement.
    assert re.search(r"\$out\s*=\s*&\s*\$UsPython\s+\$probe\s+--json.*2>&1", body)
    returns = re.findall(r"^\s*return\s+(.+)$", body, re.MULTILINE)
    assert returns[-1].strip() == "($probeExit -eq 0)"
    assert "$probeExit = $LASTEXITCODE" in body
    session = _function_text("Invoke-LanPeerSession")
    assert re.search(r"return \[bool\]\(\$LASTEXITCODE -eq 0\)", session)


def test_discovery_runs_after_node_detection() -> None:
    """Endpoint discovery is invoked only after node detection exports."""
    detect = TEXT.index("# ── Dual Windows node detection")
    export_3080 = TEXT.index("$env:WIN_3080_IP = $Win3080Ip")
    call = TEXT.index("\nInvoke-DiscoverEndpoints\r\n") if "\nInvoke-DiscoverEndpoints\r\n" in TEXT else TEXT.index("\nInvoke-DiscoverEndpoints\n")
    assert detect < export_3080 < call
    assert TEXT.index("$env:WIN_5080_IP = $Win5080Ip") < call


def test_local_identification_uses_all_local_ipv4_and_default_route() -> None:
    """Local identity is derived from interface addresses and the default route."""
    assert "Get-NetIPAddress -AddressFamily IPv4" in TEXT
    assert "Get-NetRoute -DestinationPrefix '0.0.0.0/0'" in TEXT
    assert "System.Net.Sockets.Socket" not in TEXT
    assert "config is stale" in TEXT
    assert "$WinSiblingIp = 'unknown'" in TEXT


def test_lmstudio_probe_uses_loopback_object_and_5s_timeout() -> None:
    """LM Studio probe uses the loopback object and a 5 s timeout."""
    body = _function_text("Test-LmStudioUp")
    assert "http://localhost" not in body
    assert "-TimeoutSec 5" in body
    assert "$TopoLoopback" in body
    assert "[System.Net.IPAddress]::Loopback.IPAddressToString" in TEXT


def test_banner_version_not_hardcoded() -> None:
    """The banner reads the version dynamically instead of hardcoding it."""
    banner = TEXT[TEXT.index("# ── Banner") : TEXT.index("# ── Helper: start a service")]
    assert "v1.1.0.0" not in banner
    assert "Topo-GetVersion" in banner
    assert "(this machine)" in banner
    assert re.search(r"orama-system\s+v\d", banner) is None


def test_topology_region_has_no_ipv4_literals() -> None:
    """The topology helper region contains no IPv4 literals."""
    start = TEXT.index("# ── Topology helpers")
    end = TEXT.index("# ── Helper: start a service")
    region = TEXT[start:end]
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", region.replace("0.0.0.0/0", ""))


@pytest.mark.skipif(POWERSHELL is None, reason="powershell not available")
def test_failed_probe_returns_false_and_ok_probe_returns_true(tmp_path: Path) -> None:
    if not str(POWERSHELL).lower().endswith(".exe") and not shutil.which("cmd"):
        pytest.skip("needs Windows PowerShell")
    # Topo-WriteProbeOutput calls Topo-MaskSecrets, so the harness needs it too.
    funcs = "\n".join(
        _function_text(name)
        for name in ("Topo-MaskSecrets", "Topo-WriteProbeOutput", "Invoke-LanPeerProbe")
    )
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


def _mask(text: str) -> str:
    """Apply the launcher's masking rules to ``text`` using Python ``re``."""
    keys = r"[\w-]*(?:token|secret|authorization|api[_-]?key|password|passwd|credential)[\w-]*"
    steps = [
        (r'(?i)("' + keys + r'"\s*:\s*")(?:[^"\\]|\\.)*(")', r"\1***\2"),
        (r"(?i)(\b" + keys + r"\s*[=:]\s*)(?:Bearer\s+)?[^\s,;\"']+", r"\1***"),
        (r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+", r"\1***"),
    ]
    for pattern, repl in steps:
        text = re.sub(pattern.replace("(?i)", ""), repl, text, flags=re.IGNORECASE)
    return text


def test_mask_secrets_is_applied_before_console_and_log() -> None:
    """Masking runs once, before both the console and the log write."""
    body = _function_text("Topo-WriteProbeOutput")
    mask = body.index("Topo-MaskSecrets")
    assert mask < body.index("Write-Host") < body.index("Add-Content")
    assert "-replace '(?i)(\"(?:[a-z_]*token" not in body


def test_mask_secrets_source_declares_every_rule() -> None:
    """The PowerShell source carries the JSON, key=value and Bearer rules."""
    body = _function_text("Topo-MaskSecrets")
    assert "api[_-]?key" in body and "password" in body
    assert r'(?:[^"\\]|\\.)*' in body  # escaped quotes inside JSON strings
    assert "Bearer" in body


@pytest.mark.parametrize(
    "line",
    [
        '{"auth_token":"abc123","ok":true}',
        '{"x-api-key": "k-9"}',
        '{"access-token":"a\\"b\\"c"}',
        'password=hunter2 next',
        "Authorization: Bearer eyJhbGciOi.payload.sig",
    ],
)
def test_masking_rules_hide_secret_values(line: str) -> None:
    """Representative secret shapes never survive the masking rules."""
    out = _mask(line)
    for leaked in ("abc123", "k-9", "a\\\"b", "hunter2", "eyJhbGciOi"):
        assert leaked not in out
    assert "***" in out


def test_masking_keeps_non_secret_fields() -> None:
    """Non-secret fields pass through unchanged."""
    assert _mask('{"status":"ok","count":3}') == '{"status":"ok","count":3}'


def test_win_ip_is_not_proof_of_locality() -> None:
    """``WIN_IP`` must not be appended to the local-address list."""
    assert "$TopoLocalIps += $env:WIN_IP" not in TEXT
    assert "$TopoLocalIps = @(Topo-GetLocalIPv4)" in TEXT


def test_peer_endpoint_never_defaults_to_this_machine() -> None:
    """Unknown sibling leaves the peer endpoint empty; no localhost default."""
    assert "$WinPeerDefault = 'localhost:1234'" not in TEXT
    block = TEXT[TEXT.index("$WinPeerIsLoopback") :]
    block = block[: block.index("Invoke-DiscoverEndpoints")]
    assert "else { '' }" in block
    assert '"${WinSiblingIp}:1234"' in block
    assert "-or $WinPeerIsLoopback" in block


def test_orchestrator_skips_probe_without_peer() -> None:
    """The orchestrator has no hardcoded peer and skips the probe when unset."""
    sh = (ROOT / "bin" / "orama-system" / "orchestrator.sh").read_text(encoding="utf-8")
    assert "192.168." not in sh
    assert 'WIN_PEER="${WIN_PEER_ENDPOINT:-}"' in sh
    assert '[ -n "$WIN_PEER" ] || return 1' in sh
    assert 'if [ -z "$WIN_PEER" ]' in sh
