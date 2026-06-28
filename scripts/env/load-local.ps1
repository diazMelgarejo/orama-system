# load-local.ps1 — Load gitignored repo env (.env then .env.local). Idempotent.
param(
    [string]$RepoRoot = ''
)

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Import-LocalEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = ($_ -split '#', 2)[0].Trim()
        if (-not $line -or $line -notmatch '=') { return }
        $key, $val = $line -split '=', 2
        $key = $key.Trim()
        $val = $val.Trim().Trim('"').Trim("'")
        if ($key) { Set-Item -Path "env:$key" -Value $val }
    }
}

Import-LocalEnvFile (Join-Path $RepoRoot '.env')
Import-LocalEnvFile (Join-Path $RepoRoot '.env.local')

$homeEnv = Join-Path $HOME '.orama-system\env'
Import-LocalEnvFile $homeEnv
