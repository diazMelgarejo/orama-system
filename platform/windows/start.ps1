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

#Requires -Version 5.1
# All CLI flags parsed from $args for start.sh parity (--no-open, --stop, etc.).
# PowerShell switch params do not accept --kebab-case; $PID is read-only — avoid $pid.
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NoOpen = $false
$Stop = $false
$Status = $false
$Discover = $false
$HardwarePolicy = $false
$LanPeer = $false

foreach ($a in $args) {
    switch ($a) {
        '--no-open'          { $NoOpen = $true }
        '-NoOpen'            { $NoOpen = $true }
        '--stop'             { $Stop = $true }
        '-Stop'              { $Stop = $true }
        '--status'           { $Status = $true }
        '-Status'            { $Status = $true }
        '--discover'         { $Discover = $true }
        '-Discover'          { $Discover = $true }
        '--hardware-policy'  { $HardwarePolicy = $true }
        '-HardwarePolicy'    { $HardwarePolicy = $true }
        '--lan-peer'         { $LanPeer = $true }
        '-LanPeer'           { $LanPeer = $true }
        default { throw "Unknown argument: $a. Supported: --no-open --stop --status --discover --hardware-policy --lan-peer" }
    }
}

# ── UTF-8 everywhere ──────────────────────────────────────────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8       = '1'

# ── Paths ─────────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $PSCommandPath
$RepoRoot   = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$LogDir     = Join-Path $RepoRoot '.logs'
$PathsFile  = Join-Path $RepoRoot '.paths.ps1'

# Gitignored env (.env → .env.local) before bind/token reads
$LoadLocalPs1 = Join-Path $RepoRoot 'scripts\env\load-local.ps1'
if (Test-Path $LoadLocalPs1) {
    & $LoadLocalPs1 -RepoRoot $RepoRoot
}

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

function Get-BindHost {
    param([string]$LanEnv, [string]$HostEnv, [string]$Default = '127.0.0.1')
    $lan = [Environment]::GetEnvironmentVariable($LanEnv, 'Process')
    if ($lan -and $lan.Trim().ToLower() -in @('1', 'true', 'yes')) {
        return '0.0.0.0'
    }
    $hostVal = [Environment]::GetEnvironmentVariable($HostEnv, 'Process')
    if ($hostVal -and $hostVal.Trim()) { return $hostVal.Trim() }
    return $Default
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

$PtHost     = Get-BindHost 'PT_BIND_LAN' 'PT_HOST'
$UsHost     = Get-BindHost 'ORAMA_BIND_LAN' 'ORAMASYS_HOST'
$PortalHost = Get-BindHost 'PORTAL_BIND_LAN' 'PORTAL_HOST'

function Sync-ControlPlaneToken {
    if ($env:ORAMA_CONTROL_PLANE_TOKEN -and $env:ORAMA_CONTROL_PLANE_TOKEN -notmatch '^<') { return }
    if (-not $PtDir) { return }
    $tokenPath = Join-Path $PtDir '.state\control_plane_token'
    $stateDir = Split-Path $tokenPath -Parent
    if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Force -Path $stateDir | Out-Null }
    if (Test-Path $tokenPath) {
        $existing = (Get-Content $tokenPath -Raw).Trim()
        if ($existing) {
            $env:ORAMA_CONTROL_PLANE_TOKEN = $existing
            _Info 'lan-peer' 'ORAMA_CONTROL_PLANE_TOKEN loaded from PT .state'
            return
        }
    }
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $generated = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
    Set-Content -Path $tokenPath -Value $generated -NoNewline -Encoding UTF8
    $env:ORAMA_CONTROL_PLANE_TOKEN = $generated
    _Warn 'lan-peer' 'Generated ORAMA_CONTROL_PLANE_TOKEN — copy PT/.state/control_plane_token to Mac .env.local'
}

