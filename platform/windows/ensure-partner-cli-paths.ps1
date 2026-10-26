#Requires -Version 5.1

<#
.SYNOPSIS
    Idempotently prepare Windows partner CLIs for the current session.

.DESCRIPTION
    Windows partner lanes (Hermes, Codex, AGY, cursor-agent, ai-cli-mcp) must
    resolve from a normal start.ps1 session without manual PATH or package
    repair. -SessionOnly updates only the current process for launcher use;
    the default mode persists missing entries to User PATH. Safe to re-run.
    ai-cli-mcp package/runtime readiness delegates to
    the cross-platform scripts/ensure_ai_cli_mcp.py source of truth; provider
    login and terms acceptance remain explicit operator actions.

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
    [switch]$WhatIf,
    [switch]$SessionOnly
)

$ErrorActionPreference = 'Stop'

function Add-UserPathEntry {
    <#
    .SYNOPSIS
    Prepend an existing directory to the process PATH, and to the User PATH unless -SessionOnly is set.
    Honors -WhatIf (reports without changing anything).
    .PARAMETER Dir
    Directory to add; ignored when it does not exist.
    .OUTPUTS
    True when something was (or would be) added, false when nothing changed.
    #>
    param([string]$Dir)
    if (-not $Dir) { return $false }
    $resolved = $Dir
    try { $resolved = (Resolve-Path -LiteralPath $Dir -ErrorAction Stop).Path } catch { return $false }
    if (-not (Test-Path -LiteralPath $resolved)) { return $false }

    $processParts = @($env:Path -split ';' | Where-Object { $_ -and $_.Trim() })
    $inProcessPath = @($processParts | Where-Object { $_.TrimEnd('\') -ieq $resolved.TrimEnd('\') }).Count -gt 0
    if ($SessionOnly) {
        if ($inProcessPath) { return $false }
        if ($WhatIf) {
            Write-Host "  [whatif] would add to process PATH: $resolved"
            return $true
        }
        $env:Path = (@($resolved) + $processParts) -join ';'
        Write-Host "  [+] Process PATH: $resolved"
        return $true
    }

    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @($userPath -split ';' | Where-Object { $_ -and $_.Trim() })
    $inUserPath = @($parts | Where-Object { $_.TrimEnd('\') -ieq $resolved.TrimEnd('\') }).Count -gt 0
    if ($WhatIf) {
        if ($inUserPath -and $inProcessPath) { return $false }
        $scope = if ($inUserPath) { 'process' } else { 'User' }
        Write-Host "  [whatif] would add to $scope PATH: $resolved"
        return $true
    }
    if ($inProcessPath -and $inUserPath) { return $false }
    if (-not $inProcessPath) {
        $env:Path = (@($resolved) + $processParts) -join ';'
        Write-Host "  [+] Process PATH: $resolved"
    }
    if (-not $inUserPath) {
        # Prepend so partner CLIs shadow stale Machine/npm shims (e.g. native Codex before LM Studio bin).
        $newPath = ($resolved + ';' + ($parts -join ';')).TrimEnd(';')
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Write-Host "  [+] User PATH: $resolved"
    }
    return $true
}

$candidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin'),
    (Join-Path $env:LOCALAPPDATA 'cursor-agent'),
    (Join-Path $env:LOCALAPPDATA 'agy\bin'),
    (Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts'),
    (Join-Path $env:LOCALAPPDATA 'hermes\bin'),
    (Join-Path $env:USERPROFILE '.lmstudio\bin')
)

Write-Host $(if ($SessionOnly) { 'Ensuring partner CLI paths (process PATH only)...' } else { 'Ensuring partner CLI paths (User PATH)...' })
$added = 0
foreach ($c in $candidates) {
    if (Add-UserPathEntry -Dir $c) { $added++ }
}
if ($added -eq 0) {
    $scope = if ($SessionOnly) { 'process PATH' } else { 'User PATH' }
    Write-Host "  OK - all existing partner CLI paths already on $scope"
} elseif ($WhatIf) {
    $scope = if ($SessionOnly) { 'process PATH' } else { 'User PATH' }
    Write-Host "  [whatif] would add $added path(s) to the $scope; nothing was changed."
} else {
    if ($SessionOnly) {
        Write-Host "  OK - added $added path(s) to the current process."
    } else {
        Write-Host "  OK - added $added path(s). Open a new terminal for full effect."
    }
}

# ai-cli-mcp is a partner execution lane, so start.ps1 reaches the same shared
# core-readiness contract as ensure_requirements.ps1 without embedding npm/MCP
# mechanics in the launcher. WhatIf remains side-effect free.
if (-not $WhatIf) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $McpHelper = Join-Path $RepoRoot 'scripts\ensure_ai_cli_mcp.py'
    $SkipMcp = $env:ORAMA_SKIP_MCP_ENSURE -and $env:ORAMA_SKIP_MCP_ENSURE.Trim().ToLower() -in @('1', 'true', 'yes')
    if ($SkipMcp) {
        Write-Host "  verify ai-cli-mcp     SKIPPED (ORAMA_SKIP_MCP_ENSURE=$($env:ORAMA_SKIP_MCP_ENSURE))" -ForegroundColor Yellow
    } elseif (-not (Test-Path $McpHelper)) {
        throw "ai-cli-mcp readiness helper missing: $McpHelper"
    } else {
        $RepoPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
        if (-not (Test-Path $RepoPython)) {
            $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
            $RepoPython = if ($PythonCommand) { $PythonCommand.Source } else { $null }
        }
        if (-not $RepoPython) {
            throw 'Python is unavailable for ai-cli-mcp readiness helper'
        }
        & $RepoPython $McpHelper --quiet
        if ($LASTEXITCODE -ne 0) {
            throw 'ai-cli-mcp core readiness failed; see remediation above'
        }
        Write-Host '  verify ai-cli-mcp     READY'
    }
}

# Quick verify (current session after prepend above)
$checks = @(
    @{ Name = 'ai-cli';       Cmd = 'ai-cli' },
    @{ Name = 'hermes';       Cmd = 'hermes' },
    @{ Name = 'codex';        Cmd = 'codex' },
    @{ Name = 'agy';          Cmd = 'agy' },
    @{ Name = 'cursor-agent'; Cmd = 'cursor-agent' }
)
foreach ($ch in $checks) {
    $bin = Get-Command $ch.Cmd -ErrorAction SilentlyContinue
    if ($bin) {
        Write-Host ("  verify {0,-14} {1}" -f $ch.Name, $bin.Source)
    } else {
        Write-Host ("  verify {0,-14} NOT ON PATH" -f $ch.Name) -ForegroundColor Yellow
    }
}
