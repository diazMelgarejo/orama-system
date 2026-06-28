#Requires -Version 5.1
<#
.SYNOPSIS
    start.ps1 — orama-system Windows counterpart to start.sh  v1.1.0.0

.DESCRIPTION
    Starts the three orama services on a Windows host that runs LM Studio as the
    GPU backend.  This script is the Windows-native equivalent of start.sh and
    covers every CLI mode that start.sh exposes:

      .\start.ps1             — start all services, open browser
      .\start.ps1 --no-open   — start all, skip browser
      .\start.ps1 --stop      — kill all three services
      .\start.ps1 --status    — show port-listener status
      .\start.ps1 --discover  — re-run LAN path discovery, rewrite .paths.ps1, exit
      .\start.ps1 --hardware-policy — validate model↔hardware affinity and exit
      .\start.ps1 --lan-peer    — set LAN bind env + run peer probe after start

.NOTES
    Windows-only requirements live in this /windows folder.
    The main logic mirrors start.sh line-by-line so both files stay in sync.

    Ports:
      8000  Perpetua-Tools  (PT  — Layer 2)
      8001  orama API       (US  — Layer 3 reasoning engine)
      8002  Portal dashboard

    Service processes are launched as background Jobs (Start-Job) and their
    stdout/stderr are tee-d to .logs\<svc>.log in the repo root.

    UTF-8 fix (PowerShell defaults to system ANSI codepage on Win):
      [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
      $env:PYTHONIOENCODING = 'utf-8'
    Both are applied automatically below.
#>

[CmdletBinding()]
param(
    [switch]$NoOpen,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Discover,
    [switch]$HardwarePolicy,
    [switch]$LanPeer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── UTF-8 everywhere ──────────────────────────────────────────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8       = '1'

# ── Paths ─────────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $PSCommandPath
$RepoRoot   = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$LogDir     = Join-Path $RepoRoot '.logs'
$PathsFile  = Join-Path $RepoRoot '.paths.ps1'

# ── Logging helpers ───────────────────────────────────────────────────────────
$LogStart   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function _Log {
    param([string]$Level, [string]$Stage, [string]$Message)
    $ts      = (Get-Date).ToString('HH:mm:ss')
    $elapsed = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $LogStart
    $line    = "[$ts] $Level  [$Stage]  $Message  (+${elapsed}s)"
    Write-Host $line
    $null    = New-Item -ItemType Directory -Force -Path $LogDir
    Add-Content -Path (Join-Path $LogDir "startup-$(Get-Date -Format yyyyMMdd).log") -Value $line
}
function _Info  { _Log 'INFO ' $args[0] $args[1] }
function _Warn  { _Log 'WARN ' $args[0] $args[1] }
function _Err   { _Log 'ERROR' $args[0] $args[1] }

# ── Python detection ──────────────────────────────────────────────────────────
function Get-BestPython {
    param([string]$Dir)
    $venv = Join-Path $Dir '.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    foreach ($candidate in @('python', 'python3', 'py')) {
        try {
            $p = (Get-Command $candidate -ErrorAction SilentlyContinue)
            if ($p) { return $p.Source }
        } catch {}
    }
    throw 'Python not found. Install Python 3.10+ and add it to PATH.'
}

# ── PT directory discovery ────────────────────────────────────────────────────
function Find-PtDir {
    foreach ($root in @(
        $env:PERPETUA_TOOLS_PATH,
        $env:PT_HOME,
        $env:PERPETUA_TOOLS_ROOT,
        $env:PERPETUATOOLSROOT
    )) {
        if ($root -and (Test-Path (Join-Path $root 'orchestrator\fastapi_app.py'))) {
            return $root
        }
    }
    if ($env:OPENCLAW_HOME) {
        $ocPt = Join-Path $env:OPENCLAW_HOME 'Perpetua-Tools'
        if (Test-Path (Join-Path $ocPt 'orchestrator\fastapi_app.py')) { return $ocPt }
    }
    $candidate = Resolve-Path (Join-Path $RepoRoot '..\perplexity-api\Perpetua-Tools') -ErrorAction SilentlyContinue
    if ($candidate -and (Test-Path (Join-Path $candidate 'orchestrator\fastapi_app.py'))) {
        return $candidate.Path
    }
    # Walk siblings
    $parent = Split-Path -Parent $RepoRoot
    foreach ($d in (Get-ChildItem -Path $parent -Directory)) {
        $check = Join-Path $d.FullName 'orchestrator\fastapi_app.py'
        if (Test-Path $check) { return $d.FullName }
    }
    return $null
}

# ── Load / write .paths.ps1 ───────────────────────────────────────────────────
$PtDir     = $null
$PtPython  = $null
$UsPython  = $null

if (Test-Path $PathsFile) {
    . $PathsFile
    _Info 'path' "Loaded $PathsFile"
}

if (-not $PtDir) {
    $PtDir = Find-PtDir
    _Info 'path' "PT_DIR discovered: $PtDir"
}
if (-not $UsPython) {
    $UsPython = Get-BestPython $RepoRoot
}
if (-not $PtPython -and $PtDir) {
    $PtPython = Get-BestPython $PtDir
}

if ($Discover -or -not (Test-Path $PathsFile)) {
    @"
# .paths.ps1 — auto-generated by .\platform\windows\start.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# Edit to override. Regenerate: Remove-Item .paths.ps1; .\platform\windows\start.ps1 --discover

`$PtDir    = '$PtDir'
`$PtPython = '$PtPython'
`$UsPython = '$UsPython'
"@ | Set-Content -Path $PathsFile -Encoding UTF8
    Write-Host "  Paths written to $PathsFile"
    if ($Discover) { exit 0 }
}

# ── Port config ───────────────────────────────────────────────────────────────
$PtPort     = if ($env:PT_PORT)     { [int]$env:PT_PORT }     else { 8000 }
$UsPort     = if ($env:US_PORT)     { [int]$env:US_PORT }     else { 8001 }
$PortalPort = if ($env:PORTAL_PORT) { [int]$env:PORTAL_PORT } else { 8002 }
$PortalUrl  = "http://localhost:$PortalPort"

if ($LanPeer) {
    if (-not $env:PORTAL_BIND_LAN) { $env:PORTAL_BIND_LAN = '1' }
    if (-not $env:ORAMA_BIND_LAN)  { $env:ORAMA_BIND_LAN  = '1' }
    if (-not $env:PT_BIND_LAN)     { $env:PT_BIND_LAN     = '1' }
    _Info 'lan-peer' 'LAN bind env set (services bind 0.0.0.0 on Windows)'
}

function Sync-ControlPlaneToken {
    if ($env:ORAMA_CONTROL_PLANE_TOKEN) { return }
    if (-not $PtDir) { return }
    $tokenPath = Join-Path $PtDir '.state\control_plane_token'
    if (Test-Path $tokenPath) {
        $env:ORAMA_CONTROL_PLANE_TOKEN = (Get-Content $tokenPath -Raw).Trim()
        _Info 'lan-peer' 'ORAMA_CONTROL_PLANE_TOKEN loaded from PT .state'
    } else {
        _Warn 'lan-peer' 'No ORAMA_CONTROL_PLANE_TOKEN — portal-status probe will SKIP'
    }
}

function Invoke-LanPeerProbe {
    $probe = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py'
    if (-not (Test-Path $probe)) {
        _Warn 'lan-peer' "probe script missing: $probe"
        return
    }
    Sync-ControlPlaneToken
    if ($PtDir) { $env:PERPETUA_TOOLS_ROOT = $PtDir }
    _Info 'lan-peer' 'running probe_lan_peer.py --json ...'
    & $UsPython $probe --json
    if ($LASTEXITCODE -ne 0) {
        _Warn 'lan-peer' 'peer probe reported failures (Mac peer may need ./start.sh --lan-peer)'
    }
}

# ── Hardware policy check ─────────────────────────────────────────────────────
function Invoke-HardwarePolicyCheck {
    $cli = if ($PtDir) { Join-Path $PtDir 'scripts\hardware_policy_cli.py' } else { $null }
    if ($cli -and (Test-Path $cli)) {
        Write-Host "`n=== Hardware model affinity policy ==="
        $env:PYTHONPATH = $PtDir
        & $PtPython $cli --list
        $OcJson = Join-Path $HOME '.openclaw\openclaw.json'
        if (Test-Path $OcJson) {
            _Info 'policy' 'openclaw.json found - running --check-openclaw'
            & $PtPython $cli --check-openclaw
        } else {
            _Info 'policy' 'No openclaw.json (Hermes-only OK) - skipping --check-openclaw'
        }
        & $PtPython $cli --validate 'qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2' win
    } else {
        _Warn 'policy' "hardware_policy_cli.py not found at: $cli"
    }
}

