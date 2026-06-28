#Requires -Version 5.1
<#
.SYNOPSIS
    Print ORAMA_CONTROL_PLANE_TOKEN for Mac .env.local handoff (LAN peer bidirectional).

.DESCRIPTION
    Reads PT/.state/control_plane_token (or generates via start.ps1 --lan-peer first).
    Never commit the token — paste into Mac orama-system .env.local only.
#>
param(
    [string]$PtDir = $env:PERPETUA_TOOLS_PATH
)

if (-not $PtDir) {
    $PtDir = $env:PERPETUA_TOOLS_ROOT
}
if (-not $PtDir) {
    Write-Error 'Set PERPETUA_TOOLS_PATH to your Perpetua-Tools clone.'
    exit 1
}

$tokenPath = Join-Path $PtDir '.state\control_plane_token'
if (-not (Test-Path $tokenPath)) {
    Write-Host 'No token yet. Run from orama-system:'
    Write-Host '  .\platform\windows\start.ps1 --lan-peer --no-open'
    exit 1
}

$token = (Get-Content $tokenPath -Raw).Trim()
Write-Host ''
Write-Host '=== Mac .env.local (orama-system) — add or replace this line ==='
Write-Host "ORAMA_CONTROL_PLANE_TOKEN=$token"
Write-Host ''
Write-Host 'Then on Mac:'
Write-Host '  ./start.sh --stop && ./start.sh --lan-peer --no-open'
Write-Host '  python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json'
Write-Host ''
