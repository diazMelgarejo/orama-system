# service_watchdog.ps1 — Win one-shot service health tick (scheduled)
# Sibling of bin/orama-system/skills/hermes-harness/scripts/coord_pulse.ps1 —
# same one-shot-tick-under-Task-Scheduler idiom, applied to PT/orama/Portal
# service health instead of LAN coordination.
#
# Checks PT (:8000), orama (:8001), Portal (:8002). Any down service gets up
# to 3 restart attempts (via platform/windows/start.ps1, which only touches
# the actually-down ones — Start-Service already no-ops on a live port). If a
# service is STILL down after 3 attempts: log CRITICAL, write a standing
# alert file, try a Windows toast + Application event log entry (best-effort,
# never fatal), and drop the alert to the Mac peer inbox so other devices in
# the fleet see the failure even if this box can't self-heal it.
#
# Usage:
#   powershell -File scripts\service_watchdog.ps1            # normal tick
#   powershell -File scripts\service_watchdog.ps1 -DryRun     # check only, no restarts/alerts sent
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root" }

# Resolve the repo's own .venv Python, not bare `python` — see
# scripts/lib/get-best-python.ps1 for why (a scheduled tick is not
# guaranteed to see the venv first on PATH).
. (Join-Path $Repo "scripts\lib\get-best-python.ps1")
$PythonExe = Get-BestPython $Repo

# State lives OUTSIDE the tracked repo (matches install_coord_pulse.ps1's
# $env:USERPROFILE\.openclaw\state\lan_peer\ convention) — NOT $Repo\.logs.
# A generated wrapper/log under a tracked repo path is a doxxing footgun:
# *.log is gitignored here but a *.ps1 wrapper embedding this machine's repo
# path is not, and would show up as untracked-but-stageable. Verified live
# (git status flagged exactly this before the fix).
$LogDir = Join-Path $env:USERPROFILE ".openclaw\state\service_watchdog"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "service-watchdog.log"
$AlertFile = Join-Path $LogDir "SERVICE_DOWN_ALERT.md"
$Lock = Join-Path $LogDir ".service_watchdog.lock"

$MaxAttempts = 3
$RetryDelaySeconds = 10

$PtPort     = if ($env:PT_PORT)     { [int]$env:PT_PORT }     else { 8000 }
$UsPort     = if ($env:US_PORT)     { [int]$env:US_PORT }     else { 8001 }
$PortalPort = if ($env:PORTAL_PORT) { [int]$env:PORTAL_PORT } else { 8002 }
$Services = @(
    @{ Name = "PT";     Port = $PtPort },
    @{ Name = "orama";  Port = $UsPort },
    @{ Name = "Portal"; Port = $PortalPort }
)

function Write-Log([string]$Level, [string]$Msg) {
    $line = "{0} {1,-8} {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Level, $Msg
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-PortUp([int]$Port, [int]$TimeoutMs = 800) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $conn = $tcp.ConnectAsync('localhost', $Port)
        $ok = $conn.Wait($TimeoutMs) -and $tcp.Connected
        $tcp.Close()
        return $ok
    } catch { return $false }
}

function Send-Alert([string]$Body) {
    # Standing alert file — always overwritten with the latest failure so a
    # human (or another automated check) can `cat`/tail it without digging
    # through the log. Never left stale-but-silent: cleared on recovery
    # elsewhere in this script's normal flow (next healthy tick removes it).
    Set-Content -Path $AlertFile -Value $Body -Encoding UTF8

    # Best-effort local notification. Neither path is allowed to throw —
    # a scheduled task with no interactive desktop session must not hang
    # or fail the tick because a notification API is unavailable.
    try {
        if (Get-Module -ListAvailable -Name BurntToast -ErrorAction SilentlyContinue) {
            Import-Module BurntToast -ErrorAction Stop
            New-BurntToastNotification -Text "orama-system service down", "Auto-restart failed after $MaxAttempts attempts — see $AlertFile" -ErrorAction Stop
        }
    } catch {
        Write-Log "WARN" "toast notification failed (non-fatal): $_"
    }
    try {
        $src = "OramaServiceWatchdog"
        if (-not [System.Diagnostics.EventLog]::SourceExists($src)) {
            New-EventLog -LogName Application -Source $src -ErrorAction Stop
        }
        Write-EventLog -LogName Application -Source $src -EntryType Error -EventId 1 -Message $Body -ErrorAction Stop
    } catch {
        Write-Log "WARN" "Application event log write failed (non-fatal, likely needs admin once): $_"
    }

    # Inform other fleet devices — drop to the Mac peer inbox. Gracefully
    # queues to local outbox (flushed by coord_pulse.ps1 later) if the peer
    # is unreachable right now; never blocks or throws.
    try {
        $tmpAlert = Join-Path $env:TEMP "orama-service-down-alert.md"
        Set-Content -Path $tmpAlert -Value $Body -Encoding UTF8
        $dropScript = Join-Path $Repo "bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py"
        if (Test-Path $dropScript) {
            & $PythonExe $dropScript drop --peer --file $tmpAlert --assignee mac --topic "ops/service-down" 2>&1 |
                ForEach-Object { Write-Log "INFO" "peer-drop: $_" }
        } else {
            Write-Log "WARN" "lan_peer_assign.py not found — could not notify peer devices"
        }
    } catch {
        Write-Log "WARN" "peer alert drop failed (non-fatal): $_"
    }
}