if ($HardwarePolicy) {
    Invoke-HardwarePolicyCheck
    exit 0
}

# ── Port helpers ──────────────────────────────────────────────────────────────
function Get-PidOnPort {
    param([int]$Port)
    try {
        # netstat -ano | findstr :PORT
        $lines = & netstat -ano 2>$null | Select-String (":$($Port)\s")
        foreach ($line in $lines) {
            if ($line -match 'LISTENING\s+(\d+)') {
                return [int]$Matches[1]
            }
        }
    } catch {}
    return $null
}

function Wait-ForPort {
    param([int]$Port, [string]$Label, [int]$MaxSeconds = 75)
    Write-Host -NoNewline "  waiting for $Label (port $Port)"
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $conn = $tcp.ConnectAsync('localhost', $Port)
            if ($conn.Wait(500)) {
                $tcp.Close()
                Write-Host ' UP'
                return $true
            }
            $tcp.Close()
        } catch {}
        Write-Host -NoNewline '.'
        Start-Sleep -Milliseconds 500
    }
    $timeoutLog = Join-Path $LogDir ($Label.ToLower() + '.log')
    Write-Host " TIMEOUT - check $timeoutLog"
    return $false
}

function Open-Browser {
    param([string]$Url)
    try { Start-Process $Url } catch { _Warn 'browser' "Could not open browser: $_" }
}

