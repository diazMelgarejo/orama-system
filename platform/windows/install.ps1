#Requires -Version 5.1
<#
.SYNOPSIS
    install.ps1 — One-time Windows setup for orama-system  v1.1.1.0

.DESCRIPTION
    Idempotent setup script (safe to re-run).  Installs Python dependencies,
    verifies LM Studio port, creates .venv if missing.  openclaw.json is
    optional (skipped by default — Hermes is the sole Windows orchestrator).

    Run once after cloning (from **orama-system repo root**):
        powershell -ExecutionPolicy Bypass -File .\platform\windows\install.ps1

.NOTES
    Execution policy: run as:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    or use the one-liner above.
#>

[CmdletBinding()]
param(
    # Legacy OpenClaw config stub — not required on Hermes-only Windows hosts.
    [switch]$WriteOpenClawConfig
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path

function _Step { param([string]$Msg) Write-Host "  [+] $Msg" -ForegroundColor Cyan }
function _OK   { param([string]$Msg) Write-Host "  ✓  $Msg" -ForegroundColor Green }
function _Warn { param([string]$Msg) Write-Host "  !  $Msg" -ForegroundColor Yellow }
function _Err  { param([string]$Msg) Write-Host "  ✗  $Msg" -ForegroundColor Red; exit 1 }

Write-Host ''
Write-Host '═══════════════════════════════════════════════════════════' -ForegroundColor DarkCyan
Write-Host '  orama-system Windows installer  v1.1.1.0' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════════' -ForegroundColor DarkCyan
Write-Host ''

# ── Python version check ──────────────────────────────────────────────────────
_Step 'Checking Python...'
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match '(\d+)\.(\d+)') {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            _Err "Python 3.10+ required. Found: $pyVer"
        }
        _OK "Python $pyVer"
    }
} catch { _Err 'Python not found. Install from https://python.org/downloads/' }

# ── Virtual environment ───────────────────────────────────────────────────────
$VenvPath = Join-Path $RepoRoot '.venv'
_Step "Checking virtual environment at $VenvPath..."
if (-not (Test-Path (Join-Path $VenvPath 'Scripts\python.exe'))) {
    _Step 'Creating .venv...'
    & python -m venv $VenvPath
    _OK '.venv created'
} else {
    _OK '.venv already exists'
}

$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
$VenvPip    = Join-Path $VenvPath 'Scripts\pip.exe'

# ── Install dependencies ──────────────────────────────────────────────────────
_Step 'Installing core requirements...'
$rootReqs = Join-Path $RepoRoot 'requirements.txt'
if (Test-Path $rootReqs) {
    & $VenvPip install -r $rootReqs --quiet
    _OK 'Core requirements installed'
} else {
    _Warn "requirements.txt not found at $rootReqs — skipping core install"
}

_Step 'Installing Windows-specific requirements...'
$winReqs = Join-Path $ScriptDir 'requirements-windows.txt'
if (Test-Path $winReqs) {
    & $VenvPip install -r $winReqs --quiet
    _OK 'Windows requirements installed'
} else {
    _Warn "windows/requirements-windows.txt not found — skipping"
}

# ── LM Studio port check ──────────────────────────────────────────────────────
_Step 'Checking LM Studio (localhost:1234)...'
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $conn = $tcp.ConnectAsync('localhost', 1234)
    if ($conn.Wait(2000)) {
        $tcp.Close()
        _OK 'LM Studio is listening on :1234'
    } else {
        $tcp.Close()
        _Warn 'LM Studio not detected on :1234 — start LM Studio before running start.ps1'
    }
} catch {
    _Warn "LM Studio check failed: $_"
}

