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
      .\start.ps1 --list      — show resolved read-only configuration
      .\start.ps1 --validate  — validate launcher argument handling without setup
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

    Service processes are launched detached (scripts\lib\spawn_detached.py), so
    they keep running after this script exits. stdout/stderr are appended to
    .logs\<svc>.log and the PID to .logs\<svc>.pid in the repo root.

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
$FleetStatus = $false
$FleetStatusFormat = 'text'
$Discover = $false
$HardwarePolicy = $false
$LanPeer = $false
$RestartPortal = $false
$ValidateOnly = $false
$ListOnly = $false
$ListIncludeNetwork = $false

function Show-Usage {
    @"
Usage: .\platform\windows\start.ps1 [options]

Options:
  --no-open              Start services without opening the Portal browser.
  --stop                 Stop PT, orama, and Portal services.
  --status               Show service status and hardware policy.
  --list                 Show resolved configuration without setup or probes.
  --include-network      Reveal non-loopback hosts in --list output.
  --fleet-status[=text]  Show current fleet topology and exit.
  --fleet-status=json    Show current fleet topology as JSON and exit.
  --discover             Re-run LAN path discovery, rewrite .paths.ps1, and exit.
  --hardware-policy      Validate model/hardware affinity and exit.
  --validate             Validate launcher arguments without environment, bootstrap,
                         discovery, or service startup.
  --lan-peer             LAN-bind services and probe the peer after startup.
  --restart-portal       Restart only Portal and its TLS proxy; PT and orama keep running.
  --help, -h             Show this help.
"@ | Write-Host
}

function Get-ListPathsValue {
    param([string]$PathsFile, [string]$VariableName)
    if (-not (Test-Path $PathsFile)) { return $null }
    $pattern = '^\s*\${0}\s*=\s*[''"](?<value>.*?)[''"]\s*$' -f [regex]::Escape($VariableName)
    foreach ($line in Get-Content -LiteralPath $PathsFile) {
        if ($line -match $pattern) { return $Matches['value'] }
    }
    return $null
}

function Get-ListConfigValue {
    param([string]$PathsFile, [string]$PathsVariable, [string[]]$EnvironmentNames, [string]$DefaultValue)
    $fromPaths = Get-ListPathsValue -PathsFile $PathsFile -VariableName $PathsVariable
    if ($fromPaths) { return @{ Value = $fromPaths; Source = '.paths.ps1' } }
    foreach ($name in $EnvironmentNames) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($value) { return @{ Value = $value; Source = "environment:$name" } }
    }
    return @{ Value = $DefaultValue; Source = 'default' }
}

function Get-ListResolvedHost {
    param([string]$LanEnvironment, [string[]]$HostEnvironments, [string]$DefaultHost)
    $lan = [Environment]::GetEnvironmentVariable($LanEnvironment, 'Process')
    if ($lan -and $lan.Trim().ToLower() -in @('1', 'true', 'yes')) { return '0.0.0.0' }
    foreach ($name in $HostEnvironments) {
        $hostValue = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($hostValue -and $hostValue.Trim()) { return $hostValue.Trim() }
    }
    return $DefaultHost
}

function Get-ListEnvironmentOrDefault {
    param([string]$Name, [string]$DefaultValue)
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($value) { return $value }
    return $DefaultValue
}

function Format-ListHost {
    param([string]$ResolvedHost, [bool]$IncludeNetwork)
    if ($ResolvedHost -in @('localhost', '127.0.0.1', '::1')) { return "$ResolvedHost (loopback)" }
    if ($ResolvedHost -eq '0.0.0.0' -and $IncludeNetwork) { return '0.0.0.0 (all interfaces)' }
    if ($IncludeNetwork) { return $ResolvedHost }
    return '<redacted; pass --include-network>'
}

function Show-ReadOnlyConfiguration {
    param([bool]$IncludeNetwork)
    $scriptDir = Split-Path -Parent $PSCommandPath
    $repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
    $pathsFile = Join-Path $repoRoot '.paths.ps1'
    $ptDir = Get-ListConfigValue -PathsFile $pathsFile -PathsVariable 'PtDir' -EnvironmentNames @('PERPETUA_TOOLS_PATH', 'PT_HOME', 'PERPETUA_TOOLS_ROOT', 'PERPETUATOOLSROOT') -DefaultValue '<unresolved>'
    $ptPython = Get-ListConfigValue -PathsFile $pathsFile -PathsVariable 'PtPython' -EnvironmentNames @('PT_PYTHON') -DefaultValue '<unresolved>'
    $usPython = Get-ListConfigValue -PathsFile $pathsFile -PathsVariable 'UsPython' -EnvironmentNames @('US_PYTHON') -DefaultValue '<unresolved>'
    $ptPort = Get-ListEnvironmentOrDefault -Name 'PT_PORT' -DefaultValue '8000'
    $usPort = Get-ListEnvironmentOrDefault -Name 'US_PORT' -DefaultValue '8001'
    $portalPort = Get-ListEnvironmentOrDefault -Name 'PORTAL_PORT' -DefaultValue '8002'
    $ptHost = Get-ListResolvedHost -LanEnvironment 'PT_BIND_LAN' -HostEnvironments @('PT_HOST') -DefaultHost '127.0.0.1'
    $usHost = Get-ListResolvedHost -LanEnvironment 'ORAMA_BIND_LAN' -HostEnvironments @('ORAMASYS_HOST') -DefaultHost '127.0.0.1'
    $portalHost = Get-ListResolvedHost -LanEnvironment 'PORTAL_BIND_LAN' -HostEnvironments @('PORTAL_HOST') -DefaultHost '127.0.0.1'
    $token = [Environment]::GetEnvironmentVariable('ORAMA_CONTROL_PLANE_TOKEN', 'Process')

    Write-Host 'Launcher configuration (read-only; no environment loading, bootstrap, discovery, probes, or services)'
    Write-Host ("  {0,-20} {1}" -f 'SCRIPT_DIR', $scriptDir)
    Write-Host ("  {0,-20} {1}" -f 'PATHS_FILE', $(if (Test-Path $pathsFile) { 'present' } else { 'absent' }))
    Write-Host ("  {0,-20} {1} ({2})" -f 'PT_DIR', $ptDir.Value, $ptDir.Source)
    Write-Host ("  {0,-20} {1} ({2})" -f 'PT_PYTHON', $ptPython.Value, $ptPython.Source)
    Write-Host ("  {0,-20} {1} ({2})" -f 'US_PYTHON', $usPython.Value, $usPython.Source)
    Write-Host ("  {0,-20} {1}" -f 'PT_PORT', $ptPort)
    Write-Host ("  {0,-20} {1}" -f 'US_PORT', $usPort)
    Write-Host ("  {0,-20} {1}" -f 'PORTAL_PORT', $portalPort)
    Write-Host ("  {0,-20} {1}" -f 'PT_HOST', (Format-ListHost -ResolvedHost $ptHost -IncludeNetwork $IncludeNetwork))
    Write-Host ("  {0,-20} {1}" -f 'US_HOST', (Format-ListHost -ResolvedHost $usHost -IncludeNetwork $IncludeNetwork))
    Write-Host ("  {0,-20} {1}" -f 'PORTAL_HOST', (Format-ListHost -ResolvedHost $portalHost -IncludeNetwork $IncludeNetwork))
    Write-Host ("  {0,-20} {1}" -f 'CONTROL_PLANE_TOKEN', $(if ($token) { 'configured' } else { 'not configured' }))
}

foreach ($a in $args) {
    switch -Regex ($a) {
        '^--no-open$|^-NoOpen$'        { $NoOpen = $true }
        '^--stop$|^-Stop$'             { $Stop = $true }
        '^--status$|^-Status$'         { $Status = $true }
        '^--list$|^-List$'             { $ListOnly = $true }
        '^--include-network$'          { $ListIncludeNetwork = $true }
        '^--fleet-status$|^-FleetStatus$' { $FleetStatus = $true; $FleetStatusFormat = 'text' }
        '^--fleet-status=json$|^-FleetStatus=json$' { $FleetStatus = $true; $FleetStatusFormat = 'json' }
        '^--fleet-status=text$|^-FleetStatus=text$' { $FleetStatus = $true; $FleetStatusFormat = 'text' }
        '^--discover$|^-Discover$'     { $Discover = $true }
        '^--hardware-policy$|^-HardwarePolicy$' { $HardwarePolicy = $true }
        '^--validate$|^-Validate$'     { $ValidateOnly = $true }
        '^--lan-peer$|^-LanPeer$'      { $LanPeer = $true }
        '^--restart-portal$|^-RestartPortal$' { $RestartPortal = $true }
        '^--help$|^-h$|^-Help$'        { Show-Usage; exit 0 }
        default { throw "Unknown argument: $a. Supported: --no-open --stop --status --fleet-status[=text|json] --discover --hardware-policy --validate --lan-peer --help" }
    }
}

