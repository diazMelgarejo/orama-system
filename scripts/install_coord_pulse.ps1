# install_coord_pulse.ps1 — install Win 15-minute coord pulse (Task Scheduler)
# Usage:
#   .\scripts\install_coord_pulse.ps1
#   .\scripts\install_coord_pulse.ps1 -Uninstall
#   .\scripts\install_coord_pulse.ps1 -Status

<#
.SYNOPSIS
    Install, inspect or remove the Windows scheduled task that runs the LAN coord pulse.

.DESCRIPTION
    Writes a small wrapper script under the user's OpenClaw state directory (it sets ORAMA_SYSTEM_PATH and, when known, PERPETUA_TOOLS_PATH, then calls the repo's coord_pulse.ps1) and registers a repeating task named OramaCoordPulse that runs it every IntervalSec seconds. The repo root comes from ORAMA_SYSTEM_PATH or the enclosing git work tree.

.PARAMETER Uninstall
    Remove the scheduled task and exit.

.PARAMETER Status
    Show the task state, next run time and the last lines of the pulse log, then exit.

.PARAMETER IntervalSec
    Seconds between pulses (default 900, i.e. 15 minutes).

.EXAMPLE
    .\scripts\install_coord_pulse.ps1 -Status
#>
param(
    [switch]$Uninstall,
    [switch]$Status,
    [int]$IntervalSec = 900
)

$TaskName = "OramaCoordPulse"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) {
    $Repo = (git -C (Split-Path $PSScriptRoot -Parent) rev-parse --show-toplevel 2>$null)
}
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH or run from orama-system repo" }

$PulseScript = Join-Path $Repo "bin\orama-system\skills\hermes-harness\scripts\coord_pulse.ps1"
$PtRoot = $env:PERPETUA_TOOLS_PATH
if (-not $PtRoot) { $PtRoot = "" }

$WrapperDir = Join-Path $env:USERPROFILE ".openclaw\state\lan_peer"
New-Item -ItemType Directory -Force -Path $WrapperDir | Out-Null
$Wrapper = Join-Path $WrapperDir "coord-pulse-run.ps1"

if ($Status) {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
        Format-List TaskName, State, @{N="NextRun";E={(Get-ScheduledTaskInfo $_).NextRunTime}}
    if (Test-Path (Join-Path $WrapperDir "coord-pulse.log")) {
        Write-Output "--- last 5 log lines ---"
        Get-Content (Join-Path $WrapperDir "coord-pulse.log") -Tail 5
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
    "& '$PulseScript'"
) | Set-Content -Path $Wrapper -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Wrapper`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Seconds $IntervalSec) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Orama LAN coord pulse every ${IntervalSec}s" -Force | Out-Null

Write-Output "Installed $TaskName interval=${IntervalSec}s"
Write-Output "  Wrapper: $Wrapper"
Write-Output "  Log: $WrapperDir\coord-pulse.log"
Write-Output "  Plan: bin/orama-system/skills/hermes-harness/references/coord-pulse-plan.md"
