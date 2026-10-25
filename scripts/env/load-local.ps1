# load-local.ps1 — Load gitignored repo env (.env then .env.local). Idempotent.
param(
    [string]$RepoRoot = ''
)

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

# Keys the caller may have set for this invocation (for example a per-run
# PERPETUA_TOOLS_PATH). The caller wins: snapshot them before any file loads so
# .env/.env.local can never override them.
#
# A value left in the console by a previous run (load-local itself, or
# start.ps1 resolving the PT path) is not a caller choice. Every value this
# script sets is recorded in ORAMA_LOADLOCAL_SET_<KEY>; a key counts as
# caller-set only when its current value differs from that marker.
# Callers that set these keys themselves should refresh the marker too.
$CallerWinsKeys = @('PERPETUA_TOOLS_PATH', 'PERPETUA_TOOLS_ROOT')
$CallerEnvSnapshot = @{}
foreach ($k in $CallerWinsKeys) {
    $v = [Environment]::GetEnvironmentVariable($k, 'Process')
    $marker = [Environment]::GetEnvironmentVariable("ORAMA_LOADLOCAL_SET_$k", 'Process')
    if ($v -and ($v -ne $marker)) { $CallerEnvSnapshot[$k] = $v }
}

# Quote-aware value parse: a quoted value keeps everything inside the quotes
# ('#' included) and anything after the closing quote is ignored; an unquoted
# value ends at the first '#' that starts the value or follows whitespace
# (so 'KEY= # note' and 'KEY=<tab>#x' are empty, as in load-local.sh).
# A backslash does not escape a quote: "a\"b" yields a\ (closing quote is the
# first one), unlike the pre-rewrite trim-based parser which returned a\"b.
# Escapes were never documented for .env files here; avoid embedded quotes.
function ConvertFrom-LocalEnvValue {
    param([string]$Raw)
    $v = $Raw.Trim()
    if ($v.Length -gt 0 -and ($v[0] -eq '"' -or $v[0] -eq "'")) {
        $quote = $v[0]
        $end = $v.IndexOf($quote, 1)
        if ($end -gt 0) { return $v.Substring(1, $end - 1) }
        return $v.Substring(1)
    }
    if ($v.StartsWith('#')) { return '' }
    $m = [regex]::Match($v, '\s#')
    if ($m.Success) { $v = $v.Substring(0, $m.Index) }
    return $v.Trim()
}

function Import-LocalEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $eq = $line.IndexOf('=')
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        if (-not $key) { return }
        if ($CallerEnvSnapshot.ContainsKey($key)) { return }
        $val = ConvertFrom-LocalEnvValue ($line.Substring($eq + 1))
        Set-Item -Path "env:$key" -Value $val
        if ($CallerWinsKeys -contains $key) {
            Set-Item -Path "env:ORAMA_LOADLOCAL_SET_$key" -Value $val
        }
    }
}

Import-LocalEnvFile (Join-Path $RepoRoot '.env')
Import-LocalEnvFile (Join-Path $RepoRoot '.env.local')

$homeEnv = Join-Path $HOME '.orama-system\env'
Import-LocalEnvFile $homeEnv
