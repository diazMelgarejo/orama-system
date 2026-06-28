# Hermes Windows Partner Readiness

Ensure all partner CLIs are dispatchable from the Windows host before starting a council session.

## Readiness Canaries

| Tool | Verification Command | Expected Outcome |
|---|---|---|
| **Codex** | `codex --version` | `codex-cli` version string |
| **cursor-agent** | `cursor-agent --version` | Version string (e.g. `2026.06.24-…`) |
| **Hermes** | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model stepfun/step-3.7-flash:free --max-turns 1` | `HERMES_READY` |
| **Gemini CLI** | `gemini -p "Reply with exactly: GEMINI_READY"` | `GEMINI_READY` |
| **AGY** | `agy --print "Reply with exactly: AGY_READY"` | Visible `AGY_READY` stdout |
| **LM Studio** | `/v1/models` + fast chat completions canary | Valid JSON and prompt response |

### AGY Quota Failure Mode
If `agy --print` exits with status 0 but empty stdout, run once with `--log-file <path>`. If the log shows "HTTP 429: Quota exhausted," the tool is installed but unavailable until quota resets or another model/account is selected.

### LM Studio Latency
Local models can be reachable but slow. If the completion canary (e.g., "Reply with exactly: READY") takes more than 15 seconds, the lane is considered **Unavailable for fast dispatch**.

### LM Studio Single-Model Constraint
LM Studio on **any** machine (Mac/Linux/Windows) can load **only one model at a time**. Loading a second model fails (e.g. `Failed to load model "gemma-4-e4b-it". Error: Operation canceled.`). Multiple models at once require **different remote machine IPs** (e.g. Mac LM Studio + Win LM Studio on LAN).

After a failed LM Studio canary, check server logs:
- Windows: `%USERPROFILE%\.lmstudio\server-logs`
- Mac/Linux: `~/.lmstudio/server-logs`
- Recent files: dated subdirs like `2026-06\2026-06-28.1.log`
- Quick tail: `python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --tail-lmstudio-logs`

## Path & Environment Setup

### Git Bash
Ensure `HERMES_GIT_BASH_PATH` is set to a real `bash.exe` (e.g., from GitHub Desktop or Git for Windows).

### PowerShell Encoding
Set console output to UTF-8 to prevent mojibake in skill file generation:
```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"
```

### Partner CLI PATH (Windows)

```powershell
.\platform\windows\ensure-partner-cli-paths.ps1
```

See [`windows-onboarding-config.md`](windows-onboarding-config.md) § Partner CLI Paths.

## Git sync (Mac ↔ Win)

Before council or LAN peer work with a dirty tree, use
[`../../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../../git-history-surgery/references/safe-cross-host-sync-reference-card.md)
— never `git reset --hard` or force-push `main`. Bootstrap Git first:
[`../../git-history-surgery/references/windows-powershell-runtime-bootstrap.md`](../../git-history-surgery/references/windows-powershell-runtime-bootstrap.md).
