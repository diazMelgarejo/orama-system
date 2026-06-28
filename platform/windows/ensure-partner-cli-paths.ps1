#Requires -Version 5.1
<#
.SYNOPSIS
    Idempotently add Hermes partner CLI directories to the current user's PATH.

.DESCRIPTION
    Windows partner lanes (Hermes, Codex, AGY, cursor-agent) must resolve from any
    new PowerShell session without manual PATH edits. Safe to re-run.

    Canonical install locations (repo-relative docs in windows-onboarding-config.md):
      cursor-agent  %LOCALAPPDATA%\cursor-agent
      Codex         %USERPROFILE%\.lmstudio\bin  (npm shim) or WinGet OpenAI Codex
      AGY           %LOCALAPPDATA%\agy\bin
      Hermes        %LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts
      Hermes uv     %LOCALAPPDATA%\hermes\bin

.NOTES
    Does not modify Machine PATH. OpenClaw is optional on Windows - not added here.
#>

[CmdletBinding()]
param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

function Add-UserPathEntry {
    param([string]$Dir)
    if (-not $Dir) { return $false }
    $resolved = $Dir
    try { $resolved = (Resolve-Path -LiteralPath $Dir -ErrorAction Stop).Path } catch { return $false }
    if (-not (Test-Path -LiteralPath $resolved)) { return $false }

    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @($userPath -split ';' | Where-Object { $_ -and $_.Trim() })
    foreach ($p in $parts) {
        if ($p.TrimEnd('\') -ieq $resolved.TrimEnd('\')) { return $false }
    }
    if ($WhatIf) {
        Write-Host "  [whatif] would add to User PATH: $resolved"
        return $true
    }
    $newPath = ($parts + $resolved) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:Path = "$env:Path;$resolved"
    Write-Host "  [+] User PATH: $resolved"
    return $true
}

$candidates = @(
    (Join-Path $env:LOCALAPPDATA 'cursor-agent'),
    (Join-Path $env:LOCALAPPDATA 'agy\bin'),
    (Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts'),
    (Join-Path $env:LOCALAPPDATA 'hermes\bin'),
    (Join-Path $env:USERPROFILE '.lmstudio\bin'),
    (Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin')
)

Write-Host 'Ensuring partner CLI paths (User PATH)...'
$added = 0
foreach ($c in $candidates) {
    if (Add-UserPathEntry -Dir $c) { $added++ }
}
if ($added -eq 0) {
    Write-Host '  OK - all existing partner CLI paths already on User PATH'
} else {
    Write-Host "  OK - added $added path(s). Open a new terminal for full effect."
}

# Quick verify (current session after prepend above)
$checks = @(
    @{ Name = 'hermes';        Cmd = 'hermes' },
    @{ Name = 'codex';         Cmd = 'codex' },
    @{ Name = 'agy';           Cmd = 'agy' },
    @{ Name = 'cursor-agent';  Cmd = 'cursor-agent' }
)
foreach ($ch in $checks) {
    $bin = Get-Command $ch.Cmd -ErrorAction SilentlyContinue
    if ($bin) {
        Write-Host ("  verify {0,-14} {1}" -f $ch.Name, $bin.Source)
    } else {
        Write-Host ("  verify {0,-14} NOT ON PATH" -f $ch.Name) -ForegroundColor Yellow
    }
}
