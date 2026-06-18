# 15. Hermes Windows Harness

**TL;DR:** On Windows, call Hermes through its venv launcher, export a literal
Git Bash path, and use an explicit provider/model for bounded one-shot partner
reviews.

---

## Root Cause

Hermes installed correctly under `%LOCALAPPDATA%\hermes`, but `hermes.exe` was
not on the active PowerShell `PATH`. The default provider was LM Studio with a
local model that was reachable but slow enough for `hermes -z` to time out.
Hermes terminal tools also need a real `bash.exe`; relying on a generic `bash`
lookup can miss GitHub Desktop's bundled Git Bash.

## Fix

Set the launcher and Git Bash paths before invoking Hermes:

```powershell
$hermesScripts = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts"
$env:PATH = "$hermesScripts;$env:PATH"

$gitBash = Get-ChildItem `
  "$env:LOCALAPPDATA\GitHubDesktop\app-*\resources\app\git\usr\bin\bash.exe" `
  -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1

if ($gitBash) {
  $env:HERMES_GIT_BASH_PATH = $gitBash.FullName
}
```

For bounded coding-partner prompts, route explicitly:

```powershell
hermes --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free `
  -z "Reply with exactly: HERMES_READY"
```

Use the default LM Studio route only after verifying the loaded model answers
quickly through the OpenAI-compatible local API.

## Verification

```powershell
hermes --version
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
hermes --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free `
  -z "Reply with exactly: HERMES_READY"
```

Pass criteria:

- `hermes.exe` resolves from `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts`.
- Git Bash prints `hermes-bash-ok`.
- Hermes one-shot prints `HERMES_READY` without starting an interactive TUI.

## Rules

1. Do not assume `hermes` is globally on `PATH` after install.
2. Do not leave `HERMES_GIT_BASH_PATH` implicit on Windows.
3. Prefer explicit provider/model routing for one-shot partner prompts.
4. Do not copy raw `%LOCALAPPDATA%\hermes` state, secrets, or personal memory
   into tracked repo files.
5. Keep durable behavior in canonical orama/ECC skills; keep Hermes files thin.

## Related

- [Hermes harness skill](../../bin/orama-system/skills/hermes-harness/SKILL.md)
- [ECC Hermes cross-harness notes](../../bin/orama-system/skills/hermes-harness/references/ecc-hermes-cross-harness.md)
- [Session log entry](../LESSONS.md)
