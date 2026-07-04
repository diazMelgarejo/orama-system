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

    try {
        $result = & $CheckCmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host "$Tier. $($Name.PadRight(38)) ${Green}[AVAILABLE]${Reset}"
            return $true
        } else {
            Write-Host "$Tier. $($Name.PadRight(38)) ${Red}[OFFLINE]${Reset}"
            return $false
        }
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
    exit 0
}

# Tier 2: LM Studio (Windows GPU) — on Windows, typically at localhost:1234
$Tier2 = Test-TierAvailable -Tier 2 -Name "LM Studio (Windows GPU)" -CheckCmd {
    $LmStudioEndpoint = $env:LM_STUDIO_WIN_ENDPOINTS -or 'http://localhost:1234'
    $null = Invoke-WebRequest -Uri "$LmStudioEndpoint/v1/models" -TimeoutSec 2 -ErrorAction Stop
    exit 0
}

# Tier 3: Ollama (Mac local) — on Windows, could be Mac via LAN or localhost if running
$Tier3 = Test-TierAvailable -Tier 3 -Name "Ollama (Mac local)" -CheckCmd {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    exit 0
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