function Test-LanBindConfigured {
    foreach ($name in @('PORTAL_BIND_LAN', 'ORAMA_BIND_LAN', 'PT_BIND_LAN')) {
        $value = (Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue).Value
        if ($value -match '^(1|true|yes)$') { return $true }
    }
    return $false
}

if ($LanPeer -or (Test-LanBindConfigured)) {
    Sync-ControlPlaneToken
    $weak = @('', 'change-me-before-network-use', 'changeme', 'change-me', 'placeholder', 'test', 'secret')
    $tokenVal = $env:ORAMA_CONTROL_PLANE_TOKEN
    if ($null -eq $tokenVal) { $tokenVal = '' }
    if ($weak -contains $tokenVal.Trim().ToLower()) {
        Write-Error 'LAN bind requires a strong ORAMA_CONTROL_PLANE_TOKEN (set in .env.local or generated in PT/.state/control_plane_token)'
        exit 1
    }
}

function Invoke-LanPeerProbe {
    $probe = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py'
    if (-not (Test-Path $probe)) {
        _Warn 'lan-peer' "probe script missing: $probe"
        return $false
    }
    Sync-ControlPlaneToken
    if ($PtDir) { $env:PERPETUA_TOOLS_ROOT = $PtDir }
    _Info 'lan-peer' 'running probe_lan_peer.py --json ...'
    $probeTimeout = if ($env:LAN_PEER_PROBE_TIMEOUT) { $env:LAN_PEER_PROBE_TIMEOUT } else { '2' }
    $statusTimeout = if ($env:LAN_PEER_STATUS_TIMEOUT) { $env:LAN_PEER_STATUS_TIMEOUT } else { '3' }
    $wsTimeout = if ($env:LAN_PEER_WS_TIMEOUT) { $env:LAN_PEER_WS_TIMEOUT } else { '2' }
    & $UsPython $probe --json --timeout $probeTimeout --status-timeout $statusTimeout --ws-timeout $wsTimeout
    if ($LASTEXITCODE -ne 0) {
        _Warn 'lan-peer' 'peer probe reported failures (Mac peer may need ./start.sh --lan-peer)'
        return $false
    }
    return $true
}

function Invoke-LanPeerOutboxFlush {
    $assign = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py'
    if (-not (Test-Path $assign)) {
        _Warn 'lan-peer' "assignment script missing: $assign"
        return
    }
    Sync-ControlPlaneToken
    if ($PtDir) { $env:PERPETUA_TOOLS_ROOT = $PtDir }
    _Info 'lan-peer' 'flushing queued peer drops ...'
    $httpTimeout = if ($env:LAN_PEER_HTTP_TIMEOUT) { $env:LAN_PEER_HTTP_TIMEOUT } else { '2' }
    & $UsPython $assign flush-outbox --peer --timeout $httpTimeout
    if ($LASTEXITCODE -ne 0) {
        _Warn 'lan-peer' 'queued peer drops remain pending'
    }
}

function Invoke-LanPeerSession {
    param([string[]]$Args)
    $session = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\lan_peer_session.py'
    if (-not (Test-Path $session)) {
        _Warn 'lan-peer' "session state script missing: $session"
        return $true
    }
    & $UsPython $session @Args | Out-Null
    return ($LASTEXITCODE -eq 0)
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
        $listenerPid = Get-PidOnPort $port
        if ($listenerPid) {
            Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
            Write-Host "  killed PID $listenerPid (port $port)"
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
        $listenerPid = Get-PidOnPort $entry.Port
        if ($listenerPid) {
            Write-Host ("  {0,-8} :{1,-5}  ● UP    (PID {2})" -f $entry.Name, $entry.Port, $listenerPid)
        } else {
            Write-Host ("  {0,-8} :{1,-5}  ○ DOWN" -f $entry.Name, $entry.Port)
        }
    }
    Invoke-HardwarePolicyCheck
    Write-Host ''
    exit 0
}