if (Test-Path $Lock) {
    $pidText = Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidText -and (Get-Process -Id $pidText -ErrorAction SilentlyContinue)) {
        Write-Log "INFO" "skip: watchdog lock held by pid $pidText (previous tick still running)"
        exit 0
    }
    Remove-Item $Lock -Force -ErrorAction SilentlyContinue
}
$PID | Out-File -FilePath $Lock -Encoding ascii

try {
    $down = $Services | Where-Object { -not (Test-PortUp $_.Port) }

    if (-not $down) {
        Write-Log "INFO" "healthy: PT/orama/Portal all up"
        if (Test-Path $AlertFile) { Remove-Item $AlertFile -Force -ErrorAction SilentlyContinue }
        exit 0
    }

    $downNames = ($down | ForEach-Object { $_.Name }) -join ", "
    Write-Log "WARN" "down: $downNames"

    if ($DryRun) {
        Write-Log "INFO" "dry-run: would attempt restart (up to $MaxAttempts tries)"
        exit 0
    }

    $StartPs1 = Join-Path $Repo "platform\windows\start.ps1"
    $attempt = 0
    $stillDown = $down
    while ($attempt -lt $MaxAttempts -and $stillDown) {
        $attempt++
        Write-Log "WARN" "restart attempt $attempt/$MaxAttempts for: $(($stillDown | ForEach-Object { $_.Name }) -join ', ')"

        # Deliberately NOT `& powershell.exe ... | ForEach-Object {...}` (live pipe)
        # NOR `Start-Process -Wait` — both verified live to hang indefinitely here.
        # start.ps1 spawns PT/orama/Portal as long-running detached processes;
        # a live pipe's read end never sees EOF because a grandchild inherits a
        # copy of the write handle, and Start-Process -Wait was confirmed (via
        # CIM + repeated live tests) to block on more than just the direct
        # child's exit — a known quirk with nested process trees, not
        # documented behavior we can rely on. The only invocation that can
        # never hang the watchdog itself is an explicit bounded poll on the
        # direct child's PID: -PassThru gives the process object without
        # waiting, then we poll HasExited with our own hard timeout. Even if
        # start.ps1 itself somehow never exits, the watchdog moves on instead
        # of blocking Task Scheduler's tick forever.
        $stdoutFile = Join-Path $LogDir "service-watchdog-start-stdout.tmp.log"
        $stderrFile = Join-Path $LogDir "service-watchdog-start-stderr.tmp.log"
        $proc = Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$StartPs1`"", "--no-open") `
            -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile `
            -NoNewWindow -PassThru
        $waitDeadline = (Get-Date).AddSeconds(45)
        while (-not $proc.HasExited -and (Get-Date) -lt $waitDeadline) {
            Start-Sleep -Milliseconds 500
        }
        if (-not $proc.HasExited) {
            Write-Log "WARN" "start.ps1 (pid $($proc.Id)) did not exit within 45s — continuing anyway, not killing it (its own child services may still be starting up)"
        }
        Get-Content -Path $stdoutFile, $stderrFile -Encoding UTF8 -ErrorAction SilentlyContinue |
            ForEach-Object { Write-Log "INFO" "start.ps1: $_" }
        Remove-Item $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue

        Start-Sleep -Seconds $RetryDelaySeconds
        $stillDown = $Services | Where-Object { -not (Test-PortUp $_.Port) }
    }

    if (-not $stillDown) {
        Write-Log "INFO" "recovered after $attempt attempt(s): $downNames"
        if (Test-Path $AlertFile) { Remove-Item $AlertFile -Force -ErrorAction SilentlyContinue }
        exit 0
    }

    $failedNames = ($stillDown | ForEach-Object { $_.Name }) -join ", "
    $body = @"
# orama-system service watchdog — CRITICAL

**Time:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Host:** win service watchdog
**Still down after $MaxAttempts restart attempts:** $failedNames

Auto-restart via platform\windows\start.ps1 did not bring these services back
after $MaxAttempts tries ($RetryDelaySeconds s apart). Manual intervention
needed — check .logs\<service>.log and .logs\service-watchdog.log.
"@
    Write-Log "CRITICAL" "still down after $MaxAttempts attempts: $failedNames — alerting"
    Send-Alert -Body $body
}
finally {
    Remove-Item $Lock -Force -ErrorAction SilentlyContinue
}