if ($ListIncludeNetwork -and -not $ListOnly) {
    throw '--include-network is only valid with --list.'
}
if ($ListOnly -and ($NoOpen -or $Stop -or $Status -or $FleetStatus -or $Discover -or $HardwarePolicy -or $LanPeer -or $RestartPortal)) {
    throw '--list cannot be combined with lifecycle or probe modes.'
}
if ($ValidateOnly -and ($ListOnly -or $ListIncludeNetwork -or $NoOpen -or $Stop -or $Status -or $FleetStatus -or $Discover -or $HardwarePolicy -or $LanPeer -or $RestartPortal)) {
    throw '--validate cannot be combined with another launcher mode.'
}
if ($RestartPortal -and ($Stop -or $Status -or $FleetStatus -or $Discover -or $HardwarePolicy -or $LanPeer)) {
    throw '--restart-portal cannot be combined with another lifecycle or probe mode.'
}

if ($ValidateOnly) {
    Write-Host 'Launcher validation passed: arguments parsed; no environment, bootstrap, discovery, or services started.'
    exit 0
}

if ($ListOnly) {
    Show-ReadOnlyConfiguration -IncludeNetwork $ListIncludeNetwork
    exit 0
}

# F23: modes that must never install, repair venvs, or write secrets/tokens.
# --discover is deliberately NOT here: it must (re)write .paths.ps1.
$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)

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

# GLM-5.2 Ultimate Fallback — available when all other pathways are blocked
$Glm52EnvFile = Join-Path $env:USERPROFILE '.openclaw\.env.glm52'
$Glm52Available = $false
if (Test-Path $Glm52EnvFile) {
    # Source environment variables from GLM-5.2 setup (Windows-compatible)
    $content = Get-Content $Glm52EnvFile -Raw
    $content -split "`n" | Where-Object { $_ -match '^\s*export\s+(\w+)=' } | ForEach-Object {
        if ($_ -match 'export\s+(\w+)=(.+)$') {
            $key = $Matches[1]
            $value = $Matches[2].Trim('"').Trim("'")
            if ($value -match '\$\(.*\)') {
                # Has shell substitution — skip for now
            } else {
                Set-Item -Path "env:$key" -Value $value -ErrorAction SilentlyContinue
            }
        }
    }
    if ($env:GLM52_API_KEY) {
        $Glm52Available = $true
    }
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

# ── Bootstrap helpers (venv probe / pip under a safe error policy) ────────────
# pip writes '[notice] new release available' to stderr; under
# $ErrorActionPreference='Stop' PowerShell 5.1 turns that into a terminating
# NativeCommandError whenever output is captured. Run native Python calls under
# 'Continue' and judge success by $LASTEXITCODE only. Single quotes inside
# python -c: PS 5.1 mangles embedded double quotes.
$script:BootstrapOutput = @()
function Bootstrap-RunPython {
    <#
    .SYNOPSIS
    Run a Python command during bootstrap, capturing output for later display.
    #>
    param([string]$Python, [string[]]$PyArgs)
    if (-not (Test-Path $Python)) {
        $script:BootstrapOutput = @("interpreter not found: $Python")
        return 127
    }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Python @PyArgs 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    $script:BootstrapOutput = @($out | ForEach-Object { "$_" })
    return $code
}

function Bootstrap-TestImports {
    <#
    .SYNOPSIS
    Return $true when the given Python can import the modules in -Code.
    #>
    param([string]$Python, [string]$Code)
    if (-not (Test-Path $Python)) { return $false }
    # -I (isolated): ignore PYTHONPATH/user site left in the console by earlier
    # runs so they can neither satisfy nor break the probe.
    return ((Bootstrap-RunPython $Python @('-I', '-c', $Code)) -eq 0)
}

# The launcher (not the caller) resolved the PT directory: set the env vars and
# record them in the load-local.ps1 markers so a later run in the same console
# does not mistake them for a caller override.
function Set-LauncherPtEnv {
    <#
    .SYNOPSIS
    Point PERPETUA_TOOLS_ROOT (and optionally legacy vars) at the resolved PT checkout.
    #>
    param([string]$Dir, [switch]$RootOnly)
    $env:PERPETUA_TOOLS_ROOT = $Dir
    $env:ORAMA_LOADLOCAL_SET_PERPETUA_TOOLS_ROOT = $Dir
    if (-not $RootOnly) {
        $env:PERPETUA_TOOLS_PATH = $Dir
        $env:ORAMA_LOADLOCAL_SET_PERPETUA_TOOLS_PATH = $Dir
    }
}

function Bootstrap-ShowOutput {
    <#
    .SYNOPSIS
    Print the last captured bootstrap output lines to the host.
    #>
    foreach ($l in ($script:BootstrapOutput | Select-Object -Last 25)) { Write-Host "    $l" }
}

$OramaImportProbe = 'import uvicorn, fastapi, httpx'
$PtImportProbe = "import importlib.metadata as m, sys; m.version('perpetua-tools'); import requests, uvicorn; sys.exit(1 if any(((d.metadata['Name'] or '').lower().replace('_', '-') == 'orama-system') for d in m.distributions()) else 0)"

function Heal-PtVenv {
    <#
    .SYNOPSIS
    Repair the Perpetua-Tools virtual environment when imports fail.
    #>
    param([string]$PtDir)
    $venvDir = Join-Path $PtDir '.venv'
    $venvPy  = Join-Path $venvDir 'Scripts\python.exe'
    if (Bootstrap-TestImports $venvPy $PtImportProbe) { return }
    $hasPyproject = Test-Path (Join-Path $PtDir 'pyproject.toml')
    $hasReqs      = Test-Path (Join-Path $PtDir 'requirements.txt')
    if (-not ($hasPyproject -or $hasReqs)) {
        _Warn 'bootstrap' "PT has neither pyproject.toml nor requirements.txt in $PtDir — PT service will likely fail to start"
        return
    }
    if (Test-Path $venvPy) {
        _Info 'bootstrap' "PT .venv at $venvDir lacks perpetua-tools/requests/uvicorn (or holds a stray orama-system) — repairing ..."
    } else {
        _Info 'bootstrap' "PT .venv not found — creating one at $venvDir ..."
        $bootstrapPy = Get-BestPython $RepoRoot
        $code = Bootstrap-RunPython $bootstrapPy @('-m', 'venv', $venvDir)
        if ($code -ne 0) {
            Bootstrap-ShowOutput
            _Err 'bootstrap' "creating PT .venv failed (exit $code)"
            exit 1
        }
    }
    # A previous launcher run installed orama-system here (pip -r ran from the
    # wrong cwd); remove it so the venv holds the right package only.
    $null = Bootstrap-RunPython $venvPy @('-m', 'pip', 'uninstall', '-y', 'orama-system', '--disable-pip-version-check')
    # The stray package alone may have been the only problem: re-probe and skip
    # the (network-dependent) reinstall when the venv is already usable.
    if (Bootstrap-TestImports $venvPy $PtImportProbe) {
        _Info 'bootstrap' 'PT .venv ready (removed stray orama-system)'
        return
    }
    # PT's requirements.txt is '-e .', which pip resolves against the CURRENT
    # directory, so the install must run with PtDir as cwd.
    Push-Location $PtDir
    try {
        if ($hasPyproject) {
            $code = Bootstrap-RunPython $venvPy @('-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-e', '.')
        } else {
            $code = Bootstrap-RunPython $venvPy @('-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-r', 'requirements.txt')
        }
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Bootstrap-ShowOutput
        _Err 'bootstrap' "PT dependency install failed (pip exit $code) in $PtDir"
        exit 1
    }
    if (-not (Bootstrap-TestImports $venvPy $PtImportProbe)) {
        _Err 'bootstrap' "PT .venv still unusable after install (perpetua-tools / requests / uvicorn probe failed) at $venvDir"
        exit 1
    }
    _Info 'bootstrap' 'PT .venv ready'
}

# ── Fresh-install bootstrap ────────────────────────────────────────────────────
# On a brand-new clone, .venv doesn't exist yet and Get-BestPython below throws
# "Python not found" — the operator has to already know to run install.ps1
# first. Detect that and run it automatically. Idempotent: install.ps1 itself
# no-ops (venv/deps already present, LM Studio port already OK) once bootstrap
# has run, so this check + call is cheap and safe on every subsequent
# start.ps1 invocation — the Test-Path guard just skips the call entirely once
# .venv exists.
$VenvPythonMarker = Join-Path $RepoRoot '.venv\Scripts\python.exe'
# F2: python.exe existing is not enough (a half-built venv from an aborted pip
# run has python.exe but no uvicorn); probe the third-party imports as well.
# Read-only modes (F23) never install or repair anything.
if (-not $ReadOnlyMode) {
    if (-not (Bootstrap-TestImports $VenvPythonMarker $OramaImportProbe)) {
        $InstallScript = Join-Path $ScriptDir 'install.ps1'
        if ($env:ORAMA_BOOTSTRAP_ACTIVE -eq '1') {
            # install.ps1 itself launches 'start.ps1 --discover'; never recurse.
            _Warn 'bootstrap' 'orama .venv not yet complete inside install.ps1 — skipping nested bootstrap'
        } elseif (Test-Path $InstallScript) {
            _Info 'bootstrap' 'orama .venv missing or incomplete — running install.ps1 (bootstrap/heal)...'
            $env:ORAMA_BOOTSTRAP_ACTIVE = '1'
            try {
                & $InstallScript
            } finally {
                Remove-Item Env:\ORAMA_BOOTSTRAP_ACTIVE -ErrorAction SilentlyContinue
            }
            if (-not (Bootstrap-TestImports $VenvPythonMarker $OramaImportProbe)) {
                _Err 'bootstrap' 'install.ps1 completed but the orama .venv still fails import probe (uvicorn, fastapi, httpx) — see output above'
                exit 1
            }
            _Info 'bootstrap' 'install.ps1 complete — continuing start.ps1'
        } else {
            _Warn 'bootstrap' "install.ps1 not found at $InstallScript — Python detection below may fail"
        }
    }
}

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
$PathsNeedRewrite = $false
if ($PtDir) {
    $PtVenvPython = Join-Path $PtDir '.venv\Scripts\python.exe'
    # F11: probe/heal PT's venv (perpetua-tools metadata + requests + uvicorn,
    # no stray orama-system); the install runs with PtDir as cwd. Read-only
    # modes only resolve the path.
    if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }
    # Always prefer the venv python once it exists, even over a cached
    # $PtPython from an older .paths.ps1 written before PT had a venv —
    # otherwise a stale cache silently keeps using the dep-less system
    # Python forever and PT never starts, no matter how many times the
    # bootstrap above (re)creates the venv.
    if ((Test-Path $PtVenvPython) -and $PtPython -ne $PtVenvPython) {
        $PtPython = $PtVenvPython
        $PathsNeedRewrite = $true
    }
}
if (-not $PtPython -and $PtDir) {
    $PtPython = Get-BestPython $PtDir
}

