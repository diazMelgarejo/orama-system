# 15. Hermes Windows Harness

**TL;DR:** On Windows, call Hermes through its venv launcher, export a literal
Git Bash path, and use an explicit provider/model for bounded one-shot partner
reviews.

---

## Root Cause

Hermes installed correctly under `%LOCALAPPDATA%\hermes`, but `hermes.exe` was
not on the active PowerShell `PATH`. The default provider was LM Studio with a
local model that was reachable but slow enough for `hermes chat` to time out.
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
} else {
  throw "Could not find GitHub Desktop Git Bash under $env:LOCALAPPDATA\GitHubDesktop; set HERMES_GIT_BASH_PATH manually to any bash.exe (e.g. from Git for Windows or WSL2 via %LOCALAPPDATA%\hermes\git\usr\bin\bash.exe installed by the Hermes installer)."
}
```

For bounded coding-partner prompts, route explicitly:

```powershell
hermes chat --query "Reply with exactly: HERMES_READY" --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
```

Use the default LM Studio route only after verifying the loaded model answers
quickly through the OpenAI-compatible local API.

### LM Studio single-model invariant

LM Studio on **any** machine loads **one model at a time**. A second load fails
(e.g. `Failed to load model "gemma-4-e4b-it". Error: Operation canceled.`).
Run multiple models only across **different machine IPs** (Mac LM Studio +
Win LM Studio on LAN).

After a failed LM Studio canary, check server logs at
`%USERPROFILE%\.lmstudio\server-logs` (Windows) or `~/.lmstudio/server-logs`
(Mac/Linux) — dated subdirs like `2026-06\2026-06-28.1.log` — or tail quickly:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --tail-lmstudio-logs
```

Install AGY/Antigravity on native Windows (save-first — never pipe remote script to `iex`):

```powershell
Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile "$env:TEMP\agy-install.ps1"
Get-Content "$env:TEMP\agy-install.ps1" | Select-Object -First 40
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\agy-install.ps1"
agy --version
agy --print "Reply with exactly: AGY_READY"
```

Treat AGY as dispatchable only if the print canary emits visible stdout.
If the command exits 0 with no output, rerun with `--log-file <path>`. A log
showing silent auth followed by hosted-model quota exhaustion means the CLI and
auth are present, but AGY is not currently a usable worker.

Install PT-orama local Hermes slash-command wrappers from the canonical repo:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
hermes skills list --source local
```

Expected wrappers: `/pt-orama-council`, `/pt-orama-review`, and
`/pt-orama-delegate`. These wrappers point back to canonical orama-system skill
paths under `bin/orama-system/skills/hermes-harness/commands/` and must not
contain copied canonical bodies or private Hermes state.

## Verification

```powershell
hermes --version
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
hermes chat --query "Reply with exactly: HERMES_READY" --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
agy --print "Reply with exactly: AGY_READY"
```

Pass criteria:

- `hermes.exe` resolves from `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts`.
- Git Bash prints `hermes-bash-ok`.
- Hermes one-shot prints `HERMES_READY` without starting an interactive TUI.
- AGY prints `AGY_READY`; exit 0 with empty stdout is not readiness.
- Gemini CLI answers a small `--prompt` probe only after it has a selected auth
  method; Antigravity OAuth metadata alone may not satisfy Gemini CLI auth.

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
