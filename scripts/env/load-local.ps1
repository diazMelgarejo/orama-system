<#
.SYNOPSIS
    Load the gitignored repo env files (.env, then .env.local, then the per-user env file).

.DESCRIPTION
    Dot-source this script to export KEY=VALUE pairs into the current process
    environment. Files are read in order: .env and .env.local under the repo
    root, then the orama-system env file in the user profile. Later files
    override earlier ones. Idempotent: running it again re-applies the same
    values.

    PERPETUA_TOOLS_PATH and PERPETUA_TOOLS_ROOT are caller-wins keys: a value
    the caller set for this invocation is never overridden by a file. A value
    left over from a previous run of this script is not a caller choice (see the
    ORAMA_LOADLOCAL_SET_ markers below).

.PARAMETER RepoRoot
    Repo root holding .env and .env.local. Defaults to two levels above this
    script.
#>
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
    <#
    .SYNOPSIS
    Normalise a raw .env.local value (strip quotes and trailing comments).
    .PARAMETER Raw
    Text after the first equals sign of an env line.
    .OUTPUTS
    System.String: the unquoted value, or an empty string for a comment-only value.
    #>
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
    <#
    .SYNOPSIS
    Export every KEY=VALUE line of one env file into the process environment.
    .DESCRIPTION
    Skips a missing file, blank lines, comment lines and lines without a key.
    Caller-set keys captured in the snapshot are left untouched, and each value
    set for a caller-wins key is recorded in its ORAMA_LOADLOCAL_SET_ marker.
    .PARAMETER Path
    Env file to read.
    #>
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
