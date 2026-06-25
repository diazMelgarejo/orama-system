# Hermes Windows Partner Readiness

Ensure all partner CLIs are dispatchable from the Windows host before starting a council session.

## Readiness Canaries

| Tool | Verification Command | Expected Outcome |
|---|---|---|
| **Codex** | `codex --version` | `codex-cli` version string |
| **Hermes** | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --max-turns 1` | `HERMES_READY` |
| **Gemini CLI** | ~~`gemini -p "..."`~~ — **retired 2026-06-18; returns `IneligibleTierError`** | Use AGY instead |
| **AGY** | `agy --print "Reply with exactly: AGY_READY"` | Visible `AGY_READY` stdout |
| **LM Studio** | `/v1/models` + fast chat completions canary | Valid JSON and prompt response |

### AGY Usage (non-interactive / orchestrator mode)

```bash
# One-shot (non-interactive, safe for subagent dispatch)
agy --print "Reply with exactly: AGY_READY"

# Full task with permission bypass (required in non-TTY orchestrators)
agy -p "your task" --dangerously-skip-permissions

# With explicit workspace directory
agy --dir /path/to/repo -p "your task"
```

> See `agy-gemini.md` at repo root for the full `invoke_agent` persona dispatch table
> (`codebase_investigator`, `generalist`, `cli_help`).

### AGY Quota Failure Mode
If `agy --print` exits with status 0 but empty stdout, run once with `--log-file <path>`. If the log shows "HTTP 429: Quota exhausted," the tool is installed but unavailable until quota resets or another model/account is selected.

### LM Studio Latency
Local models can be reachable but slow. If the completion canary (e.g., "Reply with exactly: READY") takes more than 15 seconds, the lane is considered **Unavailable for fast dispatch**.

### LM Studio Cross-Platform Model Listing

`/v1/models` lists ALL models known to LM Studio, regardless of hardware
compatibility. On Windows, the list may include Mac-only MLX models (confirmed:
`qwen3.5-9b-mlx` appears in Windows LM Studio alongside GGUF models).

**Filtering before dispatch:**

```powershell
# List loaded models — filter to GGUF-compatible (exclude mlx, metal, coreml)
$models = (Invoke-RestMethod http://localhost:1234/v1/models).data
$windowsModels = $models | Where-Object {
    $_.id -notmatch '(?i)mlx|metal|coreml'
}
$windowsModels | Select-Object id
```

Always run the PT hardware policy check against the result — never dispatch to a
`windows_only`-unconfirmed model based on `/v1/models` presence alone.

See [`lan-endpoint-contract.md`](lan-endpoint-contract.md) for the full locality rule.

## Path & Environment Setup

### Git Bash
Ensure `HERMES_GIT_BASH_PATH` is set to a real `bash.exe` (e.g., from GitHub Desktop or Git for Windows).

### PowerShell Encoding
Set console output to UTF-8 to prevent mojibake in skill file generation:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```