# ── LAN discovery (always fresh before IP resolution) ─────────────────────────
function Invoke-DiscoverEndpoints {
    $scripts = @(
        (Join-Path $RepoRoot 'scripts\discover.py'),
        (Join-Path $HOME '.openclaw\scripts\discover.py')
    )
    $discover = $scripts | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $discover) {
        _Warn 'ip' 'discover.py not found — skipping live LAN probe'
        return
    }
    if ($PtDir) {
        $env:PERPETUA_TOOLS_ROOT = $PtDir
        $env:PERPETUA_TOOLS_PATH = $PtDir
    }
    _Info 'ip' "Probing LAN topology ($([IO.Path]::GetFileName($discover)) --force)..."
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $discoverOutput = & $UsPython $discover --force 2>&1
    $discoverExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    $discoverOutput | ForEach-Object { "  [discover] $_" } |
        Tee-Object -FilePath (Join-Path $LogDir "startup-$(Get-Date -Format yyyyMMdd).log") -Append
    if ($discoverExit -ne 0) {
        _Warn 'ip' "discover.py exited $discoverExit — continuing with discovery state / env"
    } else {
        _Info 'ip' 'LAN probe complete'
    }
}

function Resolve-MacLanIp {
    # Priority: operator env → fresh last_discovery.json → openclaw.json (legacy)
    # Never use gateway .110 heuristic or hardcoded fallbacks.
    $macIp = $null
    $source = 'unset'

    foreach ($var in @('MAC_IP', 'LM_STUDIO_MAC_ENDPOINT', 'OLLAMA_MAC_ENDPOINT')) {
        $raw = [Environment]::GetEnvironmentVariable($var, 'Process')
        if (-not $raw) { continue }
        if ($var -eq 'MAC_IP') {
            $macIp = $raw.Trim()
        } else {
            try { $macIp = ([uri]$raw.Trim()).Host } catch { continue }
        }
        if ($macIp -and $macIp -notin @('localhost', '127.0.0.1')) {
            $source = $var
            break
        }
        $macIp = $null
    }

    if (-not $macIp) {
        $statePath = Join-Path $HOME '.openclaw\state\last_discovery.json'
        if (Test-Path $statePath) {
            try {
                $state = Get-Content $statePath -Raw | ConvertFrom-Json
                $candidate = $state.endpoints.mac.ip
                if ($candidate -and $candidate -notin @('', 'localhost', '127.0.0.1')) {
                    $macIp = $candidate
                    $source = 'last_discovery.json'
                }
            } catch {}
        }
    }

    if (-not $macIp) {
        $OcJson = Join-Path $HOME '.openclaw\openclaw.json'
        if (Test-Path $OcJson) {
            try {
                $json = Get-Content $OcJson -Raw | ConvertFrom-Json
                $url  = $json.models.providers.'lmstudio-mac'.baseUrl
                if ($url) {
                    $hostFromUrl = ([uri]$url).Host
                    if ($hostFromUrl -notin @('', 'localhost', '127.0.0.1')) {
                        $macIp = $hostFromUrl
                        $source = 'openclaw.json'
                    }
                }
            } catch {}
        }
    }

    if (-not $macIp) {
        _Warn 'ip' 'Mac LAN IP unknown — run discover.py --force or set MAC_IP (no stale .110 fallback)'
        $macIp = 'unresolved'
        $source = 'none'
    }

    return @{ Ip = $macIp; Source = $source }
}

Invoke-DiscoverEndpoints
$MacResolved = Resolve-MacLanIp
$MacIp    = $MacResolved.Ip
$IpSource = $MacResolved.Source

