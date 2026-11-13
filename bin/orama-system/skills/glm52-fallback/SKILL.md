---
name: glm52-fallback
description: Sets up BigModel glm-5.3-flash as the system-wide fallback when ClinePass (Cline Credits) is unavailable. Uses the BigModel API at open.bigmodel.cn with env-var-only auth. Never hardcodes API keys.
trigger: "bash setup-glm52.sh"
version: 1.0.0
compatibility: openclaw, cline-cli, bigmodel-api
allowed-tools: Bash(bin/orama-system/skills/glm52-fallback/setup-glm52.sh *), curl, file-operations
triggers:
  - glm fallback
  - bigmodel fallback
  - setup-glm52
  - provider failover
when_to_use: Activates for glm-5.3-flash fallback setup, provider failover guidance, or verifying BigModel fallback configuration.
disable-model-invocation: true
effort: medium
paths:
  - "bin/orama-system/skills/glm52-fallback/**"
---

<!-- wandb-inference-working-config -->
## W&B inference

`invalid model ID` from the Cline CLI is stale provider metadata, not a
bad model id. `tokenSource` must be `manual` (or Cline's `oauth` or
`migration`) and `updatedAt` must be UTC with millisecond precision and a
trailing `Z`. Repair a shared entry with
`bin/orama-system/scripts/cline-provider-profiles/switch_cline_provider.py`.
When two routes run side by side, use
`bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py`.
Use the OpenAI client and Weave only if that error remains after the
metadata is current. Do not send a CoreWeave team/project string.
Shell-source the operator W&B env file before reading
`DEEPSEEK_V4_FLASH_WANDB`.


# glm-5.3-flash BigModel Fallback Skill

## Purpose

Create a system-wide fallback for all agents to use glm-5.3-flash via BigModel
(`https://open.bigmodel.cn`) when ClinePass is unavailable or Cline Credits
are exhausted.

Canonical folder — this is the only tracked copy of this skill:

```text
bin/orama-system/skills/glm52-fallback/
```

## Fallback Chain (system-wide)

```text
1. ClinePass (cline-pass/glm-5.3-flash via api.cline.bot)     ← DEFAULT (Cline Credits)
2. BigModel glm-5.3-flash (open.bigmodel.cn)                   ← FALLBACK (this skill)
3. OpenRouter free (openrouter/free auto-router)          ← LAST RESORT
4. Ollama local (qwen3.5 on Mac, localhost:11434)         ← OFFLINE
```

## Setup (Automated)

```bash
: "${GLM52_API_KEY:?Set GLM52_API_KEY before running setup-glm52.sh}"
export GLM52_API_KEY="${GLM52_API_KEY:?}"
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
- **Model**: `glm-5.3-flash`
- **Thinking**: Always on for glm-5.3-flash (it cannot be disabled; reasoning_content in response)
- **Reasoning effort**: send `"reasoning_effort": "high"` explicitly. Official BigModel docs
  (2026-11-12): glm-5.3-flash accepts only `low`, `high` and `max`, and the default is `max`,
  which the operator rule forbids. `medium` is rejected (HTTP 400, code 1210), so the rule
  medium, else high, else low lands on `high`. Never `xhigh` or `max`.
- **Context window**: 1M tokens (official). Older text here said 131072: that is the maximum output.
- **Max tokens**: default 65536, maximum 131072 (official); this skill requests 65536
- **Temperature**: 1.0

## Request Template

```bash
curl -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 10 --max-time 120 --retry 3 --retry-delay 2 \
  -d '{
    "model": "glm-5.3-flash",
    "messages": [{"role": "user", "content": "<USER_PROMPT>"}],
    "thinking": {"type": "enabled"},
    "reasoning_effort": "high",
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
      "id": "glm-5.3-flash",
      "name": "glm-5.3-flash (BigModel, thinking)",
      "contextWindow": 1000000,
      "maxTokens": 65536,
      "reasoning": true
    }]
  }
}
```

## Timeout & Retry Policy

- **Connect timeout**: 10s (fail fast on network issues)
- **Total timeout**: 120s (allow reasoning time; the Cline profile `bigmodel-glm53-flash` uses the same 120000 ms)
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

Report only setup status (e.g. "✓ glm-5.3-flash healthy" / "✗ glm-5.3-flash unreachable"). Do not print the credential value.

## Security

- **Never commit the API key.** Read from `$GLM52_API_KEY` or
  `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` env var only.
- The key file at `~/.openclaw/secrets/glm52-api-key` is mode 600 and
  git-ignored (`secrets/` in `.gitignore`).
- The key, and any private endpoint you override `GLM52_ENDPOINT` with (a proxy or internal
  host), live only in local-only files under `~/.openclaw/` — never in tracked files, logs,
  docs, PR text, screenshots, or tests. The public BigModel URL used in this skill and in
  its setup script is not secret.
- See `SECURITY.md` for the full credential hygiene policy.

## Boundaries

### Always Do

- Read the key only from `$GLM52_API_KEY` or `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY`.
- Report only setup status; confirm the runtime contract without ever printing
  the credential value.
- Keep the key and any private endpoint override in local-only files under `~/.openclaw/`
  (key file mode 600 and git-ignored).
- Apply the timeout and retry policy, and fall through to the next fallback on
  exit codes `7`, `28` and `52`.

### Ask First

- Changing the order of the system-wide fallback chain.
- Editing the `mac-orchestrator.json` provider block.

### Never Do

- Do not commit the API key or hardcode it anywhere.
- Do not put the key or a private endpoint override in tracked files, logs, docs,
  PR text, screenshots, or tests. The public BigModel URL documented here is not secret.
- Do not use BigModel ahead of ClinePass while Cline Credits remain; this skill
  is the fallback, not the default route.

## Optional: Interactive Provider Setup

This skill is the reference implementation for [`references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md) — the shared idempotent onboarding pattern for all LLM providers (Claude, Codex, Antigravity/Gemini, Cline, BigModel, Perplexity API).

## Related

- [cline-openclaw-agent](../cline-openclaw-agent/SKILL.md) — ClinePass default
- [mcp-orchestration](../mcp-orchestration/SKILL.md) — routing strategy
- [openrouter-defaults](../openclaw-skills/references/openrouter-defaults.md) — free tier fallback

## Evidence status (2026-11-12)

- OFFICIAL (BigModel docs, Chinese originals translated): effort levels and default, thinking
  forced on, 1M context, default/max output 65536/131072, price 0.8 in / 2.8 out CNY per 1M
  tokens, error codes 1113 (account in arrears, HTTP 429) and 1210 (invalid parameters, HTTP 400).
- LIVE: `glm-5.3-flash` appears in `GET /models`; `reasoning_effort: medium` returned HTTP 400
  (code 1210); every other call returned HTTP 429 code 1113 because the account has no balance.
  Real completions on BigModel were therefore NOT observed. The same model name on W&B
  (`zai-org/GLM-5.3-Flash`) accepted medium, high and low but takes 23-30 s per call.
- Legacy names kept on purpose: `GLM52_API_KEY`, the operator-local GLM52 secrets bundle
  (created by `setup-glm52.sh`), `setup-glm52.sh`, and this directory name predate the model
  rename; the model is `glm-5.3-flash`.
- Effort re-check cadence: the checked-in `high` is applied on every switch; medium, then high,
  then low is re-verified only periodically during a reviewed repository update (see the
  "Effort rule" section of `../cline-wandb/SKILL.md`). BigModel could not be probed live on
  2026-11-12 (no balance), so re-check it first once the account can be called.
