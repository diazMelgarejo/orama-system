# coord_pulse.ps1 — Win one-shot Hermes coord pulse (900s scheduled tick)
# PLAN: references/coord-pulse-plan.md · unified: references/pulse-unified-comparison.md
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root" }

# Resolve the repo's own .venv Python, not bare `python` -- a scheduled task
# tick is not guaranteed to see the venv first on PATH, and this repo's own
# requirements.txt packages (e.g. websockets) only live in the venv. Verified
# live: probe_lan_peer.py's ws-peer check falsely reported "missing
# websockets" because bare `python` resolved a different, package-less
# system interpreter even though the venv had it installed correctly.
. (Join-Path $Repo "scripts\lib\get-best-python.ps1")
$PythonExe = Get-BestPython $Repo

$Pt = $env:PERPETUA_TOOLS_PATH
$LogDir = Join-Path $env:USERPROFILE ".openclaw\state\lan_peer"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "coord-pulse.log"
$Lock = Join-Path $LogDir "win_pulse.lock"
$Seen = Join-Path $LogDir "last_pulse_seen.json"
$WinQueue = Join-Path $Repo "bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py"
$LanSession = Join-Path $Repo "bin\orama-system\skills\hermes-harness\scripts\lan_peer_session.py"

function Write-Log([string]$Msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Msg
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

function Save-SeenInbox {
    & $PythonExe bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py list 2>$null |
        & $PythonExe -c "import sys,json; open(r'$Seen','w').write(json.dumps([x['filename'] for x in json.load(sys.stdin).get('files',[])], indent=2))" 2>$null
}

function Invoke-LanPeerSession {
    # -LanArgs, not -Args: $Args collides with PowerShell's automatic $args
    # variable (case-insensitive) -- matches the same fix applied to
    # platform/windows/start.ps1's Invoke-LanPeerSession (2026-07-03).
    param([string[]]$LanArgs)
    if (-not (Test-Path $LanSession)) {
        Write-Log "session state script missing: $LanSession"
        return $true
    }
    & $PythonExe $LanSession @LanArgs 2>&1 | ForEach-Object { Write-Log $_ }
    return ($LASTEXITCODE -eq 0)
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

    $probeTimeout = if ($env:LAN_PEER_PROBE_TIMEOUT) { $env:LAN_PEER_PROBE_TIMEOUT } else { '2' }
    $statusTimeout = if ($env:LAN_PEER_STATUS_TIMEOUT) { $env:LAN_PEER_STATUS_TIMEOUT } else { '3' }
    $wsTimeout = if ($env:LAN_PEER_WS_TIMEOUT) { $env:LAN_PEER_WS_TIMEOUT } else { '2' }
    $httpTimeout = if ($env:LAN_PEER_HTTP_TIMEOUT) { $env:LAN_PEER_HTTP_TIMEOUT } else { '2' }
    $retrySeconds = if ($env:LAN_PEER_DEGRADED_RETRY_SECONDS) { $env:LAN_PEER_DEGRADED_RETRY_SECONDS } else { '900' }
    if (-not (Invoke-LanPeerSession -LanArgs @('should-retry'))) {
        Write-Log "macOS-only degraded mode active; next peer retry waits for LAN_PEER_DEGRADED_RETRY_SECONDS=$retrySeconds"
    } else {
        $probeOutput = & $PythonExe bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json --timeout $probeTimeout --status-timeout $statusTimeout --ws-timeout $wsTimeout 2>&1
        $probeExit = $LASTEXITCODE
        $probeOutput | Select-Object -First 12 | ForEach-Object { Write-Log $_ }
        if ($probeExit -eq 0) {
            $null = Invoke-LanPeerSession -LanArgs @('record-success')
            $flushOutput = & $PythonExe bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py flush-outbox --peer --timeout $httpTimeout 2>&1
            $flushOutput | Select-Object -First 20 | ForEach-Object { Write-Log $_ }

            # Phase 4: Query fleet topology from peers and re-classify
            Write-Log "Querying fleet topology from peers..."
            $topologyOutput = & $PythonExe bin\orama-system\skills\hermes-harness\scripts\query_peer_topology.py --timeout $httpTimeout 2>&1
            $topologyExit = $LASTEXITCODE
            $topologyOutput | Select-Object -First 10 | ForEach-Object { Write-Log $_ }
            if ($topologyExit -ne 0) {
                Write-Log "topology query failed (non-fatal)"
            }
        } else {
            $null = Invoke-LanPeerSession -LanArgs @('record-failure', '--error', 'probe_lan_peer.py failed')
        }
    }

    $gateJson = & $PythonExe $WinQueue pulse-gate --seen-file $Seen 2>&1 | Out-String
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
