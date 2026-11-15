"""Execute the production LAN-peer TLS choice block without starting services."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")


@pytest.mark.skipif(POWERSHELL is None, reason="requires PowerShell")
@pytest.mark.parametrize(
    "lan_peer,initial_tls,expected_tls,expected_portal_bind",
    [
        (True, None, "1", None),
        (True, "", "1", None),
        (True, "0", "0", "1"),
        (True, "false", "false", "1"),
        (True, "no", "no", "1"),
        (True, "off", "off", "1"),
        (True, " FALSE ", " FALSE ", "1"),
        (True, "true", "1", None),
        (True, "1", "1", None),
        (False, None, None, None),
        (False, "off", "off", None),
    ],
)
def test_lan_peer_tls_choice_executes(
    tmp_path, lan_peer, initial_tls, expected_tls, expected_portal_bind
):
    """Honor explicit TLS opt-out; enable the default and set only intended binds."""
    source = str(START_PS1).replace("'", "''")
    initialize_tls = (
        "Remove-Item Env:PORTAL_TLS_ENABLED -ErrorAction SilentlyContinue"
        if initial_tls is None
        else "$env:PORTAL_TLS_ENABLED = '" + initial_tls.replace("'", "''") + "'"
    )
    script = tmp_path / "lan-peer-tls.ps1"
    script.write_text(
        f"""$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    '{source}', [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) {{ throw 'launcher parse failed' }}
$blocks = @($ast.FindAll({{
    param($node)
    $node -is [System.Management.Automation.Language.IfStatementAst] -and
        $node.Clauses[0].Item1.Extent.Text.Trim() -eq '$LanPeer'
}}, $true))
if ($blocks.Count -eq 0) {{ throw 'LAN-peer choice block not found' }}
foreach ($name in @('PORTAL_BIND_LAN', 'ORAMA_BIND_LAN', 'PT_BIND_LAN')) {{
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}}
{initialize_tls}
$LanPeer = ${str(lan_peer).lower()}
function _Info {{ param([string]$Stage, [string]$Message) }}
& ([scriptblock]::Create($blocks[0].Extent.Text))
@{{
    tls = [Environment]::GetEnvironmentVariable('PORTAL_TLS_ENABLED', 'Process')
    portal_bind = [Environment]::GetEnvironmentVariable('PORTAL_BIND_LAN', 'Process')
    orama_bind = [Environment]::GetEnvironmentVariable('ORAMA_BIND_LAN', 'Process')
    pt_bind = [Environment]::GetEnvironmentVariable('PT_BIND_LAN', 'Process')
}} | ConvertTo-Json -Compress
""",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(script)],
        capture_output=True, text=True, check=False, timeout=30, cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout.strip().splitlines()[-1])
    assert actual["tls"] == expected_tls
    assert actual["portal_bind"] == expected_portal_bind
    assert actual["orama_bind"] == ("1" if lan_peer else None)
    assert actual["pt_bind"] == ("1" if lan_peer else None)
