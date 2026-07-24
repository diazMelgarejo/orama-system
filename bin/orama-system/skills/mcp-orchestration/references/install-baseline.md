# Install Baseline

> Extracted from `mcp-orchestration/SKILL.md` §3 during the 2026-07-22
> skill-trimming pass. Run once per machine; see `SKILL.md` §12 for the
> post-install verification checklist.

Use Node.js 20+ when using both Gemini MCP Tool and ai-cli-mcp.

```bash
node -v
npm -v
```

## Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude doctor
```

For ai-cli-mcp Claude workers, run once manually:

```bash
claude --dangerously-skip-permissions
```

This accepts prompts so background Claude subprocesses do not hang.

### Verify Claude auth (REQUIRED before dispatching Claude workers)

Before routing work to Claude, verify auth through the exact binary the orchestrator will use:

```bash
which claude
claude --version
claude auth status --text
claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"
```

If `claude -p` reports `Not logged in` after a login attempt, assume the auth flow may have been sandbox-blocked until proven otherwise. Claude's OAuth flow needs a local callback server and host credential persistence. Run login outside the sandbox or with explicit escalation:

```bash
claude auth login --claudeai
claude auth status --text
claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"
```

If login prints success but `auth status` remains false, inspect a debug log:

```bash
claude --debug --debug-file /tmp/claude-auth-debug.log auth login --claudeai
sed -n '1,120p' /tmp/claude-auth-debug.log
```

`Failed to start OAuth callback server` is a sandbox/auth-environment failure, not a normal stale session. Escalate the auth command instead of looping.

If the machine has both native and npm-global Claude installs, compare `which claude`, `claude --version`, and known full paths. Use one exact binary for login, status, and `-p` probes.

## Install Gemini CLI

```bash
npm install -g @google/gemini-cli
gemini auth login
gemini --version
```

**Non-interactive subagent dispatch (verified 2026-06-14; updated 2026-06-18):** prefer the
**Antigravity** CLI (`agy -p "/goal <task>"`) as the successor path for general Gemini-style
agent dispatch. `gemini -p "/goal <task>"` remains useful when Gemini CLI is explicitly
authenticated or needed for Gemini-Analyzer use-cases. `agy` is multi-model (Gemini 3.x /
Claude Sonnet+Opus 4.6 / GPT-OSS 120B; list with `agy models`) and should be bounded like
any other worker: no commits, deletes, deploys, or account changes without explicit user
confirmation. On native Windows, save the installer first (never pipe to `iex`):
`Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile "$env:TEMP\agy-install.ps1"`;
skim the first 40 lines, then run with `-ExecutionPolicy Bypass`. Treat AGY as ready only after `agy --print "Reply with exactly: AGY_READY"`
emits visible stdout; exit 0 with empty stdout is not a usable worker. Full command guide:
`agy-gemini.md` at the workspace root. Dispatch lanes,
model picks, and bounding (`gtimeout`, never `sleep` chains) are in
[`../../code-review/references/orchestration-dispatch.md`](../../code-review/references/orchestration-dispatch.md).

If AGY exits 0 with empty stdout, rerun once with `--log-file <path>` before
debugging PATH or shell quoting. On Windows this can mean silent auth succeeded
but the hosted model call failed with quota exhaustion; in that case AGY is
installed but not dispatchable until quota resets or another authenticated
model/account is selected. Do not loop on `agy -p` without checking the log.

## Install Codex CLI (optional, Codex worker support)

```bash
npm install -g @openai/codex
codex login
```

## Install Hermes Agent (operator shell support)

Use [`../../hermes-harness/SKILL.md`](../../hermes-harness/SKILL.md) for the
Windows-aware bring-up. Hermes consumes canonical ECC/orama skills and bounded
partner prompts; it must not become a source of copied private state. Keep
OpenClaw operations on `openclaw-skills`.

## Install ai-cli-mcp

```bash
npm install -g ai-cli-mcp
ai-cli doctor
ai-cli models
```

## Install ollama (for local-priority routing per Rule 1)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b-nvfp4   # Mac default model
ollama serve                    # listens on localhost:11434
```