# ── --stop ────────────────────────────────────────────────────────────────────
if ($Stop) {
    Write-Host 'Stopping orama-system services...'
    foreach ($port in @($PtPort, $UsPort, $PortalPort)) {
        $pid = Get-PidOnPort $port
        if ($pid) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  killed PID $pid (port $port)"
        } else {
            Write-Host "  nothing on port $port"
        }
    }
    exit 0
}

# ── --status ──────────────────────────────────────────────────────────────────
if ($Status) {
    Write-Host '── service status ────────────────────────────────────────────────────'
    foreach ($entry in @(
        @{Name='PT';     Port=$PtPort},
        @{Name='orama';  Port=$UsPort},
        @{Name='Portal'; Port=$PortalPort}
    )) {
        $pid = Get-PidOnPort $entry.Port
        if ($pid) {
            Write-Host ("  {0,-8} :{1,-5}  ● UP    (PID {2})" -f $entry.Name, $entry.Port, $pid)
        } else {
            Write-Host ("  {0,-8} :{1,-5}  ○ DOWN" -f $entry.Name, $entry.Port)
        }
    }
    Invoke-HardwarePolicyCheck
    Write-Host ''
    exit 0
}

# ── LAN discovery (optional — OpenClaw/Mac only) ────────────────────────────
# Hermes-only Windows hosts do not install OpenClaw; discover.py is absent by
# design. IP resolution below uses env vars + gateway heuristic — no hard dep.
$DiscoverScript = Join-Path $HOME '.openclaw\scripts\discover.py'
if (Test-Path $DiscoverScript) {
    _Info 'ip' 'Probing LAN topology (discover.py --force)...'
    try {
        & $UsPython $DiscoverScript --force 2>&1 | ForEach-Object { "  [discover] $_" } | Tee-Object -FilePath (Join-Path $LogDir "startup-$(Get-Date -Format yyyyMMdd).log") -Append
        _Info 'ip' 'LAN probe complete'
    } catch {
        _Warn 'ip' "discover.py failed: $_ — continuing with env/heuristic IPs"
    }
} else {
    _Info 'ip' 'No OpenClaw discover.py (Hermes-only Windows) — skipping LAN probe'
}