# F4: write .paths.ps1 exactly once. Read-only modes (F23) never write it
# (they resolve paths in memory); --discover always does.
if ($Discover -or (-not $ReadOnlyMode -and ($PathsNeedRewrite -or -not (Test-Path $PathsFile)))) {
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
        # Set-StrictMode -Version Latest throws on .Value against a $null
        # Get-Item result (e.g. a fresh install where none of these env vars
        # are set yet) — guard the item before dereferencing it.
        $item = Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue
        if ($item -and $item.Value -match '^(1|true|yes)$') { return $true }
    }
    return $false
}

if (-not $ReadOnlyMode -and ($LanPeer -or (Test-LanBindConfigured))) {
    _Warn 'svc' 'LAN bind enabled (PT_BIND_LAN/ORAMA_BIND_LAN/PORTAL_BIND_LAN) — control-plane APIs are reachable on the network'
    $MeshScript = Join-Path $RepoRoot 'scripts\mesh\Invoke-MeshLocalCache.ps1'
    if (Test-Path $MeshScript) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $MeshScript -RepoRoot $RepoRoot -Python $UsPython -Mode LanBind
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Error 'scripts\mesh\Invoke-MeshLocalCache.ps1 missing — GOSSIP gate cannot run for LAN bind'
        exit 1
    }
    Sync-ControlPlaneToken
    $weak = @('', 'change-me-before-network-use', 'changeme', 'change-me', 'placeholder', 'test', 'secret')
    $tokenVal = $env:ORAMA_CONTROL_PLANE_TOKEN
    if ($null -eq $tokenVal) { $tokenVal = '' }
    if ($weak -contains $tokenVal.Trim().ToLower()) {
        Write-Error 'LAN bind requires a strong ORAMA_CONTROL_PLANE_TOKEN (set in .env.local or generated in PT/.state/control_plane_token)'
        exit 1
    }
}

function Topo-MaskSecrets([string]$Text) {
    <#
    .SYNOPSIS
    Mask secret-bearing values in captured text.
    #>
    # Mask secret-bearing values in captured child output: JSON string values
    # (keys with underscores/hyphens, escaped quotes inside the value),
    # key=value pairs, and Bearer credentials. Applied before console AND log.
    $keys = '[\w-]*(?:token|secret|authorization|api[_-]?key|password|passwd|credential)[\w-]*'
    $Text = $Text -replace ('(?i)("' + $keys + '"\s*:\s*")(?:[^"\\]|\\.)*(")'), '$1***$2'
    $Text = $Text -replace ('(?i)(\b' + $keys + '\s*[=:]\s*)(?:Bearer\s+)?[^\s,;"'']+'), '$1***'
    $Text = $Text -replace '(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+', '$1***'
    return $Text
}

function Topo-WriteProbeOutput {
    <#
    .SYNOPSIS
    Print captured child output to host and startup log with secrets masked.
    #>
    # Show captured child output on the host and in the startup log; mask any
    # token-like JSON values before printing.
    param([string]$Tag, $Lines)
    foreach ($ln in @($Lines)) {
        $s = "$ln"
        if (-not $s.Trim()) { continue }
        $s = Topo-MaskSecrets $s
        Write-Host "  [$Tag] $s"
        try {
            $null = New-Item -ItemType Directory -Force -Path $LogDir
            Add-Content -Path (Join-Path $LogDir "startup-$(Get-Date -Format yyyyMMdd).log") -Value "  [$Tag] $s"
        } catch {}
    }
}

function Invoke-LanPeerProbe {
    $probe = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py'
    if (-not (Test-Path $probe)) {
        _Warn 'lan-peer' "probe script missing: $probe"
        return $false
    }
    Sync-ControlPlaneToken
    if ($PtDir) { Set-LauncherPtEnv -Dir $PtDir -RootOnly }
    _Info 'lan-peer' 'running probe_lan_peer.py --json ...'
    $probeTimeout = if ($env:LAN_PEER_PROBE_TIMEOUT) { $env:LAN_PEER_PROBE_TIMEOUT } else { '2' }
    $statusTimeout = if ($env:LAN_PEER_STATUS_TIMEOUT) { $env:LAN_PEER_STATUS_TIMEOUT } else { '3' }
    $wsTimeout = if ($env:LAN_PEER_WS_TIMEOUT) { $env:LAN_PEER_WS_TIMEOUT } else { '2' }
    # Capture stdout/stderr: leaving the call uncaptured leaks the JSON into this
    # function's output stream, so the caller would see a non-empty (truthy)
    # array even when the probe failed.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $UsPython $probe --json --timeout $probeTimeout --status-timeout $statusTimeout --ws-timeout $wsTimeout 2>&1
        $probeExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    Topo-WriteProbeOutput 'probe' $out
    if ($probeExit -ne 0) {
        _Warn 'lan-peer' 'peer probe reported failures (Mac peer may need ./start.sh --lan-peer)'
    }
    return ($probeExit -eq 0)
}

function Invoke-LanPeerOutboxFlush {
    $assign = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py'
    if (-not (Test-Path $assign)) {
        _Warn 'lan-peer' "assignment script missing: $assign"
        return
    }
    Sync-ControlPlaneToken
    if ($PtDir) { Set-LauncherPtEnv -Dir $PtDir -RootOnly }
    _Info 'lan-peer' 'flushing queued peer drops ...'
    $httpTimeout = if ($env:LAN_PEER_HTTP_TIMEOUT) { $env:LAN_PEER_HTTP_TIMEOUT } else { '2' }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $flushOut = & $UsPython $assign flush-outbox --peer --timeout $httpTimeout 2>&1
        $flushExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    Topo-WriteProbeOutput 'outbox' $flushOut
    if ($flushExit -ne 0) {
        _Warn 'lan-peer' 'queued peer drops remain pending'
    }
}

function Invoke-LanPeerSession {
    param([string[]]$LanArgs)
    $session = Join-Path $RepoRoot 'bin\orama-system\skills\hermes-harness\scripts\lan_peer_session.py'
    if (-not (Test-Path $session)) {
        _Warn 'lan-peer' "session state script missing: $session"
        return $true
    }
    & $UsPython $session @LanArgs | Out-Null
    return [bool]($LASTEXITCODE -eq 0)
}

