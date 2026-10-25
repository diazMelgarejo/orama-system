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
$CallerWinsKeys = @('PERPETUA_TOOLS_PATH', 'PERPETUA_TOOLS_ROOT')
$CallerEnvSnapshot = @{}
foreach ($k in $CallerWinsKeys) {
    $v = [Environment]::GetEnvironmentVariable($k, 'Process')
    if ($v) { $CallerEnvSnapshot[$k] = $v }
}

# Quote-aware value parse: a quoted value keeps everything inside the quotes
# ('#' included) and anything after the closing quote is ignored; an unquoted
# value ends at the first '#' that is preceded by whitespace.
function ConvertFrom-LocalEnvValue {
    param([string]$Raw)
    $v = $Raw.Trim()
    if ($v.Length -gt 0 -and ($v[0] -eq '"' -or $v[0] -eq "'")) {
        $quote = $v[0]
        $end = $v.IndexOf($quote, 1)
        if ($end -gt 0) { return $v.Substring(1, $end - 1) }
        return $v.Substring(1)
    }
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
    }
}

Import-LocalEnvFile (Join-Path $RepoRoot '.env')
Import-LocalEnvFile (Join-Path $RepoRoot '.env.local')

$homeEnv = Join-Path $HOME '.orama-system\env'
Import-LocalEnvFile $homeEnv