# ── openclaw.json defaults (optional — Hermes-only Windows skips by default) ───
# Windows deliberately has no OpenClaw/AlphaClaw install. Hermes is the sole
# local orchestrator. Pass -WriteOpenClawConfig only for legacy cross-repo stubs.
if ($WriteOpenClawConfig) {
    _Step 'Writing openclaw.json Windows defaults (legacy stub)...'
    $OcDir  = Join-Path $HOME '.openclaw'
    $OcJson = Join-Path $OcDir 'openclaw.json'
    $null   = New-Item -ItemType Directory -Force -Path $OcDir

    $template = @{
        models = @{
            providers = @{
                'lmstudio-win' = @{ baseUrl = 'http://localhost:1234' }
                'ollama-win'   = @{ baseUrl = 'http://localhost:11434' }
            }
        }
        distributed = $false
        platform    = 'windows'
        version     = '1.1.1.0'
    }

    if (Test-Path $OcJson) {
        try {
            $existing = Get-Content $OcJson -Raw | ConvertFrom-Json
            # Merge — don't overwrite user customizations
            if (-not $existing.models) {
                $existing | Add-Member -NotePropertyName 'models' -NotePropertyValue $template.models
                $existing | ConvertTo-Json -Depth 10 | Set-Content $OcJson -Encoding UTF8
                _OK "openclaw.json updated (merged defaults)"
            } else {
                _OK "openclaw.json already configured"
            }
        } catch {
            _Warn "Could not read existing openclaw.json: $_ — writing fresh copy"
            $template | ConvertTo-Json -Depth 10 | Set-Content $OcJson -Encoding UTF8
        }
    } else {
        $template | ConvertTo-Json -Depth 10 | Set-Content $OcJson -Encoding UTF8
        _OK "openclaw.json created at $OcJson"
    }
} else {
    _Step 'Skipping openclaw.json (Hermes-only Windows — use -WriteOpenClawConfig for legacy stub)'
    _OK 'No OpenClaw config written (not required)'
}

# ── Partner CLI PATH (Hermes, Codex, AGY, cursor-agent) ───────────────────────
_Step 'Ensuring partner CLI paths on User PATH...'
$PathScript = Join-Path $ScriptDir 'ensure-partner-cli-paths.ps1'
if (Test-Path $PathScript) {
    & $PathScript
    _OK 'Partner CLI PATH check complete'
} else {
    _Warn "ensure-partner-cli-paths.ps1 not found — skip PATH update"
}

# ── .paths.ps1 cache ──────────────────────────────────────────────────────────
_Step 'Generating .paths.ps1...'
& $VenvPython (Join-Path $ScriptDir 'start.ps1') --discover
_OK '.paths.ps1 written'

# ── gstack brain-sync Windows shim (fix #1731) ───────────────────────────────
# gstack-brain-sync is a bash shebang script. bun/Node.js spawns it via
# cmd.exe on Windows (NEEDS_SHELL_ON_WINDOWS=true), which can't exec shebangs.
# The .cmd wrapper calls bash.exe explicitly. Without it, /sync-gbrain's
# brain-sync stage always fails with "not recognized as an internal command".
_Step 'Installing gstack-brain-sync.cmd Windows shim...'
$GstackBin = Join-Path $HOME '.claude\skills\gstack\bin'
if (Test-Path $GstackBin) {
    $ShimSrc = Join-Path $ScriptDir 'gstack-brain-sync.cmd'
    $ShimDst = Join-Path $GstackBin 'gstack-brain-sync.cmd'
    if (Test-Path $ShimSrc) {
        Copy-Item -Path $ShimSrc -Destination $ShimDst -Force
        _OK "gstack-brain-sync.cmd installed to $ShimDst"
    } else {
        _Warn "gstack-brain-sync.cmd not found at $ShimSrc — skipping"
    }
} else {
    _Warn "gstack not installed at $GstackBin — run gstack setup first, then re-run this script"
}

# ── LM Studio operational invariant ───────────────────────────────────────────
_Warn 'IMPORTANT: LM Studio loads ONE model at a time on any machine (Mac/Linux/Windows).'
_Warn '           Loading a second model fails (e.g. gemma-4-e4b-it: Operation canceled).'
_Warn '           Multiple models at once require different machine IPs (Mac + Win on LAN).'
_Warn '           Windows GPU: never configure parallel inference on one host.'
_Warn ''
_Warn 'LM Studio server logs after failed canary probes:'
_Warn '  Windows:   %USERPROFILE%\.lmstudio\server-logs (e.g. 2026-06\2026-06-28.1.log)'
_Warn '  Mac/Linux: ~/.lmstudio/server-logs'
_Warn '  Quick tail: python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --tail-lmstudio-logs'

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '═══════════════════════════════════════════════════════════' -ForegroundColor DarkCyan
_OK 'Install complete!'
Write-Host ''
Write-Host '  Start services:  .\platform\windows\start.ps1'
Write-Host '  Stop services:   .\platform\windows\start.ps1 --stop'
Write-Host '  Check status:    .\platform\windows\start.ps1 --status'
Write-Host ''