# ── Hardware policy check ─────────────────────────────────────────────────────
function Invoke-HardwarePolicyCheck {
    $cli = if ($PtDir) { Join-Path $PtDir 'scripts\hardware_policy_cli.py' } else { $null }
    if ($cli -and (Test-Path $cli)) {
        Write-Host "`n=== Hardware model affinity policy ==="
        $env:PYTHONPATH = $PtDir
        & $PtPython $cli --list
        if ($LASTEXITCODE -ne 0) {
            throw "Hardware policy listing exited $LASTEXITCODE"
        }
        & $PtPython $cli --validate 'qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2' win
        if ($LASTEXITCODE -ne 0) {
            throw "Hardware policy validation exited $LASTEXITCODE"
        }
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

# True when every LISTENING socket on the port is bound to a loopback address.
# No listener, or an unparsable address, counts as not loopback-only (fail closed).
function Test-PortLoopbackOnly {
    param([int]$Port)
    $seen = 0
    try {
        foreach ($nsLine in @(& netstat -ano 2>$null)) {
            if ("$nsLine" -match '^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+\d+') {
                $nsAddrText = $Matches[1].Trim('[', ']')
                if ([int]$Matches[2] -ne $Port) { continue }
                $seen++
                $nsAddr = $null
                if (-not [System.Net.IPAddress]::TryParse($nsAddrText, [ref]$nsAddr)) { return $false }
                if (-not [System.Net.IPAddress]::IsLoopback($nsAddr)) { return $false }
            }
        }
    } catch { return $false }
    return ($seen -gt 0)
}

# Life-* helpers: service lifecycle (detached launch, readiness, stop). PS 5.1 safe.
function Life-GetProc {
    param([int]$ProcId)
    if ($ProcId -le 0) { return $null }
    try { return (Get-Process -Id $ProcId -ErrorAction Stop) } catch { return $null }
}

# True when ProcId is alive, its name matches NamePattern and (optionally) its
# command line matches CmdPattern. Never matches on process name alone for kills.
function Life-PidMatches {
    param([int]$ProcId, [string]$NamePattern, [string]$CmdPattern = '')
    $p = Life-GetProc $ProcId
    if (-not $p) { return $false }
    if ($p.ProcessName -notmatch $NamePattern) { return $false }
    if ($CmdPattern) {
        try {
            $cim = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$ProcId" -ErrorAction Stop
            if (-not $cim -or -not $cim.CommandLine) { return $false }
            if ($cim.CommandLine -notmatch $CmdPattern) { return $false }
        } catch { return $false }
    }
    return $true
}

function Life-IsPythonPid {
    param([int]$ProcId)
    return (Life-PidMatches $ProcId '^pythonw?[0-9.]*$')
}

function Life-ReadPid {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) { return 0 }
    try {
        $text = (Get-Content -Path $PidFile -Raw -ErrorAction Stop).Trim()
        $n = 0
        if ([int]::TryParse($text, [ref]$n)) { return $n }
    } catch {}
    return 0
}

# Probe host: the specific bind host, else IPv4 loopback by address (the name
# localhost costs ~2 s per attempt on IPv6-first hosts).
function Life-ProbeHost {
    param([string]$BindHost = '')
    if ($BindHost -and $BindHost -ne '0.0.0.0' -and $BindHost -ne '::') { return $BindHost }
    return [System.Net.IPAddress]::Loopback.IPAddressToString
}

function Life-ShowLogTail {
    param([string]$LogFile, [int]$Lines = 30)
    if (Test-Path $LogFile) {
        Write-Host "  --- last $Lines lines of $LogFile ---"
        foreach ($l in @(Get-Content -Path $LogFile -Tail $Lines -Encoding UTF8 -ErrorAction SilentlyContinue)) {
            Write-Host "  | $l"
        }
        Write-Host '  --- end of log ---'
    } else {
        Write-Host "  (no log file at $LogFile)"
    }
}

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$Label,
        [int]$MaxSeconds = 75,
        [int]$ServicePid = 0,
        [string]$BindHost = ''
    )
    $probeHost = Life-ProbeHost $BindHost
    $svcLog = Join-Path $LogDir (($Label.ToLower() -replace '\s+', '_') + '.log')
    Write-Host -NoNewline "  waiting for $Label (port $Port)"
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        $tcp = New-Object System.Net.Sockets.TcpClient
        try {
            $conn = $tcp.ConnectAsync($probeHost, $Port)
            if ($conn.Wait(250) -and $tcp.Connected) {
                Write-Host ' UP'
                return $true
            }
        } catch {
        } finally {
            $tcp.Close()
        }
        # Process-exit branch: the service died before opening its port.
        if ($ServicePid -gt 0 -and -not (Life-GetProc $ServicePid)) {
            Write-Host " FAILED - process $ServicePid exited before port $Port was up"
            Life-ShowLogTail $svcLog 30
            return $false
        }
        Write-Host -NoNewline '.'
        Start-Sleep -Milliseconds 250
    }
    Write-Host " TIMEOUT - check $svcLog"
    Life-ShowLogTail $svcLog 30
    return $false
}

function Open-Browser {
    param([string]$Url)
    try { Start-Process $Url } catch { _Warn 'browser' "Could not open browser: $_" }
}

# ── Portal TLS front end (opt-in: PORTAL_TLS_ENABLED=1/true/yes) ──────────────
# When enabled, the Portal binds loopback only and orchestrator.portal_tls_proxy
# (Perpetua-Tools) is the single LAN-facing listener, on PORTAL_TLS_PORT.
$PortalTlsEnabled = $false
if ($env:PORTAL_TLS_ENABLED) {
    $PortalTlsEnabled = ($env:PORTAL_TLS_ENABLED.Trim().ToLower() -in @('1', 'true', 'yes'))
}
$PortalTlsPort = if ($env:PORTAL_TLS_PORT) { [int]$env:PORTAL_TLS_PORT } else { 8443 }
$PortalTlsListenHost = if ($env:PORTAL_TLS_LISTEN_HOST) { $env:PORTAL_TLS_LISTEN_HOST.Trim() } else { '0.0.0.0' }

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
    # PID files written by the detached launcher (never kill by process name).
    if (Test-Path $LogDir) {
        foreach ($pf in @(Get-ChildItem -Path $LogDir -Filter '*.pid' -File -ErrorAction SilentlyContinue)) {
            $recorded = Life-ReadPid $pf.FullName
            $isWatcher = ($pf.BaseName -eq 'lm_link_watch')
            if ($isWatcher) {
                $owned = Life-PidMatches $recorded '^(powershell|pwsh)$' 'lm_link_watch'
            } elseif ($pf.BaseName -eq 'portal_tls') {
                # Portal TLS proxy: command-line match on portal_tls_proxy, never by name.
                $owned = Life-PidMatches $recorded '^pythonw?[0-9.]*$' 'portal_tls_proxy'
            } else {
                $owned = Life-PidMatches $recorded '^pythonw?[0-9.]*$' 'uvicorn'
            }
            if ($owned) {
                & taskkill.exe /PID $recorded /T /F 2>$null | Out-Null
                Write-Host "  killed PID $recorded ($($pf.BaseName) from $($pf.Name))"
            } elseif ($recorded -gt 0) {
                Write-Host "  $($pf.Name): PID $recorded is not a matching process (already stopped or reused); not killed"
            }
            Remove-Item -Path $pf.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    exit 0
}

# ── --fleet-status ───────────────────────────────────────────────────────────
$script:FleetStatusExitCode = 1

function Show-FleetStatus {
    param([string]$Format = 'text')
    try {
        $py = Get-BestPython $RepoRoot
        $src = Join-Path $RepoRoot 'src'
        if (-not (Test-Path $src)) {
            Write-Host 'Error: orama-system source not found'
            return
        }
        $pyCode = @"
import sys
from orama_system.display_fleet_status import load_fleet_topology, format_json, format_text
status = load_fleet_topology()
if '$Format' == 'json':
    print(format_json(status))
else:
    print(format_text(status))
"@
        $env:PYTHONPATH = "$src$([IO.Path]::PathSeparator)$env:PYTHONPATH"
        & $py -c $pyCode
        $script:FleetStatusExitCode = $LASTEXITCODE
    } catch {
        Write-Host "Error displaying fleet status: $_"
        $script:FleetStatusExitCode = 1
    }
}

if ($FleetStatus) {
    Show-FleetStatus -Format $FleetStatusFormat
    exit $script:FleetStatusExitCode
}

# ── --status ──────────────────────────────────────────────────────────────────
if ($Status) {
    Write-Host '── service status ────────────────────────────────────────────────────'
    foreach ($entry in @(
        @{Name='PT';     Port=$PtPort},
        @{Name='orama';  Port=$UsPort},
        @{Name='Portal'; Port=$PortalPort}
    ) + $(if ($PortalTlsEnabled -or (Test-Path (Join-Path $LogDir 'portal_tls.pid'))) { @(@{Name='Portal TLS'; Port=$PortalTlsPort}) } else { @() })) {
        $listenerPid = Get-PidOnPort $entry.Port
        if ($listenerPid) {
            Write-Host ("  {0,-10} :{1,-5}  ● UP    (PID {2})" -f $entry.Name, $entry.Port, $listenerPid)
        } else {
            Write-Host ("  {0,-10} :{1,-5}  ○ DOWN" -f $entry.Name, $entry.Port)
        }
    }
    Invoke-HardwarePolicyCheck
    Write-Host ''
    exit 0
}

# ── LAN discovery (always fresh before IP resolution) ─────────────────────────
# ── Topology helpers (Topo- prefix) ───────────────────────────────────────────
# Loopback by address object, never by name: resolving 'localhost' tries the
# IPv6 loopback first and costs ~2 s per probe when nothing listens there.
$TopoLoopback = [System.Net.IPAddress]::Loopback.IPAddressToString

function Topo-GetLocalIPv4 {
    <#
    .SYNOPSIS
    Return every IPv4 address bound to this machine.
    #>
    # Every IPv4 address bound on this machine.
    try {
        return @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Select-Object -ExpandProperty IPAddress)
    } catch {
        try {
            return @([System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
                Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork } |
                ForEach-Object { $_.IPAddressToString })
        } catch { return @() }
    }
}

