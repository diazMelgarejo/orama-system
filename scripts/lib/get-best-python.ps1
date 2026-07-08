# scripts/lib/get-best-python.ps1 — shared venv-aware Python resolver
#
# Dot-source this instead of calling bare `python` / `python3` / `py`.
# Bare `python` resolves whatever happens to be first on PATH at the moment
# the calling script runs — under Task Scheduler that is NOT guaranteed to be
# the repo's own .venv, and a script can silently run against a Python that
# is missing requirements.txt packages while looking like a real failure
# (e.g. "missing websockets" when it's actually installed, just in a
# different interpreter). Verified live: coord_pulse.ps1's bare `python`
# calls hit exactly this on a real Windows node.
#
# Canonical logic mirrors platform/windows/start.ps1's inline Get-BestPython
# (kept there as-is to avoid re-testing a proven-stable file for this fix;
# every OTHER script in this family should dot-source this shared copy
# instead of re-implementing it).
#
# Usage:
#   . (Join-Path $PSScriptRoot "..\lib\get-best-python.ps1")   # adjust relative path to repo scripts/lib
#   $PythonExe = Get-BestPython $RepoRoot

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