# ── Export env vars for child processes ───────────────────────────────────────
if ($MacIp -and $MacIp -notin @('unresolved', 'localhost', '127.0.0.1')) {
    $env:MAC_IP = $MacIp
}
$env:WIN_IP = if ($env:WIN_IP) { $env:WIN_IP } else {
    try {
        $s = New-Object System.Net.Sockets.Socket([System.Net.Sockets.AddressFamily]::InterNetwork, [System.Net.Sockets.SocketType]::Dgram, [System.Net.Sockets.ProtocolType]::Udp)
        $s.Connect('192.168.254.1', 80)
        ($s.LocalEndPoint).Address.ToString()
    } catch { 'localhost' }
}
$env:OLLAMA_MAC_ENDPOINT       = if ($env:OLLAMA_MAC_ENDPOINT)       { $env:OLLAMA_MAC_ENDPOINT }       elseif ($MacIp -notin @('unresolved','localhost','127.0.0.1')) { "http://${MacIp}:11434" } else { 'http://localhost:11434' }
$env:OLLAMA_WINDOWS_ENDPOINT   = if ($env:OLLAMA_WINDOWS_ENDPOINT)   { $env:OLLAMA_WINDOWS_ENDPOINT }   else { 'http://localhost:11434' }
$env:LM_STUDIO_MAC_ENDPOINT    = if ($env:LM_STUDIO_MAC_ENDPOINT)    { $env:LM_STUDIO_MAC_ENDPOINT }    elseif ($MacIp -notin @('unresolved','localhost','127.0.0.1')) { "http://${MacIp}:1234" } else { 'http://localhost:1234' }
$env:LM_STUDIO_WIN_ENDPOINTS   = if ($env:LM_STUDIO_WIN_ENDPOINTS)   { $env:LM_STUDIO_WIN_ENDPOINTS }   else { "http://$($env:WIN_IP):1234" }
$env:WIN_LM_STUDIO_HOST        = if ($env:WIN_LM_STUDIO_HOST)        { $env:WIN_LM_STUDIO_HOST }        else { 'localhost' }
$env:WINDOWS_IP                = $env:WIN_IP

_Info 'ip' "Mac LMS endpoint: ${MacIp}:1234 (source: $IpSource)"

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
        if (-not $psi.EnvironmentVariables.ContainsKey($kv.Key)) {
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
               '--host', $PtHost, '--port', $PtPort.ToString()) `
        -EnvExtra @{ PYTHONPATH = "$PtDir\src;$PtDir" }
    $null = Wait-ForPort $PtPort 'PT'
} else {
    Write-Host "  PT   skipped (not found at: $PtDir)"
}

# ── 2. orama reasoning engine ─────────────────────────────────────────────────
$oramaPyPath = "$RepoRoot\src;$RepoRoot"
Start-Service -Name 'orama' -Port $UsPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'orama_system.api_server:app',
           '--host', $UsHost, '--port', $UsPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $oramaPyPath }
$null = Wait-ForPort $UsPort 'orama'

# ── 3. Portal ─────────────────────────────────────────────────────────────────
Start-Service -Name 'Portal' -Port $PortalPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'orama_system.portal_server:app',
           '--host', $PortalHost, '--port', $PortalPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $oramaPyPath }
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
    $retrySeconds = if ($env:LAN_PEER_DEGRADED_RETRY_SECONDS) { $env:LAN_PEER_DEGRADED_RETRY_SECONDS } else { '900' }
    if (-not (Invoke-LanPeerSession -Args @('should-retry'))) {
        _Warn 'lan-peer' "macOS-only degraded mode active; next peer retry waits for LAN_PEER_DEGRADED_RETRY_SECONDS=$retrySeconds"
    } elseif (Invoke-LanPeerProbe) {
        $null = Invoke-LanPeerSession -Args @('record-success')
        Invoke-LanPeerOutboxFlush
    } else {
        $null = Invoke-LanPeerSession -Args @('record-failure', '--error', 'probe_lan_peer.py failed')
        _Warn 'lan-peer' 'skipping outbox flush until peer portal probe passes'
    }
}

if (-not $NoOpen) {
    Open-Browser $PortalUrl
}
