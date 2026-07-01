# cline_autoresearcher_watch.ps1 — AutoResearcher 15-min checkback watcher (Windows)
#
# Called by start.ps1 with three positional args:
#   $1 = RepoRoot   (orama-system repo root)
#   $2 = UsPython   (Python interpreter path)
#   $3 = LogDir     (.logs directory)
#
# Runs an infinite loop checking every 15 minutes whether the ClinePass
# AutoResearcher fallback should be active. When the Hermes Gateway is
# paused, not running, or rate-limited, and LM Studio Win is idle, the
# Cline Bot takes over as AutoResearcher.
#
# Resilience: 10x peer unreachable -> solo mode (lan_peer_session.py).
# In solo mode, checks back every 15 minutes if the peer is online.
param(
    [string]$RepoRoot,
    [string]$UsPython = "python3",
    [string]$LogDir
)

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
if (-not $LogDir) { $LogDir = Join-Path $RepoRoot ".logs" }

$AutoResearcher = Join-Path $RepoRoot "scripts\cline_autoresearcher.py"
$Session = Join-Path $RepoRoot "bin\orama-system\skills\hermes-harness\scripts\lan_peer_session.py"
$ArLog = Join-Path $LogDir "autoresearcher-watch.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-ArLog([string]$Msg) {
    $line = "{0} [autoresearcher] {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Msg
    Add-Content -Path $ArLog -Value $line
    Write-Output $line
}

Write-ArLog "AutoResearcher watcher started (Windows) - 15-min checkback cycle"
Write-ArLog "  RepoRoot=$RepoRoot"
Write-ArLog "  UsPython=$UsPython"
Write-ArLog "  LogDir=$LogDir"

while ($true) {
    if (Test-Path $AutoResearcher) {
        $checkRaw = & $UsPython $AutoResearcher --platform windows --check --json 2>$null
        $check = $null
        try { $check = $checkRaw | ConvertFrom-Json } catch {}

        if ($check -and $check.should_fallback) {
            Write-ArLog "fallback active: $($check.reason)"

            if (Test-Path $Session) {
                & $UsPython $Session should-retry 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-ArLog "co-orchestration: peer reachable - retrying"
                } else {
                    Write-ArLog "solo mode: peer unreachable 10x - 15-min checkback active"
                }
            }
        } elseif ($check) {
            Write-ArLog "fallback inactive: $($check.reason)"
        } else {
            Write-ArLog "ERROR: cline_autoresearcher.py --check produced no parseable output"
        }
    } else {
        Write-ArLog "ERROR: cline_autoresearcher.py not found at $AutoResearcher"
    }

    Start-Sleep -Seconds 900  # 15 minutes
}
