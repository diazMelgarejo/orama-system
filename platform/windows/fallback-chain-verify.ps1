#Requires -Version 5.1
<#
.SYNOPSIS
    fallback-chain-verify.ps1 — Verify all model fallback tiers are healthy (Windows)

.DESCRIPTION
    PowerShell equivalent of bin/orama-system/scripts/fallback-chain-verify.sh
    Checks all 5 model tiers and reports status. Used by start.ps1 on gateway restart
    to ensure automatic failover is armed.

.PARAMETER StatusOnly
    Report tier status and exit (no setup/config checks)

.PARAMETER SetupOpenRouter
    Automatically run setup-openrouter.sh if Tier 5 not configured

.EXAMPLE
    .\fallback-chain-verify.ps1 -StatusOnly
    .\fallback-chain-verify.ps1
#>

param(
    [switch]$StatusOnly = $false,
    [switch]$SetupOpenRouter = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Colors ────────────────────────────────────────────────────────────────────
$Green  = "`e[32m"
$Red    = "`e[31m"
$Yellow = "`e[33m"
$Reset  = "`e[0m"

# ── Directories ───────────────────────────────────────────────────────────────
$SecretsDir = Join-Path $env:USERPROFILE '.openclaw\secrets'
$EnvFile    = Join-Path $env:USERPROFILE '.openclaw\.env.openrouter'

function Log {
    param([string]$Message)
    Write-Host "[fallback-verify] $Message"
}

function Test-TierAvailable {
    param(
        [int]$Tier,
        [string]$Name,
        [scriptblock]$CheckCmd
    )

    # $CheckCmd blocks used to end with `exit 0`, and this function checked
    # $LASTEXITCODE afterward. Two problems: (1) cmdlets never set
    # $LASTEXITCODE — only native executables do — so the check was
    # comparing against a stale/unrelated value; (2) `exit` inside a
    # scriptblock invoked via `& $CheckCmd` from a non-top-level function
    # terminates the ENTIRE PowerShell process immediately, not just this
    # check. Confirmed live: whenever a check actually succeeded, the whole
    # script died right there — silently, with no [AVAILABLE] line, no
    # remaining tiers checked, no summary printed. `-ErrorAction Stop` is
    # set globally (Set-StrictMode/$ErrorActionPreference above), so
    # "no exception thrown" already IS success — that's all this needs.
    try {
        $null = & $CheckCmd
        Write-Host "$Tier. $($Name.PadRight(38)) ${Green}[AVAILABLE]${Reset}"
        return $true
    } catch {
        Write-Host "$Tier. $($Name.PadRight(38)) ${Red}[OFFLINE]${Reset}"
        return $false
    }
}

function Test-TierConfigured {
    param(
        [int]$Tier,
        [string]$Name,
        [string]$FilePath
    )

    if (Test-Path $FilePath) {
        Write-Host "$Tier. $($Name.PadRight(38)) ${Green}[CONFIGURED]${Reset}"
        return $true
    } else {
        Write-Host "$Tier. $($Name.PadRight(38)) ${Yellow}[NOT CONFIGURED]${Reset}"
        return $false
    }
}

# ── Main ──────────────────────────────────────────────────────────────────────
Log "Model Fallback Chain Verification"
Log ""

# Tier 1: ClinePass (local Claude)
$Tier1 = Test-TierAvailable -Tier 1 -Name "ClinePass (local Claude)" -CheckCmd {
    $null = Get-Command cline -ErrorAction Stop
}

# Tier 2: LM Studio (Windows GPU) — on Windows, typically at localhost:1234
$Tier2 = Test-TierAvailable -Tier 2 -Name "LM Studio (Windows GPU)" -CheckCmd {
    # -or is a boolean operator in PowerShell, not null-coalescing: it always
    # returns $true/$false, never either operand. $env:X -or 'default' used
    # to resolve to the literal string "True" whenever $env:X was unset,
    # producing an invalid URL ("True/v1/models") and reporting LM Studio
    # OFFLINE even when it was actually up and serving models.
    $LmStudioEndpoint = if ($env:LM_STUDIO_WIN_ENDPOINTS) { $env:LM_STUDIO_WIN_ENDPOINTS } else { 'http://localhost:1234' }
    # -UseBasicParsing: without it, Invoke-WebRequest routes through the IE
    # COM parsing engine, which throws "Windows PowerShell is in
    # NonInteractive mode. Read and Prompt functionality is not available."
    # under any non-interactive invocation (Task Scheduler, CI, automation
    # tooling) — reporting this tier OFFLINE even when LM Studio is actually
    # up and serving models. Invoke-RestMethod elsewhere in this repo isn't
    # affected (confirmed) since it doesn't go through the HTML parser.
    # TimeoutSec 5, not 2: curl hits this same endpoint in ~0.2s, but
    # Invoke-WebRequest's underlying .NET HTTP stack adds proxy
    # auto-detection overhead even for localhost — confirmed live, 2s
    # timed out 3/3 tries while 5s succeeded reliably. Matches the 5s
    # timeout scripts/ensure_requirements.ps1 already uses for this same
    # check.
    $null = Invoke-WebRequest -Uri "$LmStudioEndpoint/v1/models" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
}

# Tier 3: Ollama (Mac local) — on Windows, could be Mac via LAN or localhost if running
$Tier3 = Test-TierAvailable -Tier 3 -Name "Ollama (Mac local)" -CheckCmd {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
}

# Tier 4: GLM-5.2 (BigModel fallback)
$Tier4 = Test-TierConfigured -Tier 4 -Name "GLM-5.2 (BigModel fallback)" -FilePath (Join-Path $SecretsDir 'glm52-api-key')

# Tier 5: OpenRouter (cloud fallback)
$Tier5 = Test-TierConfigured -Tier 5 -Name "OpenRouter (cloud fallback)" -FilePath (Join-Path $SecretsDir 'openrouter-api-key')

Log ""

# If status-only, exit now
if ($StatusOnly) {
    exit 0
}

# Check if any tier is available
$AvailableCount = 0
if ($Tier1) { $AvailableCount++ }
if ($Tier2) { $AvailableCount++ }
if ($Tier3) { $AvailableCount++ }
if ($Tier4) { $AvailableCount++ }
if ($Tier5) { $AvailableCount++ }

if ($AvailableCount -eq 0) {
    Write-Host "${Red}⚠️  No model tiers are currently available!${Reset}" -ForegroundColor Red
    Write-Host "${Red}At least one tier should be online. Check:${Reset}" -ForegroundColor Red
    Write-Host "  • Tier 1 (ClinePass): Get-Command cline"
    Write-Host "  • Tier 2 (LM Studio): Invoke-WebRequest http://localhost:1234/v1/models"
    Write-Host "  • Tier 3 (Ollama): Invoke-WebRequest http://localhost:11434/api/tags"
    Write-Host "  • Tier 4 (GLM-5.2): Test-Path ~/.openclaw/secrets/glm52-api-key"
    Write-Host "  • Tier 5 (OpenRouter): Test-Path ~/.openclaw/secrets/openrouter-api-key"
}

# Prompt for OpenRouter setup if not configured and flag is set
if (-not $Tier5 -and $SetupOpenRouter) {
    Log "Tier 5 (OpenRouter) not configured. Setup required."
    Log "Run: bash -c 'bash ~/.openclaw/.../setup-openrouter.sh'"
    Log "Or: .\platform\windows\setup-openrouter.ps1 (when available)"
}

Log ""
Log "Fallback chain: If tier N becomes unavailable, tier N+1 will automatically take over."
Log "Ensure ALL tiers are AVAILABLE or CONFIGURED for maximum resilience."
Log ""

# Final gate: at least tier 3 or 5 should be available
if ($Tier3 -or $Tier5) {
    $TierName = if ($Tier3) { "Ollama" } else { "OpenRouter" }
    Log "✅ Fallback chain healthy: $TierName available"
    exit 0
} else {
    Write-Host "${Yellow}⚠️  Fallback chain degraded: Ollama offline AND OpenRouter not configured${Reset}" -ForegroundColor Yellow
    Write-Host "${Yellow}    Run Windows setup for OpenRouter when available${Reset}" -ForegroundColor Yellow
    exit 1
}