# ── IP resolution (Hermes-only: env vars + gateway heuristic) ─────────────────
# Priority for Mac LM Studio IP (cross-machine routing hint):
#   1. LM_STUDIO_MAC_ENDPOINT / OLLAMA_MAC_ENDPOINT env (operator override)
#   2. ~/.openclaw/openclaw.json lmstudio-mac baseUrl (legacy, if present)
#   3. Default-gateway subnet .110 heuristic
#   4. Hardcoded fallback 192.168.254.110
# Windows LM Studio is always localhost:1234 on this host — no openclaw.json needed.
$MacIp    = $null
$IpSource = 'unset'

if ($env:LM_STUDIO_MAC_ENDPOINT) {
    try { $MacIp = ([uri]$env:LM_STUDIO_MAC_ENDPOINT).Host; $IpSource = 'LM_STUDIO_MAC_ENDPOINT' } catch {}
}
if (-not $MacIp -and $env:OLLAMA_MAC_ENDPOINT) {
    try { $MacIp = ([uri]$env:OLLAMA_MAC_ENDPOINT).Host; $IpSource = 'OLLAMA_MAC_ENDPOINT' } catch {}
}

$OcJson = Join-Path $HOME '.openclaw\openclaw.json'
if (-not $MacIp -and (Test-Path $OcJson)) {
    try {
        $json = Get-Content $OcJson -Raw | ConvertFrom-Json
        $url  = $json.models.providers.'lmstudio-mac'.baseUrl
        if ($url) { $MacIp = ([uri]$url).Host; $IpSource = 'openclaw.json' }
    } catch {}
}

if (-not $MacIp) {
    try {
        $gw = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).NextHop
        $parts = $gw.Split('.')
        $MacIp = "$($parts[0]).$($parts[1]).$($parts[2]).110"
        $IpSource = 'gateway-heuristic'
    } catch {
        $MacIp = '192.168.254.110'
        $IpSource = 'fallback-constant'
    }
}
_Info 'ip' "Mac LMS endpoint: ${MacIp}:1234 (source: $IpSource)"

# ── Export env vars for child processes ───────────────────────────────────────
$env:OLLAMA_MAC_ENDPOINT       = if ($env:OLLAMA_MAC_ENDPOINT)       { $env:OLLAMA_MAC_ENDPOINT }       else { "http://${MacIp}:11434" }
$env:OLLAMA_WINDOWS_ENDPOINT   = if ($env:OLLAMA_WINDOWS_ENDPOINT)   { $env:OLLAMA_WINDOWS_ENDPOINT }   else { 'http://localhost:11434' }
$env:LM_STUDIO_MAC_ENDPOINT    = if ($env:LM_STUDIO_MAC_ENDPOINT)    { $env:LM_STUDIO_MAC_ENDPOINT }    else { "http://${MacIp}:1234" }
$env:LM_STUDIO_WIN_ENDPOINTS   = if ($env:LM_STUDIO_WIN_ENDPOINTS)   { $env:LM_STUDIO_WIN_ENDPOINTS }   else { 'http://localhost:1234' }
$env:WIN_LM_STUDIO_HOST        = if ($env:WIN_LM_STUDIO_HOST)        { $env:WIN_LM_STUDIO_HOST }        else { 'localhost' }
$env:WINDOWS_IP                = 'localhost'

_Info 'env' 'Endpoints exported'

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '╔══════════════════════════════════════════════════════════════════╗'
Write-Host '║  orama-system  v1.1.0.0  (Windows)                              ║'
Write-Host '║  ὅραμα — vision/revelation · Layer 3 orchestration/meta-intel   ║'
Write-Host '╠══════════════════════════════════════════════════════════════════╣'
Write-Host ("║  Mac  {0,-9}  LM Studio expected on port 1234              ║" -f ($MacIp + ':'))
Write-Host ("║  Win  localhost   LM Studio on port 1234 (this machine)        ║")
Write-Host ('╠══════════════════════════════════════════════════════════════════╣')
Write-Host ("║  PT   port $PtPort     orama port $UsPort     Portal port $PortalPort                      ║")
Write-Host '╚══════════════════════════════════════════════════════════════════╝'
Write-Host ''

