# install_service_watchdog.ps1 — install Win service self-heal watchdog (Task Scheduler)
# Mirrors install_coord_pulse.ps1's idiom exactly, applied to service_watchdog.ps1
# instead of coord_pulse.ps1 — PT/orama/Portal health-check-and-restart on a
# schedule, independent of any interactive session.
#
# Usage:
#   .\scripts\install_service_watchdog.ps1
#   .\scripts\install_service_watchdog.ps1 -Uninstall
#   .\scripts\install_service_watchdog.ps1 -Status

param(
    [switch]$Uninstall,
    [switch]$Status,
    [int]$IntervalSec = 300
)

$TaskName = "OramaServiceWatchdog"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) {
    $Repo = (git -C (Split-Path $PSScriptRoot -Parent) rev-parse --show-toplevel 2>$null)
}
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH or run from orama-system repo" }

$WatchdogScript = Join-Path $Repo "scripts\service_watchdog.ps1"
$PtRoot = $env:PERPETUA_TOOLS_PATH
if (-not $PtRoot) { $PtRoot = "" }

# Outside the tracked repo — matches install_coord_pulse.ps1's WrapperDir
# convention (state under %USERPROFILE%\.openclaw\state\...) and must stay
# in sync with service_watchdog.ps1's own $LogDir. Do not point this at
# $Repo\.logs: a generated wrapper embeds this machine's repo path, and
# *.log is gitignored here but a *.ps1 wrapper is not — verified live as a
# real untracked-but-stageable file before this fix.
$WrapperDir = Join-Path $env:USERPROFILE ".openclaw\state\service_watchdog"
New-Item -ItemType Directory -Force -Path $WrapperDir | Out-Null
$Wrapper = Join-Path $WrapperDir "service-watchdog-run.ps1"

if ($Status) {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
        Format-List TaskName, State, @{N="NextRun";E={(Get-ScheduledTaskInfo $_).NextRunTime}}
    if (Test-Path (Join-Path $WrapperDir "service-watchdog.log")) {
        Write-Output "--- last 5 log lines ---"
        Get-Content (Join-Path $WrapperDir "service-watchdog.log") -Tail 5 -Encoding UTF8
    }
    if (Test-Path (Join-Path $WrapperDir "SERVICE_DOWN_ALERT.md")) {
        Write-Output "--- ACTIVE ALERT ---"
        Get-Content (Join-Path $WrapperDir "SERVICE_DOWN_ALERT.md") -Encoding UTF8
    }
    exit 0
}

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Uninstalled $TaskName"
    exit 0
}

@(
    "`$env:ORAMA_SYSTEM_PATH = '$Repo'"
    "if ('$PtRoot') { `$env:PERPETUA_TOOLS_PATH = '$PtRoot' }"
    "& '$WatchdogScript'"
) | Set-Content -Path $Wrapper -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Wrapper`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Seconds $IntervalSec) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Orama service self-heal watchdog every ${IntervalSec}s" -Force | Out-Null

Write-Output "Installed $TaskName interval=${IntervalSec}s"
Write-Output "  Wrapper: $Wrapper"
Write-Output "  Log: $WrapperDir\service-watchdog.log"
Write-Output "  Alert file (only present while a service is down after 3 retries): $WrapperDir\SERVICE_DOWN_ALERT.md"
