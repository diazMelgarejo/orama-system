# coord_pulse.ps1 — Win one-shot Hermes coord pulse (900s scheduled tick)
# PLAN: references/coord-pulse-plan.md · unified: references/pulse-unified-comparison.md
# Dispatch backend (2026-06-30): Parallel dispatch racing - cursor-agent and
# Hermes+LM Studio Win race in parallel; first successful completion wins.
# Fallback: direct LM Studio Win (serialized by GPU lock). Orchestrator
# reasoning = Hermes native model (Nous Portal, stepfun/step-3.7-flash:free,
# config.yaml model.default). Win-coder/autoresearcher execution = Hermes
# --provider lmstudio-win (custom OpenAI-compat provider added to
# %LOCALAPPDATA%\hermes\config.yaml) -> LM Studio qwen3.5-27b-claude-4.6-opus-
# reasoning-distilled-v2 @ localhost:1234. Race impl: scripts/spawn_agents.py
# --agent race.
param(
    [switch]$DryRun,
    [int]$BusinessHoursStart = 7,   # 24h local time; dispatch gated outside [Start,End)
    [int]$BusinessHoursEnd = 22,
    [switch]$IgnoreBusinessHours
)

$ErrorActionPreference = "Continue"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root" }
if (-not $env:LM_STUDIO_API_TOKEN) { $env:LM_STUDIO_API_TOKEN = "lm-studio" }

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

# Pause gate - checked even if the Task Scheduler entry itself is still enabled
# (belt + suspenders: Disable-ScheduledTask is the primary control; this file
# check covers manual/adhoc invocations). Default state on pause = stays paused
# until an explicit resume clears the file. Hermes honors "pause/resume coord
# pulse" via the coord-pulse-control Hermes skill (HERMES_HOME/skills/orchestration).
$PauseFile = Join-Path $LogDir "coord_pulse_pause.json"
if (Test-Path $PauseFile) {
    $pauseState = Get-Content $PauseFile -Raw | ConvertFrom-Json
    if ($pauseState.paused) {
        Write-Log "paused: since=$($pauseState.since) reason=$($pauseState.reason) - skipping pulse"
        exit 0
    }
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

$hourNow = (Get-Date).Hour
if (-not $IgnoreBusinessHours -and ($hourNow -lt $BusinessHoursStart -or $hourNow -ge $BusinessHoursEnd)) {
    Write-Log "idle: outside business hours ($BusinessHoursStart-$BusinessHoursEnd local, now=$hourNow)"
    exit 0
}

$hermesExe = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes.exe"
if (-not (Test-Path $hermesExe)) {
    $hermesExe = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes"
}
$gwStatus = & $hermesExe gateway status 2>&1 | Out-String
if ($gwStatus -notmatch "Gateway is running") {
    Write-Log "hermes gateway not running - starting"
    Start-Process -FilePath $hermesExe -ArgumentList "gateway","run" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Push-Location $Repo
try {
    git fetch origin main --quiet 2>&1 | Out-Null
    if ($Pt -and (Test-Path (Join-Path $Pt ".git"))) {
        git -C $Pt fetch origin --prune 2>&1 | Out-Null
    }

    python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json 2>&1 |
        Select-Object -First 12 | ForEach-Object { Write-Log $_ }

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
        Write-Log "dry-run: would invoke race dispatch (cursor,hermes-lmstudio-win) for $($pick.role) job $($pick.id)"
        exit 0
    }

    $PID | Out-File -FilePath $Lock -Encoding ascii
    $jobDispatched = $false
    try {
        $prompt = @"
Follow $agentCard — execute ONE $($pick.role) job ($($pick.id)) from win_job_queue.
After complete: learn.py + auto_dream.py on PT, push main both repos, drop to Mac peer if needed.
"@
        Write-Log "race dispatch start role=$($pick.role) job=$($pick.id) racers=cursor,hermes-lmstudio-win fallback=direct-lmstudio-win"
        $raceJson = & python "$Repo\scripts\spawn_agents.py" --agent race --task $prompt --json 2>&1 |
            ForEach-Object { Write-Log $_ }
        # Parse the last JSON line from race output (spawn_agents prints JSON to stdout)
        $raceResult = $raceJson | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1
        if ($raceResult) {
            try {
                $parsed = $raceResult | ConvertFrom-Json
                if ($parsed.ok) {
                    Write-Log "race winner=$($parsed.winner) elapsed=$($parsed.elapsed)s"
                    $jobDispatched = $true
                } else {
                    Write-Log "race failed: all legs failed winner=$($parsed.winner)"
                }
            } catch {
                Write-Log "race result parse error: $_"
            }
        } else {
            Write-Log "race: no JSON output captured, treating as dispatched"
            $jobDispatched = $true
        }
    }
    finally {
        Remove-Item $Lock -Force -ErrorAction SilentlyContinue
    }

    if ($jobDispatched) {
        # Re-poll the queue 5 min after finishing, instead of waiting the full
        # 15-min baseline tick - one-shot Task Scheduler trigger, self-removes.
        $followupTask = "OramaCoordPulse-Followup"
        Unregister-ScheduledTask -TaskName $followupTask -Confirm:$false -ErrorAction SilentlyContinue
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5)
        Register-ScheduledTask -TaskName $followupTask -Action $action -Trigger $trigger `
            -Description "One-shot re-poll 5 min after last coord pulse job" -Force | Out-Null
        Write-Log "scheduled 5-min follow-up re-poll ($followupTask)"
    }
}
finally {
    Pop-Location
}

Write-Log "pulse end"