function Topo-GetDefaultRouteIp {
    <#
    .SYNOPSIS
    Return the IPv4 address used for the default route, or empty.
    #>
    # IPv4 of the interface that owns the lowest-metric default route.
    try {
        $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop |
            Sort-Object { $_.RouteMetric + $_.InterfaceMetric } | Select-Object -First 1
        $addr = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
            Select-Object -First 1
        $ipText = [string]$addr.IPAddress
        if ($ipText) { return $ipText }
        return 'localhost'
    } catch { return 'localhost' }
}

function Topo-GetVersion {
    <#
    .SYNOPSIS
    Return the orama-system version read from the version module.
    #>
    # Single source of truth is src/orama_system/_version.py (pyproject.toml
    # reads it dynamically); pyproject.toml is the fallback.
    $candidates = @(
        @{ Path = (Join-Path $RepoRoot 'src\orama_system\_version.py'); Pattern = '(?m)^__version__\s*=\s*["'']([^"'']+)["'']' },
        @{ Path = (Join-Path $RepoRoot 'pyproject.toml');               Pattern = '(?m)^version\s*=\s*"([^"]+)"' }
    )
    foreach ($c in $candidates) {
        if (-not (Test-Path $c.Path)) { continue }
        try {
            $m = [regex]::Match((Get-Content $c.Path -Raw -Encoding UTF8), $c.Pattern)
            if ($m.Success) { return $m.Groups[1].Value }
        } catch {}
    }
    return 'unknown'
}

function Topo-IsKnownIp([string]$ip) {
    <#
    .SYNOPSIS
    True when the value is a concrete, resolvable peer address.
    #>
    return [bool]($ip -and $ip -notin @('unknown', 'unresolved', 'localhost', $TopoLoopback))
}

function Topo-EndpointRefersToLoopback {
    <#
    .SYNOPSIS
    True when an endpoint string names only this machine (loopback host).
    #>
    param([string]$Endpoint)
    if (-not $Endpoint -or -not $Endpoint.Trim()) { return $false }
    $raw = $Endpoint.Trim()
    if ($raw -notmatch '^(?i)https?://') {
        $raw = "http://$raw"
    }
    try {
        $uri = [System.Uri]$raw
    } catch {
        return $false
    }
    $hostText = $uri.Host
    if (-not $hostText) { return $false }
    $addr = $null
    if ([System.Net.IPAddress]::TryParse($hostText, [ref]$addr)) {
        return [System.Net.IPAddress]::IsLoopback($addr)
    }
    try {
        foreach ($resolved in [System.Net.Dns]::GetHostAddresses($hostText)) {
            if ([System.Net.IPAddress]::IsLoopback($resolved)) { return $true }
        }
    } catch {}
    return $false
}

