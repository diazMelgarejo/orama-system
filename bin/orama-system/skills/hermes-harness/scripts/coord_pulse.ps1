# coord_pulse.ps1 — Win one-shot Hermes coord pulse (900s scheduled tick)
# PLAN: references/coord-pulse-plan.md · unified: references/pulse-unified-comparison.md
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root" }

$Pt = $env:PERPETUA_TOOLS_PATH
$LogDir = Join-Path $env:USERPROFILE ".openclaw\state\lan_peer"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "coord-pulse.log"
$Lock = Join-Path $LogDir "win_pulse.lock"
$Seen = Join-Path $LogDir "last_pulse_seen.json"
$WinQueue = Join-Path $Repo "bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py"

function Write-Log([string]$Msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Msg
    Add-Content -Path $Log -Value $line
    Write-Output $line
}

function Save-SeenInbox {
    python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py list 2>$null |
        python -c "import sys,json; open(r'$Seen','w').write(json.dumps([x['filename'] for x in json.load(sys.stdin).get('files',[])], indent=2))" 2>$null
}

if (Test-Path $Lock) {
    $pidText = Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidText -and (Get-Process -Id $pidText -ErrorAction SilentlyContinue)) {
        Write-Log "skip: win_pulse.lock held by pid $pidText"
        exit 0
    }
    Remove-Item $Lock -Force -ErrorAction SilentlyContinue
}

Write-Log "pulse start dry_run=$($DryRun.IsPresent)"

Push-Location $Repo
try {
    git fetch origin main --quiet 2>&1 | Out-Null
    if ($Pt -and (Test-Path (Join-Path $Pt ".git"))) {
        git -C $Pt fetch origin --prune 2>&1 | Out-Null
    }

    python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json 2>&1 |
        Select-Object -First 12 | ForEach-Object { Write-Log $_ }
    python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py flush-outbox --peer 2>&1 |
        Select-Object -First 20 | ForEach-Object { Write-Log $_ }

    $gateJson = python $WinQueue pulse-gate --seen-file $Seen 2>&1 | Out-String
    Write-Log "gate: $gateJson"

    $gate = $gateJson | ConvertFrom-Json
    Save-SeenInbox

    if ($gate.status -ne "actionable") {
        Write-Log "idle: gate=$($gate.status) reason=$($gate.reason)"
        exit 0
    }

    $pick = $gate.pick
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
