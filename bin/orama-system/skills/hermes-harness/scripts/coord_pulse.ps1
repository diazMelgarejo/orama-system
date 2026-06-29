# coord_pulse.ps1 — Win one-shot Hermes coord pulse (900s scheduled tick)
# PLAN: references/coord-pulse-plan.md
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root" }

$LogDir = Join-Path $env:USERPROFILE ".openclaw\state\lan_peer"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "coord-pulse.log"
$Lock = Join-Path $LogDir "win_pulse.lock"

# Blocked until prerequisite lands (operator steer + assignment card)
$BlockedPending = @(
    "win-coder-l1-comms-autoplan-backlog.md"
)

function Write-Log([string]$Msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Msg
    Add-Content -Path $Log -Value $line
    Write-Output $line
}

if (Test-Path $Lock) {
    $pidText = Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidText -and (Get-Process -Id $pidText -ErrorAction SilentlyContinue)) {
        Write-Log "skip: win_pulse.lock held by pid $pidText"
        exit 0
    }
}

Write-Log "pulse start dry_run=$($DryRun.IsPresent)"

Push-Location $Repo
try {
    git fetch origin main --quiet 2>&1 | Out-Null

    python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json 2>&1 |
        Select-Object -First 12 | ForEach-Object { Write-Log $_ }

    python bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py enqueue 2>&1 |
        ForEach-Object { Write-Log $_ }

    $statusJson = python bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py status 2>&1 | Out-String
    Write-Log "queue: $statusJson"

    $status = $statusJson | ConvertFrom-Json
    foreach ($role in @("coder", "autoresearcher")) {
        if ($status.$role.active) {
            Write-Log "skip: $role job active"
            exit 0
        }
    }

    $actionable = @()
    foreach ($role in @("coder", "autoresearcher")) {
        foreach ($id in $status.$role.pending) {
            if ($BlockedPending -notcontains $id) {
                $actionable += @{ role = $role; id = $id }
            }
        }
    }

    if ($actionable.Count -eq 0) {
        Write-Log "idle: no actionable pending jobs (blocked or empty)"
        exit 0
    }

    # Prefer first non-blocked pending per role (queue order); skip blocked entries in list
    $pick = $actionable[0]
    $agentCard = if ($pick.role -eq "coder") {
        "$Repo\.cursor\agents\win-coder-queue.md"
    } else {
        "$Repo\.cursor\agents\win-autoresearcher-queue.md"
    }

    if ($DryRun) {
        Write-Log "dry-run: would invoke cursor-agent for $($pick.role) job $($pick.id)"
        exit 0
    }

    if (-not (Get-Command cursor-agent -ErrorAction SilentlyContinue)) {
        Write-Log "skip: cursor-agent not on PATH"
        exit 0
    }

    $PID | Out-File -FilePath $Lock -Encoding ascii
    try {
        $prompt = @"
Follow $agentCard — execute ONE $($pick.role) job ($($pick.id)) from win_job_queue.
After complete: learn.py + auto_dream.py on PT, push main both repos, drop to Mac peer if needed.
"@
        Write-Log "cursor-agent start role=$($pick.role) job=$($pick.id)"
        cursor-agent --print --model composer-2.5 $prompt 2>&1 | ForEach-Object { Write-Log $_ }
    }
    finally {
        Remove-Item $Lock -Force -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}

Write-Log "pulse end"
