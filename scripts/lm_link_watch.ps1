# lm_link_watch.ps1 — Windows counterpart of scripts/lm_link_watch.py (PS 5.1-compatible).
# LOCAL = LM Studio http://localhost:1234/v1/models ; PEER = Mac Ollama from
# last_discovery.json (endpoints.mac.ip + :11434). Same state schema/file as the
# Python watcher: %USERPROFILE%\.openclaw\state\lm_link.json — orama AND perpetua
# read this one file. Gossip heartbeats carry model ids + queue depth only (no prompts).
# Run persistent:  powershell -ExecutionPolicy Bypass -File scripts\lm_link_watch.ps1
# Single cycle:    ... -File scripts\lm_link_watch.ps1 -Once

param([switch]$Once, [switch]$Status)

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$StateDir  = Join-Path $env:USERPROFILE ".openclaw\state"
$StateFile = Join-Path $StateDir "lm_link.json"
$Discovery = Join-Path $StateDir "last_discovery.json"
$InboxDir  = Join-Path $StateDir "lan_peer\inbox"
$LoopSec   = if ($env:LM_LINK_INTERVAL) { [int]$env:LM_LINK_INTERVAL } else { 60 }
$GossipSec = if ($env:LM_LINK_GOSSIP_INTERVAL) { [int]$env:LM_LINK_GOSSIP_INTERVAL } else { 300 }
$RetrySec  = if ($env:LM_LINK_DEGRADED_RETRY) { [int]$env:LM_LINK_DEGRADED_RETRY } else { 900 }
$MaxFails  = 10

function Get-NowIso { (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }

function Probe-Endpoint([string]$Url) {
    try {
        $r = Invoke-RestMethod -Uri $Url -TimeoutSec 5 -ErrorAction Stop
        $ids = @()
        if ($r.data)   { $ids = @($r.data | ForEach-Object { $_.id }   | Select-Object -First 12) }
        elseif ($r.models) { $ids = @($r.models | ForEach-Object { $_.name } | Select-Object -First 12) }
        return @{ up = $true; models = $ids }
    } catch { return @{ up = $false; models = @() } }
}

function Get-PeerUrl {
    try {
        $d = Get-Content $Discovery -Raw -Encoding UTF8 | ConvertFrom-Json
        $ip = $d.endpoints.mac.ip
        if ($ip -and $ip -ne "localhost") { return "http://${ip}:11434/api/tags" }
    } catch { }
    return $null
}

function Load-State {
    try { Get-Content $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $null }
}

function Run-Cycle($prev) {
    $local = Probe-Endpoint "http://localhost:1234/v1/models"
    $purl  = Get-PeerUrl
    $peerUp = $false
    if ($purl) { $peerUp = (Probe-Endpoint $purl).up }

    $fails = 0
    if (-not $peerUp) {
        $fails = 1
        if ($prev -and $prev.consecutive_peer_failures) { $fails = [int]$prev.consecutive_peer_failures + 1 }
    }
    $mode = "down"
    if ($peerUp -and $local.up) { $mode = "linked" }
    elseif ($local.up) { if ($fails -ge $MaxFails) { $mode = "solo-local" } else { $mode = "peer-degraded" } }

    $lastChange = Get-NowIso
    if ($prev -and $prev.mode -eq $mode -and $prev.last_change_iso) { $lastChange = $prev.last_change_iso }
    $lastGossip = ""
    if ($prev -and $prev.last_gossip_iso) { $lastGossip = $prev.last_gossip_iso }

    if ($mode -eq "linked") {
        $due = $true
        if ($lastGossip) {
            try {
                $dt = [DateTime]::ParseExact($lastGossip, "yyyy-MM-ddTHH:mm:ssZ", $null).ToUniversalTime()
                $due = ((Get-Date).ToUniversalTime() - $dt).TotalSeconds -ge $GossipSec
            } catch { }
        }
        $queue = @()
        if (Test-Path $InboxDir) {
            $queue = @(Get-ChildItem $InboxDir -Filter *.md -ErrorAction SilentlyContinue |
                       Where-Object { $_.Name -notlike "gossip-*" })
        }
        if ($due) {
            New-Item -ItemType Directory -Force -Path $InboxDir | Out-Null
            @{ ts = Get-NowIso; platform = "windows"; local_model_ids = $local.models; queue_depth = $queue.Count } |
                ConvertTo-Json | Set-Content -Path (Join-Path $InboxDir "gossip-windows.json") -Encoding UTF8
            $lastGossip = Get-NowIso
        }
        foreach ($f in $queue) {
            Write-Output (@{ event = "job_available"; file = $f.Name; platform = "windows"; ts = Get-NowIso } | ConvertTo-Json -Compress)
        }
    }

    $state = [ordered]@{
        schema = 1; platform = "windows"; local_up = $local.up; peer_up = $peerUp
        peer_url = if ($purl) { $purl } else { "" }; mode = $mode
        consecutive_peer_failures = $fails; last_change_iso = $lastChange
        last_gossip_iso = $lastGossip; updated_iso = Get-NowIso
    }
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $tmp = "$StateFile.tmp"
    $state | ConvertTo-Json | Set-Content -Path $tmp -Encoding UTF8
    Move-Item -Force $tmp $StateFile
    return $state
}

if ($Status) { Load-State | ConvertTo-Json; exit 0 }
if ($Once)   { Run-Cycle (Load-State) | ConvertTo-Json; exit 0 }

$state = Load-State
while ($true) {
    try { $state = Run-Cycle $state } catch { Write-Output ("watch_error: " + $_.Exception.Message) }
    $sleep = $LoopSec
    if ($state -and $state.mode -eq "solo-local") { $sleep = $RetrySec }
    Start-Sleep -Seconds $sleep
}
