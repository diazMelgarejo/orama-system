#Requires -Version 5.1
<#
.SYNOPSIS
    install-hermes-harness.ps1 — Idempotent sync: Hermes profiles + thin wrappers from orama canonical.

.DESCRIPTION
    Idempotent sync (safe to re-run):
      - Profiles: install_hermes_profiles.py --sync (verify first; install only on drift)
      - Thin wrappers: verify first; install only when verify fails

    Does not install the Hermes application — only wires canonical bin/agents staging
    into an existing $HERMES_HOME brain.

.PARAMETER RepoRoot
    orama-system repository root. Defaults to parent of platform/windows.

.PARAMETER Python
    Python executable. Caller should pass .venv\Scripts\python.exe when available.

.PARAMETER DryRun
    Pass --dry-run to installers (preview only).

.PARAMETER SkipHermesSync
    Skip profile + thin-wrapper sync (maps to ORAMA_SKIP_HERMES_SYNC=1).

.PARAMETER TrustHermesSync
    Operator override after manual review (maps to ORAMA_TRUST_HERMES_SYNC=1).

.PARAMETER RunDoctor
    When hermes CLI is on PATH, run hermes doctor + config check after sync.

.EXAMPLE
    powershell -File .\platform\windows\install-hermes-harness.ps1

.EXAMPLE
    powershell -File .\platform\windows\install-hermes-harness.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [string]$Python = 'python',
    [switch]$DryRun,
    [switch]$SkipHermesSync,
    [switch]$TrustHermesSync,
    [switch]$RunDoctor
)

$ErrorActionPreference = 'Stop'

function _Step { param([string]$Msg) Write-Host "  [+] $Msg" -ForegroundColor Cyan }
function _OK   { param([string]$Msg) Write-Host "  ✓  $Msg" -ForegroundColor Green }
function _Warn { param([string]$Msg) Write-Host "  !  $Msg" -ForegroundColor Yellow }

function Get-HermesInstallState {
    $hermesCmd = Get-Command hermes -ErrorAction SilentlyContinue
    $hermesHome = $env:HERMES_HOME
    if (-not $hermesHome) {
        $hermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
    }
    $markers = @(
        (Join-Path $hermesHome 'config.yaml'),
        (Join-Path $hermesHome 'SOUL.md'),
        (Join-Path $hermesHome 'state.db'),
        (Join-Path $hermesHome 'profiles')
    )
    $brainPresent = ($markers | Where-Object { Test-Path $_ }).Count -gt 0
    return @{
        CliOnPath    = ($null -ne $hermesCmd)
        HermesHome   = $hermesHome
        BrainPresent = $brainPresent
        Present      = (($null -ne $hermesCmd) -or $brainPresent)
    }
}

function Invoke-PythonScript {
    param(
        [string[]]$ScriptArgs
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Python @ScriptArgs 2>&1 | ForEach-Object { Write-Host "    $_" }
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    return $exitCode
}

function Sync-Profiles {
    _Step 'Hermes profiles — idempotent sync (bin/agents → $HERMES_HOME/profiles)'
    $args = @($ProfileInstaller, '--sync')
    if ($DryRun) { $args += '--dry-run' }
    $code = Invoke-PythonScript -ScriptArgs $args
    if ($code -ne 0) {
        _Warn 'Profile sync failed — see output above'
        return $false
    }
    _OK 'Hermes profiles synced (or already matched staging)'
    return $true
}

function Sync-ThinWrappers {
    _Step 'Hermes thin wrappers — verify'
    $verifyArgs = @($ThinInstaller, '--verify')
    $code = Invoke-PythonScript -ScriptArgs $verifyArgs
    if ($code -eq 0) {
        _OK 'Thin wrappers already synced'
        return $true
    }
    _Step 'Hermes thin wrappers — install drift'
    $installArgs = @($ThinInstaller, '--install', '--verify')
    if ($DryRun) { $installArgs += '--dry-run' }
    $code = Invoke-PythonScript -ScriptArgs $installArgs
    if ($code -ne 0) {
        _Warn 'Thin wrapper sync failed — see output above'
        return $false
    }
    _OK 'Hermes thin wrappers synced'
    return $true
}

if (-not $RepoRoot) {
    $ScriptDir = Split-Path -Parent $PSCommandPath
    $RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
}

$env:ORAMA_SYSTEM_PATH = $RepoRoot

if ($SkipHermesSync) {
    $env:ORAMA_SKIP_HERMES_SYNC = '1'
}
if ($TrustHermesSync) {
    $env:ORAMA_TRUST_HERMES_SYNC = '1'
}

$VerifyTrust = Join-Path $RepoRoot 'scripts\review\verify_trusted_install.py'
if ($env:ORAMA_SKIP_HERMES_SYNC -eq '1') {
    _Warn 'Skipping Hermes harness sync (ORAMA_SKIP_HERMES_SYNC=1)'
    exit 0
}
if ((Test-Path $VerifyTrust) -and $env:ORAMA_TRUST_HERMES_SYNC -ne '1') {
    $trustCode = Invoke-PythonScript -ScriptArgs @($VerifyTrust, '--quiet')
    if ($trustCode -ne 0) {
        _Warn 'Hermes sync blocked — untrusted checkout (git pull --ff-only on main, review bin/agents, then -TrustHermesSync)'
        exit 1
    }
}

$HarnessScripts = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts'
$ProfileInstaller = Join-Path $HarnessScripts 'install_hermes_profiles.py'
$ThinInstaller    = Join-Path $HarnessScripts 'install_hermes_thin_skills.py'

if (-not (Test-Path $ProfileInstaller)) {
    _Warn "Profile installer not found: $ProfileInstaller"
    exit 1
}
if (-not (Test-Path $ThinInstaller)) {
    _Warn "Thin skills installer not found: $ThinInstaller"
    exit 1
}

$HermesState = Get-HermesInstallState
if ($HermesState.Present) {
    _OK "Hermes detected (CLI=$($HermesState.CliOnPath), brain=$($HermesState.BrainPresent)) — wire/sync only, no app install"
} else {
    _Warn 'Hermes not detected — still materializing profiles under %LOCALAPPDATA%\hermes; install Hermes app separately if needed'
}

$profileOk = Sync-Profiles
$thinOk    = Sync-ThinWrappers

if (-not $profileOk -or -not $thinOk) {
    exit 1
}

if ($RunDoctor -and $HermesState.CliOnPath) {
    _Step 'hermes doctor (post-sync smoke)'
    & hermes doctor 2>&1 | ForEach-Object { Write-Host "    $_" }
    & hermes config check 2>&1 | ForEach-Object { Write-Host "    $_" }
    if (Get-Command hermes -ErrorAction SilentlyContinue) {
        & hermes profile list 2>&1 | ForEach-Object { Write-Host "    $_" }
    }
    _OK 'Hermes doctor smoke complete'
}

if ($DryRun) {
    _OK 'Hermes harness dry-run complete'
} else {
    _OK "Hermes harness idempotent sync complete — profiles under $($HermesState.HermesHome)\profiles"
}

exit 0
