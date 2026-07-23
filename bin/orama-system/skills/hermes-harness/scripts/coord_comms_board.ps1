<#
.SYNOPSIS
Coord comms board — recur around full enchilada: coordination board,
peer inbox, GossipBus lanes, whiteboard/last-pulse metadata.

.DESCRIPTION
Reusable 5-minute heartbeat for local operator harness or Task Scheduler.
This is a thin caller; the real queue/probe logic lives in coord_pulse.ps1
and probe_lan_peer.py. This script normalizes args, preserves env vars,
and returns actionable counts for Hermes/cron/operator UI.

.PARAMETER Minutes
Listen span. Default: 5. Use 0 for one-shot.

.PARAMETER DryRun
Write planned actions only; no peer HTTP / no spawn.

.PARAMETER Json
Structured output {ok, minutes, summary{}, checks{}}.

.EXAMPLE
powershell -File scripts/coord_comms_board.ps1 -Minutes 5 -Json

.EXAMPLE
powershell -File scripts/coord_comms_board.ps1 -DryRun

.NOTES
Runs safely on a clean clone: every path is repo-relative.
Requires: ORAMA_SYSTEM_PATH / PERPETUA_TOOLS_PATH OR script dir discovery.
#>

[CmdletBinding()]
param(
  [int]$Minutes = 5,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptRoot)
if (-not $env:ORAMA_SYSTEM_PATH) {
  $env:ORAMA_SYSTEM_PATH = $RepoRoot
}
if (-not $env:PERPETUA_TOOLS_PATH) {
  $pt = Join-Path $RepoRoot '..' 'Perpetua-Tools'
  if (Test-Path $pt) { $env:PERPETUA_TOOLS_PATH = (Resolve-Path $pt).Path }
}

function Write-Info([string]$tag, [string]$msg) {
  Write-Host "[$tag] $msg"
}
function Write-Warn([string]$tag, [string]$msg) {
  Write-Host "[$tag][WARN] $msg" -ForegroundColor Yellow
}

$summary = @{}
$checks  = @{}

# 0) resolve scripts
$coordPulse    = Join-Path $ScriptRoot 'coord_pulse.ps1'
$coordMonitor  = Join-Path $ScriptRoot 'coord_monitor.ps1'
$probe         = Join-Path $ScriptRoot 'probe_lan_peer.py'
$assignList    = Join-Path $ScriptRoot 'lan_peer_assign.py'
$agentCoord    = Join-Path $env:PERPETUA_TOOLS_PATH 'scripts' 'agent_coordination.py'

foreach ($p in @($coordPulse,$coordMonitor,$probe,$assignList,$agentCoord)) {
  if (-not (Test-Path $p)) { $checks[$p] = 'MISSING' } else { $checks[$p] = 'OK' }
}

# 1) optional peer probe
$probes = @()
if ($checks[$probe] -eq 'OK') {
  if (-not $DryRun) {
    try {
      $pb = python $probe --json 2>&1
      Write-Info 'probe' 'peer probe queued'
      $probes += $pb
    } catch {
      Write-Warn 'probe' $_.Exception.Message
      $checks['peer_probe_json'] = 'FAIL'
    }
  } else {
    Write-Info 'probe' 'dry-run: skip peer probe'
    $checks['peer_probe_json'] = 'DRY'
  }
} else { $checks['peer_probe_json'] = 'SKIP' }

# 2) agent coordination board state
$heartbeatPath = Join-Path $RepoRoot 'bin' 'orama-system' 'skills' 'hermes-harness' 'references' 'results'
if (-not (Test-Path $heartbeatPath)) { New-Item -ItemType Directory -Force -Path $heartbeatPath | Out-Null }
$boardNow = (Get-Date).ToUniversalTime().ToString('u')
$summary['boardTimestamp'] = $boardNow
$summary['heartbeatDir']   = $heartbeatPath

# 3) optional communicator heartbeat; keep lane healthy
$lane = 'hermes'
if ($checks[$agentCoord] -eq 'OK') {
  try {
    if (-not $DryRun) {
      python $agentCoord heartbeat pulse $lane 2>&1 | Out-Null
      $checks['heartbeat'] = 'OK'
    } else { $checks['heartbeat'] = 'DRY' }
  } catch {
    $checks['heartbeat'] = 'FAIL'
    Write-Warn 'heartbeat' $_.Exception.Message
  }
} else { $checks['heartbeat'] = 'SKIP' }

# 4) optional queue/pulse
$pulseResult = ''
if ($checks[$coordPulse] -eq 'OK') {
  if (-not $DryRun) {
    try {
      $pulseResult = & powershell -NoProfile -ExecutionPolicy Bypass -File $coordPulse
      $summary['pulseOutput'] = $pulseResult
      $checks['coordPulse'] = 'OK'
    } catch {
      $checks['coordPulse'] = 'FAIL'
      Write-Warn 'coordPulse' $_.Exception.Message
    }
  } else { $checks['coordPulse'] = 'DRY' }
} else { $checks['coordPulse'] = 'SKIP' }

# 5) peer inbox summary
$inboxSummary = 'queued'
if (($checks[$assignList] -eq 'OK') -and (-not $DryRun)) {
  try {
    $listOut = python $assignList list 2>&1
    if ($LASTEXITCODE -eq 0) { $inboxSummary = $listOut }
    $checks['peerInboxList'] = 'OK'
  } catch { $checks['peerInboxList'] = 'FAIL'; $inboxSummary = 'FAIL' }
} else { $checks['peerInboxList'] = 'SKIP'; $inboxSummary = 'SKIP' }
$summary['peerInbox'] = $inboxSummary

$summary['checks'] = $checks
$summary['dryRun'] = [bool]$DryRun
$summary['minutes'] = $Minutes

Write-Info 'comms-board' ('mode=' + (if ($DryRun){'dryrun'} else {'live'}) + ' minutes=' + $Minutes)
if (-not $Json) {
  $summary.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Host ('{0}: {1}' -f $_.Name, $_.Value) }
} else {
  $summary | ConvertTo-Json -CompDepth 6
}
