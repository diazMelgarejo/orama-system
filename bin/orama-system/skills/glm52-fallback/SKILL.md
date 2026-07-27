---
name: glm52-fallback
description: Sets up BigModel GLM-5.2 as the system-wide fallback when ClinePass (Cline Credits) is unavailable. Uses the BigModel API at open.bigmodel.cn with env-var-only auth. Never hardcodes API keys.
trigger: "bash setup-glm52.sh"
when_to_use: Activates for GLM-5.2 fallback setup, provider failover guidance, or verifying BigModel fallback configuration.
disable-model-invocation: true
effort: medium
paths:
  - "bin/orama-system/skills/glm52-fallback/**"
---

# GLM-5.2 BigModel Fallback Skill

Create a system-wide fallback for all agents to use GLM-5.2 via BigModel
(`https://open.bigmodel.cn`) when ClinePass is unavailable or Cline Credits
are exhausted.

Canonical folder — this is the only tracked copy of this skill:

```text
bin/orama-system/skills/glm52-fallback/
```

## Fallback Chain (system-wide)

```text
1. ClinePass (cline-pass/glm-5.2 via api.cline.bot)     ← DEFAULT (Cline Credits)
2. BigModel GLM-5.2 (open.bigmodel.cn)                   ← FALLBACK (this skill)
3. OpenRouter free (openrouter/free auto-router)          ← LAST RESORT
4. Ollama local (qwen3.5 on Mac, localhost:11434)         ← OFFLINE
```

## Setup (Automated)

```bash
export GLM52_API_KEY="<BigModel.API.key>"
bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh
```

This script will:
1. Require `$GLM52_API_KEY` (or `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY`) to already be set in the environment — fails fast with a clear error instead of prompting interactively, so it is safe to run unattended or in CI.
2. Store it securely at the operator openclaw secrets directory (mode 600; path written by `setup-glm52.sh`)
3. Create the operator-local GLM52 env bundle (mode 600; same script)
4. **Opt-in only:** wires env config into zsh/bash profiles when `GLM52_PERSIST_SHELL_PROFILE=1` (runtime `start.sh` already sources the GLM52 env bundle)
5. Test connection to the BigModel endpoint

> **NEVER hardcode the API key in tracked files.** Read from environment
> variables only. See `SECURITY.md` — "Read keys from environment variables,
> not source or tracked config." Logs, docs, PR bodies, and tests must not
> print, quote, or store the credential value.

## Setup (Manual)

Prefer the automated script. If you must run steps by hand:

```bash
# Fail clearly before creating configuration from an empty value.
: "${GLM52_API_KEY:?Set GLM52_API_KEY before running these commands}"
bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh
```

The script creates the secrets file and operator-local env bundle (mode 600), with optional profile wiring when `GLM52_PERSIST_SHELL_PROFILE=1`.

## API Configuration

- **Endpoint**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **API Key**: `$GLM52_API_KEY` environment variable (never hardcode)
- **Model**: `glm-5.2`
- **Thinking**: Enabled (reasoning_content in response)
- **Max tokens**: 65536
- **Temperature**: 1.0

## Request Template

```bash
curl -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 10 --max-time 120 --retry 3 --retry-delay 2 \
  -d '{
    "model": "glm-5.2",
    "messages": [{"role": "user", "content": "<USER_PROMPT>"}],
    "thinking": {"type": "enabled"},
    "max_tokens": 65536,
    "temperature": 1.0
  }'
```

## OpenClaw Provider Config (mac-orchestrator.json pattern)

```jsonc
{
  "bigmodel": {
    "api": "openai-completions",
    "apiKey": "${env:OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY}",
    "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
    "models": [{
      "id": "glm-5.2",
      "name": "GLM-5.2 (BigModel, thinking)",
      "contextWindow": 131072,
      "maxTokens": 65536,
      "reasoning": true
    }]
  }
}
```

## Timeout & Retry Policy

- **Connect timeout**: 10s (fail fast on network issues)
- **Total timeout**: 120s (allow reasoning time)
- **Auto-retry**: 3 attempts, 2s backoff

**Exit codes:** `0` = success · `7` = connection failed → next fallback · `28` = timeout → next · `52` = empty reply → next

## Verification

Before or after running setup, confirm the runtime contract without ever printing the credential value:

```bash
if [ -n "${GLM52_API_KEY:-}" ] || [ -n "${OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY:-}" ]; then
  echo "BigModel API key is set"
fi
bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh
```

Report only setup status (e.g. "✓ GLM-5.2 healthy" / "✗ GLM-5.2 unreachable"). Do not print the credential value.

## Security

- **Never commit the API key.** Read from `$GLM52_API_KEY` or
  `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` env var only.
- The key file at `~/.openclaw/secrets/glm52-api-key` is mode 600 and
  git-ignored (`secrets/` in `.gitignore`).
- Runtime values (key, endpoint) live only in local-only files under
  `~/.openclaw/` — never in tracked files, logs, docs, PR text, screenshots,
  or tests.
- See `SECURITY.md` for the full credential hygiene policy.

## Optional: Interactive Provider Setup

This skill is the reference implementation for [`references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md) — the shared idempotent onboarding pattern for all LLM providers (Claude, Codex, Antigravity/Gemini, Cline, BigModel, Perplexity API).

## Related

- [cline-openclaw-agent](../cline-openclaw-agent/SKILL.md) — ClinePass default
- [mcp-orchestration](../mcp-orchestration/SKILL.md) — routing strategy
- [openrouter-defaults](../openclaw-skills/references/openrouter-defaults.md) — free tier fallback
