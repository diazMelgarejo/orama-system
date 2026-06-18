# Hermes Windows Partner Readiness

Ensure all partner CLIs are dispatchable from the Windows host before starting a council session.

## Readiness Canaries

| Tool | Verification Command | Expected Outcome |
|---|---|---|
| **Codex** | `codex --version` | `codex-cli` version string |
| **Hermes** | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --max-turns 1` | `HERMES_READY` |
| **Gemini CLI** | `gemini -p "Reply with exactly: GEMINI_READY"` | `GEMINI_READY` |
| **AGY** | `agy --print "Reply with exactly: AGY_READY"` | Visible `AGY_READY` stdout |
| **LM Studio** | `/v1/models` + fast chat completions canary | Valid JSON and prompt response |

### AGY Quota Failure Mode
If `agy --print` exits with status 0 but empty stdout, run once with `--log-file <path>`. If the log shows "HTTP 429: Quota exhausted," the tool is installed but unavailable until quota resets or another model/account is selected.

### LM Studio Latency
Local models can be reachable but slow. If the completion canary (e.g., "Reply with exactly: READY") takes more than 15 seconds, the lane is considered **Unavailable for fast dispatch**.

## Path & Environment Setup

### Git Bash
Ensure `HERMES_GIT_BASH_PATH` is set to a real `bash.exe` (e.g., from GitHub Desktop or Git for Windows).

### PowerShell Encoding
Set console output to UTF-8 to prevent mojibake in skill file generation:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```
