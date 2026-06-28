# 15-minute co-orchestration monitor (Win operator tick)
param(
    [int]$Minutes = 15,
    [int]$IntervalSec = 120
)

$ErrorActionPreference = "Continue"
$Repo = $env:ORAMA_SYSTEM_PATH
if (-not $Repo) { throw "Set ORAMA_SYSTEM_PATH to the orama-system repo root before running coord_monitor.ps1" }
$LogDir = Join-Path $env:USERPROFILE ".openclaw\state\lan_peer\monitor"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("monitor-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
$end = (Get-Date).AddMinutes($Minutes)
"=== coord monitor start $(Get-Date -Format o) duration=${Minutes}m interval=${IntervalSec}s ===" | Tee-Object -FilePath $Log

while ((Get-Date) -lt $end) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "`n--- tick $ts ---" | Tee-Object -FilePath $Log -Append
    Push-Location $Repo
    try {
        git fetch origin main --quiet 2>&1 | Out-Null
        $behind = (git rev-list HEAD..origin/main --count 2>$null)
        if ($behind -gt 0) { "git: behind origin/main by $behind - run git pull" | Tee-Object -FilePath $Log -Append }
        else { "git: up to date with origin/main" | Tee-Object -FilePath $Log -Append }

        python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json 2>&1 |
            Select-Object -First 8 | Tee-Object -FilePath $Log -Append

        python bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py enqueue 2>&1 |
            Tee-Object -FilePath $Log -Append

        python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py list 2>&1 |
            Select-String -Pattern "win-autoresearcher|win-coder|coord-00" |
            Tee-Object -FilePath $Log -Append

        python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py list --peer 2>&1 |
            Select-String -Pattern "mac-h5|coord-005|assignment" |
            Tee-Object -FilePath $Log -Append
    }
    finally { Pop-Location }
  if ((Get-Date).AddSeconds($IntervalSec) -ge $end) { break }
  Start-Sleep -Seconds $IntervalSec
}
"=== coord monitor end $(Get-Date -Format o) log=$Log ===" | Tee-Object -FilePath $Log -Append
Write-Output $Log