# ── Helper: start a service as a background process ───────────────────────────
function Start-Service {
    param(
        [string]$Name,
        [int]$Port,
        [string]$WorkDir,
        [string[]]$Cmd,
        [hashtable]$EnvExtra = @{}
    )
    if (Get-PidOnPort $Port) {
        Write-Host "  $Name  port $Port already running"
        return
    }
    $logFile = Join-Path $LogDir "$($Name.ToLower()).log"
    $null    = New-Item -ItemType Directory -Force -Path $LogDir
    Write-Host "  $Name  starting → $logFile"

    # Build environment block
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $Cmd[0]
    $psi.Arguments              = ($Cmd[1..($Cmd.Length-1)] | ForEach-Object { "`"$_`"" }) -join ' '
    $psi.WorkingDirectory       = $WorkDir
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true
    foreach ($kv in $EnvExtra.GetEnumerator()) {
        $psi.EnvironmentVariables[$kv.Key] = $kv.Value
    }
    # Inherit parent env
    foreach ($kv in [System.Environment]::GetEnvironmentVariables('Process').GetEnumerator()) {
        if (-not $psi.EnvironmentVariables.Contains($kv.Key)) {
            $psi.EnvironmentVariables[$kv.Key] = $kv.Value
        }
    }

    $proc = [System.Diagnostics.Process]::Start($psi)
    # Async tee stdout+stderr to log
    $null = $proc.StandardOutput.BaseStream.CopyToAsync(
        [System.IO.File]::Open($logFile, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
    )
    $null = $proc.StandardError.BaseStream.CopyToAsync(
        [System.IO.File]::Open($logFile, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
    )
}

# ── 1. Perpetua-Tools ─────────────────────────────────────────────────────────
if ($PtDir -and (Test-Path (Join-Path $PtDir 'orchestrator\fastapi_app.py'))) {
    Start-Service -Name 'PT' -Port $PtPort -WorkDir $PtDir `
        -Cmd @($PtPython, '-m', 'uvicorn', 'orchestrator.fastapi_app:app',
               '--host', '0.0.0.0', '--port', $PtPort.ToString()) `
        -EnvExtra @{ PYTHONPATH = $PtDir }
    $null = Wait-ForPort $PtPort 'PT'
} else {
    Write-Host "  PT   skipped (not found at: $PtDir)"
}

# ── 2. orama reasoning engine ─────────────────────────────────────────────────
Start-Service -Name 'orama' -Port $UsPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'api_server:app',
           '--host', '0.0.0.0', '--port', $UsPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $RepoRoot }
$null = Wait-ForPort $UsPort 'orama'

# ── 3. Portal ─────────────────────────────────────────────────────────────────
Start-Service -Name 'Portal' -Port $PortalPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'portal_server:app',
           '--host', '0.0.0.0', '--port', $PortalPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $RepoRoot }
$null = Wait-ForPort $PortalPort 'Portal'

# ── Ready ─────────────────────────────────────────────────────────────────────
Write-Host '── services ready ────────────────────────────────────────────────────'
Write-Host ("  ●  PT      http://localhost:{0}/health" -f $PtPort)
Write-Host ("  ●  orama   http://localhost:{0}/health" -f $UsPort)
Write-Host ("  ●  Portal  {0}" -f $PortalUrl)
Write-Host ("  ○  JSON    {0}/api/status" -f $PortalUrl)
Write-Host ''
Write-Host ("  Logs  : {0}\" -f $LogDir)
Write-Host '  Stop  : .\platform\windows\start.ps1 --stop'
Write-Host '  LAN   : .\platform\windows\start.ps1 --lan-peer'
Write-Host '────────────────────────────────────────────────────────────────────'
Write-Host ''

if ($LanPeer) {
    Invoke-LanPeerProbe
}

if (-not $NoOpen) {
    Open-Browser $PortalUrl
}