function Test-LmStudioUp([string]$ip) {
    <#
    .SYNOPSIS
    Probe LM Studio on the given host with a 5 s timeout; returns bool.
    #>
    if (-not $ip) { return $false }
    # Local checks use the loopback address object (8 ms) not 'localhost' (~2 s);
    # 5 s timeout matches the other LM Studio check in this script.
    $probeHost = if ($ip -in @('localhost', $TopoLoopback)) { $TopoLoopback } else { $ip }
    $url = "http://${probeHost}:1234/v1/models"
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    } catch { return $false }
}

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
        Set-LauncherPtEnv -Dir $PtDir
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
        if ($macIp -and $macIp -notin @('localhost', $TopoLoopback)) {
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
                if ($candidate -and $candidate -notin @('', 'localhost', $TopoLoopback)) {
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
                    if ($hostFromUrl -notin @('', 'localhost', $TopoLoopback)) {
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

# ── Dual Windows node detection (RTX 3080 + RTX 5080) ────────────────────────
# This machine is ONE Win node; detect the SIBLING Win node on the LAN.
# Runs BEFORE Invoke-DiscoverEndpoints so discover.py inherits WIN_3080_IP /
# WIN_5080_IP / WIN_IP from the environment.
# Reads PT config/devices.yml for both node IPs and identifies which is local by
# comparing against ALL local IPv4 addresses. Probes only a KNOWN sibling IP on
# port 1234; an unknown sibling is reported 'unknown' and never probed.
# Exports WIN_3080_IP, WIN_5080_IP, WIN_NODES, WIN_SIBLING_IP.
# Coordinated with start.sh dual-node detection (same env vars).
#
# Priority for each node IP:
#   1. Explicit env var (WIN_3080_IP / WIN_5080_IP) — user override
#   2. PT config/devices.yml (win-rtx3080.lan_ip / win-rtx5080.lan_ip)
# Idempotent: read-only HTTP probes, no state mutation, safe to re-run.
# A pre-set WIN_IP is trusted only when it is on a local interface; a stale one
# (from .env.local or a previous run in this console) is warned about and replaced.
$TopoLocalIps = @(Topo-GetLocalIPv4)
# WIN_IP is an operator hint for the Windows-facing address, NOT proof of
# locality: it must never be added to $TopoLocalIps (a stale or sibling value
# would make the sibling look local). Local identity comes from interfaces only.
if ($env:WIN_IP -and $env:WIN_IP -notin $TopoLocalIps) {
    _Warn 'dual-win' "WIN_IP=$($env:WIN_IP) is not on any local interface - stale; using the default-route address instead"
    $env:WIN_IP = Topo-GetDefaultRouteIp
} elseif (-not $env:WIN_IP) {
    $env:WIN_IP = Topo-GetDefaultRouteIp
}

$Win3080Ip = $env:WIN_3080_IP
$Win5080Ip = $env:WIN_5080_IP

# Read devices.yml from PtDir
if ($PtDir) {
    $DevicesYaml = Join-Path $PtDir 'config\devices.yml'
    if (Test-Path $DevicesYaml) {
        try {
            $yamlText = Get-Content $DevicesYaml -Raw -Encoding UTF8
            $currentId = ""
            foreach ($line in ($yamlText -split "`n")) {
                if ($line -match '^\s+-\s+id:\s*"?([A-Za-z0-9_.-]+)"?') {
                    $currentId = $Matches[1]
                }
                elseif ($line -match '^\s+lan_ip:\s*"([^"]*)"' -and $currentId) {
                    $ip = $Matches[1]
                    if ($currentId -eq 'win-rtx3080' -and -not $Win3080Ip) { $Win3080Ip = $ip }
                    elseif ($currentId -eq 'win-rtx5080' -and -not $Win5080Ip) { $Win5080Ip = $ip }
                }
            }
        } catch {
            _Warn 'dual-win' "Failed to parse devices.yml: $($_.Exception.Message)"
        }
    }
}

# A configured IP is "local" when it is on any local interface (or the loopback name).
function Topo-IsLocalIp([string]$ip) {
    <#
    .SYNOPSIS
    True when the address belongs to this machine (interfaces or loopback only).
    #>
    if (-not $ip) { return $false }
    return [bool]($ip -in $TopoLocalIps -or $ip -in @('localhost', $TopoLoopback))
}

$LocalIs3080 = $false
$LocalIs5080 = $false
if (Topo-IsLocalIp $Win3080Ip) { $LocalIs3080 = $true }
elseif (Topo-IsLocalIp $Win5080Ip) { $LocalIs5080 = $true }
else {
    # Neither configured IP is on this machine: assume the 3080 and say so.
    $LocalIs3080 = $true
    if ($Win3080Ip -or $Win5080Ip) {
        _Warn 'dual-win' "Configured node IPs (3080=$Win3080Ip 5080=$Win5080Ip) match no local address - config is stale; assuming this machine is the RTX 3080 (WIN_IP=$($env:WIN_IP))"
    } else {
        _Warn 'dual-win' "No Win node IPs configured; assuming this machine is the RTX 3080 (WIN_IP=$($env:WIN_IP))"
    }
    if (Topo-IsKnownIp $env:WIN_IP) { $Win3080Ip = $env:WIN_IP }
}

# Sibling is the OTHER node; unknown when empty or identical to a local address.
$WinSiblingIp = if ($LocalIs3080) { $Win5080Ip } else { $Win3080Ip }
if (-not (Topo-IsKnownIp $WinSiblingIp) -or (Topo-IsLocalIp $WinSiblingIp)) {
    $WinSiblingIp = 'unknown'
    if ($LocalIs3080) { $Win5080Ip = '' } else { $Win3080Ip = '' }
}

# Probe: local node via loopback, sibling only when its IP is known.
$Win3080Up = $false
$Win5080Up = $false
if ($LocalIs3080) { $Win3080Up = Test-LmStudioUp 'localhost' } elseif (Topo-IsKnownIp $Win3080Ip) { $Win3080Up = Test-LmStudioUp $Win3080Ip }
if ($LocalIs5080) { $Win5080Up = Test-LmStudioUp 'localhost' } elseif (Topo-IsKnownIp $Win5080Ip) { $Win5080Up = Test-LmStudioUp $Win5080Ip }
$WinNodes = 0; if ($Win3080Up) { $WinNodes++ }; if ($Win5080Up) { $WinNodes++ }

# Export for child processes and hardware routing (before discovery runs)
$env:WIN_3080_IP = $Win3080Ip
$env:WIN_5080_IP = $Win5080Ip
$env:WIN_NODES   = "$WinNodes"
$env:WIN_SIBLING_IP = if ($WinSiblingIp -eq 'unknown') { '' } else { $WinSiblingIp }
$env:LM_STUDIO_WIN_3080_ENDPOINTS = if ($Win3080Ip) { "http://${Win3080Ip}:1234" } else { '' }
$env:LM_STUDIO_WIN_5080_ENDPOINTS = if ($Win5080Ip) { "http://${Win5080Ip}:1234" } else { '' }
# Peer endpoint: keep an explicit remote override; replace a loopback
# placeholder (it points at THIS machine) with the sibling when known; leave it
# unset when the sibling is unknown so the orchestrator skips the probe rather
# than probing this machine.
$WinPeerIsLoopback = Topo-EndpointRefersToLoopback $env:WIN_PEER_ENDPOINT
if (-not $env:WIN_PEER_ENDPOINT -or $WinPeerIsLoopback) {
    $env:WIN_PEER_ENDPOINT = if (Topo-IsKnownIp $WinSiblingIp) { "${WinSiblingIp}:1234" } else { '' }
}

Invoke-DiscoverEndpoints
$MacResolved = Resolve-MacLanIp
$MacIp    = $MacResolved.Ip
$IpSource = $MacResolved.Source

# ── Export env vars for child processes ───────────────────────────────────────
if ($MacIp -and $MacIp -notin @('unresolved', 'localhost', $TopoLoopback)) {
    $env:MAC_IP = $MacIp
}
$env:OLLAMA_MAC_ENDPOINT       = if ($env:OLLAMA_MAC_ENDPOINT)       { $env:OLLAMA_MAC_ENDPOINT }       elseif ($MacIp -notin @('unresolved','localhost',$TopoLoopback)) { "http://${MacIp}:11434" } else { 'http://localhost:11434' }
$env:OLLAMA_WINDOWS_ENDPOINT   = if ($env:OLLAMA_WINDOWS_ENDPOINT)   { $env:OLLAMA_WINDOWS_ENDPOINT }   else { 'http://localhost:11434' }
$env:LM_STUDIO_MAC_ENDPOINT    = if ($env:LM_STUDIO_MAC_ENDPOINT)    { $env:LM_STUDIO_MAC_ENDPOINT }    elseif ($MacIp -notin @('unresolved','localhost',$TopoLoopback)) { "http://${MacIp}:1234" } else { 'http://localhost:1234' }
$env:LM_STUDIO_WIN_ENDPOINTS   = if ($env:LM_STUDIO_WIN_ENDPOINTS)   { $env:LM_STUDIO_WIN_ENDPOINTS }   else { "http://$($env:WIN_IP):1234" }
# WIN_PEER_ENDPOINT - consumed by the dual-path orchestrator peer probe
# (set above, before discovery: sibling node when known, else empty = no probe).
$env:WIN_LM_STUDIO_HOST        = if ($env:WIN_LM_STUDIO_HOST)        { $env:WIN_LM_STUDIO_HOST }        else { 'localhost' }
$env:WINDOWS_IP                = $env:WIN_IP

if ($WinNodes -ge 2) {
    _Info 'gpu' "Dual Win nodes detected: 3080=$Win3080Ip  5080=$Win5080Ip  ($WinNodes UP, sibling=$WinSiblingIp)"
} else {
    $Win3080Shown = if ($Win3080Ip) { $Win3080Ip } else { 'unknown' }
    $Win5080Shown = if ($Win5080Ip) { $Win5080Ip } else { 'unknown' }
    _Info 'gpu' "Win nodes: 3080=$Win3080Shown  5080=$Win5080Shown  ($WinNodes UP, sibling=$WinSiblingIp)"
}

_Info 'ip' "Mac LMS endpoint: ${MacIp}:1234 (source: $IpSource)"

_Info 'env' 'Endpoints exported'

# ── Banner ────────────────────────────────────────────────────────────────────
$TopoVersion = Topo-GetVersion
$TopoTitle   = "orama-system  v$TopoVersion  (Windows)"
Write-Host ''
Write-Host '╔══════════════════════════════════════════════════════════════════╗'
Write-Host ("║  {0}║" -f $TopoTitle.PadRight(64))
Write-Host '║  ὅραμα — vision/revelation · Layer 3 orchestration/meta-intel   ║'
Write-Host '╠══════════════════════════════════════════════════════════════════╣'
Write-Host ("║  Mac  {0,-9}  LM Studio expected on port 1234              ║" -f ($MacIp + ':'))
$Win3080Label = if ($LocalIs3080) { 'localhost' } elseif ($Win3080Ip) { $Win3080Ip } else { 'unknown' }
$Win5080Label = if ($LocalIs5080) { 'localhost' } elseif ($Win5080Ip) { $Win5080Ip } else { 'unknown' }
$Win3080Mark  = if ($Win3080Up) { '✓' } else { '✗' }
$Win5080Mark  = if ($Win5080Up) { '✓' } else { '✗' }
$Win3080Desc  = 'RTX 3080 · qwen3.5-27b' + $(if ($LocalIs3080) { ' (this machine)' } else { '' })
$Win5080Desc  = 'RTX 5080 · gemma-4-26b (nvfp4)' + $(if ($LocalIs5080) { ' (this machine)' } else { '' })
Write-Host ("║  Win {0}  {1,-9}  {2}║" -f $Win3080Mark, $Win3080Label, $Win3080Desc.PadRight(46))
Write-Host ("║  Win {0}  {1,-9}  {2}║" -f $Win5080Mark, $Win5080Label, $Win5080Desc.PadRight(46))
Write-Host ('╠══════════════════════════════════════════════════════════════════╣')
Write-Host ("║  PT   port $PtPort     orama port $UsPort     Portal port $PortalPort                      ║")
Write-Host '╚══════════════════════════════════════════════════════════════════╝'
Write-Host ''

# ── Helper: start a service as a detached background process ──────────────────
# scripts\lib\spawn_detached.py starts the child detached (own process group, no
# console, outside the launcher's job), appends stdout+stderr to the log and
# writes the PID file, then exits. The service therefore keeps running and keeps
# logging after this launcher exits. Secrets are inherited via the environment,
# never put on a command line.
$LifeSpawnScript = Join-Path $RepoRoot 'scripts\lib\spawn_detached.py'

# Returns the child PID (int), or 0 when the launcher failed.
function Life-Spawn {
    param(
        [string]$LogFile,
        [string]$PidFile,
        [string]$WorkDir,
        [string[]]$Cmd,
        [hashtable]$EnvExtra = @{}
    )
    $spawnArgs = @($LifeSpawnScript, $LogFile, $PidFile, $WorkDir)
    foreach ($kv in $EnvExtra.GetEnumerator()) {
        $spawnArgs += '--env'
        $spawnArgs += ('{0}={1}' -f $kv.Key, $kv.Value)
    }
    $spawnArgs += '--'
    $spawnArgs += $Cmd
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = @(& $UsPython @spawnArgs 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    $n = 0
    if ($code -eq 0 -and $out.Count -gt 0 -and [int]::TryParse($out[$out.Count - 1].Trim(), [ref]$n)) {
        return $n
    }
    Write-Host "  spawn failed (exit $code): $($out -join ' ')"
    return 0
}

function Start-OramaService {
    param(
        [string]$Name,
        [int]$Port,
        [string]$WorkDir,
        [string[]]$Cmd,
        [hashtable]$EnvExtra = @{}
    )
    $slug    = ($Name.ToLower() -replace '\s+', '_')
    $logFile = Join-Path $LogDir "$slug.log"
    $pidFile = Join-Path $LogDir "$slug.pid"
    $null    = New-Item -ItemType Directory -Force -Path $LogDir

    $owner = Get-PidOnPort $Port
    if ($owner) {
        if (Life-IsPythonPid ([int]$owner)) {
            Write-Host "  $Name  port $Port already running (python PID $owner)"
            return [pscustomobject]@{ Name = $Name; Port = $Port; Pid = [int]$owner; Started = $false; Failed = $false }
        }
        $ownerProc = Life-GetProc ([int]$owner)
        $ownerName = if ($ownerProc) { $ownerProc.ProcessName } else { 'unknown' }
        Write-Host "  $Name  port $Port is held by a non-python process ($ownerName, PID $owner); not starting"
        return [pscustomobject]@{ Name = $Name; Port = $Port; Pid = 0; Started = $false; Failed = $true }
    }

    # Port is free: keep the previous log instead of truncating or interleaving.
    if ((Test-Path $logFile) -and ((Get-Item $logFile).Length -gt 0)) {
        try { Move-Item -Path $logFile -Destination "$logFile.prev" -Force -ErrorAction Stop } catch {}
    }
    Write-Host "  $Name  starting -> $logFile"
    $svcPid = Life-Spawn -LogFile $logFile -PidFile $pidFile -WorkDir $WorkDir -Cmd $Cmd -EnvExtra $EnvExtra
    if ($svcPid -le 0) {
        return [pscustomobject]@{ Name = $Name; Port = $Port; Pid = 0; Started = $false; Failed = $true }
    }
    return [pscustomobject]@{ Name = $Name; Port = $Port; Pid = $svcPid; Started = $true; Failed = $false }
}

# Wait for a started service and return its summary row.
function Life-Settle {
    param($Svc, [string]$BindHost)
    if ($Svc.Failed) {
        return [pscustomobject]@{ Name = $Svc.Name; Port = $Svc.Port; State = 'FAILED'; Detail = 'could not start' }
    }
    if (-not $Svc.Started) {
        return [pscustomobject]@{ Name = $Svc.Name; Port = $Svc.Port; State = 'UP'; Detail = "already running (PID $($Svc.Pid))" }
    }
    $up = Wait-ForPort $Svc.Port $Svc.Name 75 $Svc.Pid $BindHost
    if ($up) {
        return [pscustomobject]@{ Name = $Svc.Name; Port = $Svc.Port; State = 'UP'; Detail = "started (PID $($Svc.Pid))" }
    }
    return [pscustomobject]@{ Name = $Svc.Name; Port = $Svc.Port; State = 'FAILED'; Detail = "not listening (PID $($Svc.Pid))" }
}

# Ensure partner CLI paths are present in this process without requiring User PATH registry access.
# Placed after all read-only/lifecycle handlers so --stop, --status, --list, etc.
# do not mutate PATH or leak script-scope variables.
if (Test-Path "$RepoRoot\platform\windows\ensure-partner-cli-paths.ps1") {
    & "$RepoRoot\platform\windows\ensure-partner-cli-paths.ps1" -SessionOnly
}

# Restart only owned Portal processes; never disturb PT or orama.
if ($RestartPortal) {
    Write-Host 'Restarting Portal (PT and orama keep running)...'
    foreach ($service in @(
        @{ Name = 'portal'; Pattern = 'uvicorn' },
        @{ Name = 'portal_tls'; Pattern = 'portal_tls_proxy' }
    )) {
        $pidFile = Join-Path $LogDir ($service.Name + '.pid')
        $recorded = Life-ReadPid $pidFile
        if ($recorded -gt 0 -and (Life-PidMatches $recorded '^pythonw?[0-9.]*$' $service.Pattern)) {
            & taskkill.exe /PID $recorded /T /F 2>$null | Out-Null
            Write-Host "  stopped $($service.Name) PID $recorded"
        } elseif ($recorded -gt 0) {
            Write-Host "  $($service.Name) PID record is stale or mismatched; process not killed"
        }
        if (Test-Path $pidFile) { Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue }
    }
    foreach ($restartPort in @($PortalPort, $PortalTlsPort)) {
        $deadline = (Get-Date).AddSeconds(10)
        while ((Get-Date) -lt $deadline -and (Get-PidOnPort $restartPort)) {
            Start-Sleep -Milliseconds 250
        }
        if (Get-PidOnPort $restartPort) {
            Write-Host "  port $restartPort remains occupied; normal startup will report its state"
        }
    }
}

# ── 1. Perpetua-Tools ─────────────────────────────────────────────────────────
$LifeResults = @()
$TlsSelfCheckLines = @()
$TlsSelfCheckNotice = ''
if ($PtDir -and (Test-Path (Join-Path $PtDir 'orchestrator\fastapi_app.py'))) {
    $svc = Start-OramaService -Name 'PT' -Port $PtPort -WorkDir $PtDir `
        -Cmd @($PtPython, '-m', 'uvicorn', 'orchestrator.fastapi_app:app',
               '--host', $PtHost, '--port', $PtPort.ToString()) `
        -EnvExtra @{ PYTHONPATH = "$PtDir\src;$PtDir" }
    $LifeResults += Life-Settle $svc $PtHost
} elseif ($PtDir) {
    Write-Host "  PT   FAILED (orchestrator\fastapi_app.py missing under: $PtDir)"
    $LifeResults += [pscustomobject]@{ Name = 'PT'; Port = $PtPort; State = 'FAILED'; Detail = 'PT directory resolved but fastapi_app.py missing' }
} else {
    Write-Host '  PT   skipped (Perpetua-Tools directory not found)'
    $LifeResults += [pscustomobject]@{ Name = 'PT'; Port = $PtPort; State = 'SKIPPED'; Detail = 'PT directory not found' }
}

# ── 2. orama reasoning engine ─────────────────────────────────────────────────
$oramaPyPath = "$RepoRoot\src;$RepoRoot"
$svc = Start-OramaService -Name 'orama' -Port $UsPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'orama_system.api_server:app',
           '--host', $UsHost, '--port', $UsPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $oramaPyPath }
$LifeResults += Life-Settle $svc $UsHost

# ── 3. Portal ─────────────────────────────────────────────────────────────────
if ($PortalTlsEnabled) {
    # The proxy is the only LAN-facing listener: force the Portal onto loopback
    # regardless of PORTAL_BIND_LAN / PORTAL_HOST.
    $PortalHost = [System.Net.IPAddress]::Loopback.IPAddressToString
    Write-Host "  Portal TLS enabled: Portal binds loopback only; TLS front end on port $PortalTlsPort"
}
$svc = Start-OramaService -Name 'Portal' -Port $PortalPort -WorkDir $RepoRoot `
    -Cmd @($UsPython, '-m', 'uvicorn', 'orama_system.portal_server:app',
           '--host', $PortalHost, '--port', $PortalPort.ToString()) `
    -EnvExtra @{ PYTHONPATH = $oramaPyPath }
$portalRow = Life-Settle $svc $PortalHost
$PortalLoopbackOk = $true
$PortalTlsReused = $false
if ($PortalTlsEnabled -and $portalRow.State -eq 'UP') {
    # A reused Portal keeps whatever bind it was started with. The TLS proxy must
    # never sit in front of one that also serves plain HTTP on the LAN.
    $PortalLoopbackOk = Test-PortLoopbackOnly $PortalPort
    if (-not $PortalLoopbackOk) {
        Write-Host "  Portal  port $PortalPort is bound to a non-loopback address; not starting the TLS front end"
        $portalRow = [pscustomobject]@{ Name = 'Portal'; Port = $PortalPort; State = 'FAILED'; Detail = 'bound to a non-loopback address; run --stop first' }
    }
}
$LifeResults += $portalRow

# ── 4. Portal TLS front end (only when PORTAL_TLS_ENABLED) ────────────────────
if ($PortalTlsEnabled -and $PortalLoopbackOk) {
    $tlsModule = if ($PtDir) { Join-Path $PtDir 'orchestrator\portal_tls_proxy.py' } else { '' }
    if (-not $PtDir -or -not $PtPython -or -not (Test-Path $tlsModule)) {
        Write-Host "  Portal TLS  FAILED (PORTAL_TLS_ENABLED is set but orchestrator\portal_tls_proxy.py is missing; update Perpetua-Tools)"
        $LifeResults += [pscustomobject]@{ Name = 'Portal TLS'; Port = $PortalTlsPort; State = 'FAILED'; Detail = 'portal_tls_proxy.py missing in PT directory' }
    } else {
        $svc = Start-OramaService -Name 'Portal TLS' -Port $PortalTlsPort -WorkDir $PtDir `
            -Cmd @($PtPython, '-m', 'orchestrator.portal_tls_proxy',
                   '--listen-port', $PortalTlsPort.ToString(),
                   '--upstream-port', $PortalPort.ToString(),
                   '--listen-host', $PortalTlsListenHost) `
            -EnvExtra @{ PYTHONPATH = "$PtDir\src;$PtDir" }
        $tlsRow = Life-Settle $svc $PortalTlsListenHost
        if ($tlsRow.State -eq 'UP' -and -not $svc.Started) { $PortalTlsReused = $true }
        if ($tlsRow.State -eq 'UP') {
            $prevEapCheck = $ErrorActionPreference
            $prevPyPathCheck = $env:PYTHONPATH
            $ErrorActionPreference = 'Continue'
            Push-Location $PtDir
            try {
                $env:PYTHONPATH = "$PtDir\src;$PtDir"
                $TlsSelfCheckLines = @(& $PtPython -m orchestrator.portal_tls_proxy --self-check `
                    --listen-port $PortalTlsPort.ToString() --upstream-port $PortalPort.ToString() 2>&1 |
                    ForEach-Object { "$_" })
                $selfCheckCode = $LASTEXITCODE
            } catch {
                $TlsSelfCheckLines = @("self-check could not run: $($_.Exception.Message)")
                $selfCheckCode = 1
            } finally {
                Pop-Location
                $env:PYTHONPATH = $prevPyPathCheck
                $ErrorActionPreference = $prevEapCheck
            }
            $olderProxy = ($selfCheckCode -eq 2 -and @($TlsSelfCheckLines | Where-Object { $_ -match 'unrecognized arguments' }).Count -gt 0)
            if ($olderProxy) {
                $TlsSelfCheckNotice = 'TLS self-check unavailable; update Perpetua-Tools before treating this endpoint as verified'
            } elseif ($selfCheckCode -ne 0) {
                $failureLine = @($TlsSelfCheckLines | Where-Object { $_ -match '^check_\w+=FAIL' } | Select-Object -First 1)
                $detail = if ($failureLine.Count) { "TLS self-check failed: $($failureLine[0])" } else { "TLS self-check failed (exit $selfCheckCode)" }
                $tlsRow = [pscustomobject]@{ Name = 'Portal TLS'; Port = $PortalTlsPort; State = 'FAILED'; Detail = $detail }
            }
        }
        $LifeResults += $tlsRow
    }
}

# ── Per-service summary; a failed core service fails the launcher ─────────────
Write-Host ''
Write-Host '── service summary ───────────────────────────────────────────────────'
foreach ($r in $LifeResults) {
    Write-Host ('  {0,-10} port {1,-6} {2,-8} {3}' -f $r.Name, $r.Port, $r.State, $r.Detail)
}
foreach ($checkLine in $TlsSelfCheckLines) {
    if ($checkLine -match '^(check_\w+|ca_sha256_file|self_check)=') { Write-Host "  $checkLine" }
}
if ($TlsSelfCheckNotice) { Write-Host "  WARNING: $TlsSelfCheckNotice" -ForegroundColor Yellow }
$LifeFailed = @($LifeResults | Where-Object { $_.State -eq 'FAILED' })
if ($LifeFailed.Count -gt 0) {
    Write-Host ("  {0} core service(s) failed: {1}" -f $LifeFailed.Count, (($LifeFailed | ForEach-Object { $_.Name }) -join ', '))
    Write-Host ("  Logs  : {0}\" -f $LogDir)
    Write-Host '────────────────────────────────────────────────────────────────────'
    exit 1
}

# ── Ready ─────────────────────────────────────────────────────────────────────
Write-Host '── services ready ────────────────────────────────────────────────────'
Write-Host ("  ●  PT      http://localhost:{0}/health" -f $PtPort)
Write-Host ("  ●  orama   http://localhost:{0}/health" -f $UsPort)
Write-Host ("  ●  Portal  {0}" -f $PortalUrl)
Write-Host ("  ○  JSON    {0}/api/status" -f $PortalUrl)
if ($PortalTlsEnabled -and $PortalLoopbackOk) {
    # Fingerprint lines come from the proxy itself (ca_sha256_file=, ca_public_path=).
    $tlsCaSha = ''
    $tlsCaPath = ''
    $prevEapFp = $ErrorActionPreference
    $prevPyPath = $env:PYTHONPATH
    $ErrorActionPreference = 'Continue'
    Push-Location $PtDir
    try {
        $env:PYTHONPATH = "$PtDir\src;$PtDir"
        $fpOut = @(& $PtPython -m orchestrator.portal_tls_proxy --print-fingerprint 2>&1 | ForEach-Object { "$_" })
        foreach ($fpLine in $fpOut) {
            if ($fpLine -match '^ca_sha256_file=(.+)$')  { $tlsCaSha  = $Matches[1].Trim() }
            if ($fpLine -match '^ca_public_path=(.+)$')  { $tlsCaPath = $Matches[1].Trim() }
        }
    } finally {
        Pop-Location
        $env:PYTHONPATH = $prevPyPath
        $ErrorActionPreference = $prevEapFp
    }
    Write-Host ("  ●  Portal TLS  https://localhost:{0}  (LAN-facing; Portal itself is loopback-only)" -f $PortalTlsPort)
    if ($PortalTlsReused) {
        Write-Host '     NOTE: the TLS front end was already running; the fingerprint below reflects the'
        Write-Host '     current PORTAL_TLS_STATE_DIR. If it was started with another state dir, compare'
        Write-Host '     with ca_sha256_file= in .logs\portal_tls.log, or run --stop and relaunch.'
    }
    if ($tlsCaSha -and $tlsCaPath) {
        Write-Host ("     CA public cert : {0}" -f $tlsCaPath)
        Write-Host ("     CA SHA-256     : {0}" -f $tlsCaSha)
        Write-Host '     Send the CA public cert to the peer, then compare its SHA-256 through a'
        Write-Host '     separate channel (voice, chat) before the peer trusts it. Never send a private key.'
    } else {
        Write-Host '     WARNING: could not read the CA fingerprint from --print-fingerprint output:'
        foreach ($fpLine in $fpOut) { Write-Host "       | $fpLine" }
    }
}
Write-Host ''
Write-Host ("  Logs  : {0}\" -f $LogDir)
Write-Host '  Stop  : .\platform\windows\start.ps1 --stop'
Write-Host '  LAN   : .\platform\windows\start.ps1 --lan-peer'
Write-Host '────────────────────────────────────────────────────────────────────'
Write-Host ''

# ── Verify model fallback tiers on startup (report the real result) ───────────
Write-Host '── model fallback chain ────────────────────────────────────────────'
$FallbackVerifyPs1 = Join-Path $ScriptDir 'fallback-chain-verify.ps1'
if (Test-Path $FallbackVerifyPs1) {
    $fallbackCode = 1
    try {
        & $FallbackVerifyPs1 -StatusOnly
        $fallbackCode = $LASTEXITCODE
    } catch {
        Write-Host "⚠️  Fallback chain verification failed to run: $($_.Exception.Message)"
    }
    if ($fallbackCode -eq 0) {
        Write-Host '✅ LM Studio (hard-required tier) is up; other tiers are listed above'
    } else {
        Write-Host '⚠️  LM Studio (hard-required tier) is DOWN; failover is not fully armed (services stay up)'
    }
} else {
    Write-Host "⚠️  Fallback chain verification script not found at $FallbackVerifyPs1"
}
Write-Host ''

# ── GLM-5.2 Ultimate Fallback Status ───────────────────────────────────────────
# When all other pathways (LM Studio, Ollama, cloud APIs) are blocked, agents can
# queue tasks for GLM-5.2 execution. This is the last-resort pathway that always works.
Write-Host ''
if ($Glm52Available -and $env:GLM52_API_KEY) {
    Write-Host '✅ GLM-5.2 Ultimate Fallback ACTIVE (all pathways blocked → GLM-5.2)'
    Write-Host "   Queue any task when LM Studio/Ollama unavailable"
    Write-Host "   Endpoint: $($env:GLM52_ENDPOINT)"
} else {
    Write-Host '⚠️  GLM-5.2 Ultimate Fallback NOT AVAILABLE'
    Write-Host '   Setup: bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh'
}
Write-Host ''

if ($LanPeer) {
    $retrySeconds = if ($env:LAN_PEER_DEGRADED_RETRY_SECONDS) { $env:LAN_PEER_DEGRADED_RETRY_SECONDS } else { '900' }
    if (-not (Invoke-LanPeerSession -LanArgs @('should-retry'))) {
        _Warn 'lan-peer' "macOS-only degraded mode active; next peer retry waits for LAN_PEER_DEGRADED_RETRY_SECONDS=$retrySeconds"
    } elseif (Invoke-LanPeerProbe) {
        $null = Invoke-LanPeerSession -LanArgs @('record-success')
        Invoke-LanPeerOutboxFlush
    } else {
        $null = Invoke-LanPeerSession -LanArgs @('record-failure', '--error', 'probe_lan_peer.py failed')
        _Warn 'lan-peer' 'skipping outbox flush until peer portal probe passes'
    }

    # ── LM Link watcher autostart (detached process, per-repo PID file, idempotent) ──
    try {
        $LmLinkWatchScript = Join-Path $RepoRoot 'scripts\lm_link_watch.ps1'
        if (-not (Test-Path $LmLinkWatchScript)) {
            _Warn 'lan-peer' "lm_link_watch.ps1 not found at: $LmLinkWatchScript - skipping watcher autostart"
        } else {
            $watchPidFile = Join-Path $LogDir 'lm_link_watch.pid'
            $watchPid = Life-ReadPid $watchPidFile
            if ($watchPid -gt 0 -and (Life-PidMatches $watchPid '^(powershell|pwsh)$' 'lm_link_watch')) {
                _Info 'lan-peer' "lm-link-watch already running (PID $watchPid)"
            } else {
                $null = New-Item -ItemType Directory -Force -Path $LogDir
                $watchLog = Join-Path $LogDir 'lm_link_watch.log'
                $newWatchPid = Life-Spawn -LogFile $watchLog -PidFile $watchPidFile -WorkDir $RepoRoot `
                    -Cmd @('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $LmLinkWatchScript)
                if ($newWatchPid -gt 0) {
                    _Info 'lan-peer' "lm-link-watch started detached (PID $newWatchPid, log $watchLog)"
                } else {
                    _Warn 'lan-peer' 'lm-link-watch failed to start'
                }
            }
        }
    } catch {
        _Warn 'lan-peer' "failed to start lm-link-watch: $($_.Exception.Message)"
    }
}

if (-not $NoOpen) {
    Open-Browser $PortalUrl
}
