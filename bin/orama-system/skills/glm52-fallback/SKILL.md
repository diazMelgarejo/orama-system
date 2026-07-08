---
name: glm52-fallback
description: Sets up BigModel GLM-5.2 as the system-wide fallback when ClinePass (Cline Credits) is unavailable. Uses the BigModel API at open.bigmodel.cn with env-var-only auth. Never hardcodes API keys.
trigger: "bash setup-glm52.sh"
---

# GLM-5.2 BigModel Fallback Skill

Create a system-wide fallback for all agents to use GLM-5.2 via BigModel
(`https://open.bigmodel.cn`) when ClinePass is unavailable or Cline Credits
are exhausted.

## Fallback Chain (system-wide)

```
1. ClinePass (cline-pass/glm-5.2 via api.cline.bot)     ← DEFAULT (Cline Credits)
2. BigModel GLM-5.2 (open.bigmodel.cn)                   ← FALLBACK (this skill)
3. OpenRouter free (openrouter/free auto-router)          ← LAST RESORT
4. Ollama local (qwen3.5 on Mac, localhost:11434)         ← OFFLINE
```

## Setup (Automated)

```bash
bash setup-glm52.sh
```

This script will:
1. Read the API key from `$GLM52_API_KEY` or `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` env var (or prompt if unset)
2. Store it securely at `~/.openclaw/secrets/glm52-api-key` (mode 600)
3. Create env config at `~/.openclaw/.env.glm52` (mode 600)
4. Add sourcing to `~/.zshrc` and `~/.bashrc`
5. Test connection to the BigModel endpoint

> **NEVER hardcode the API key in tracked files.** Read from environment
> variables only. See `SECURITY.md` — "Read keys from environment variables,
> not source or tracked config."

## Setup (Manual)

```bash
# 1. Store API key securely (not in tracked files)
mkdir -p ~/.openclaw/secrets
printf '%s' "$GLM52_API_KEY" > ~/.openclaw/secrets/glm52-api-key
chmod 600 ~/.openclaw/secrets/glm52-api-key

# 2. Configure environment
cat > ~/.openclaw/.env.glm52 <<'EOF'
export GLM52_API_KEY=$(cat ~/.openclaw/secrets/glm52-api-key)
export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"
EOF
chmod 600 ~/.openclaw/.env.glm52

# 3. Activate + make permanent
source ~/.openclaw/.env.glm52
echo "source ~/.openclaw/.env.glm52 2>/dev/null || true" >> ~/.zshrc
```

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

## Security

- **Never commit the API key.** Read from `$GLM52_API_KEY` or
  `$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` env var only.
- The key file at `~/.openclaw/secrets/glm52-api-key` is mode 600 and
  git-ignored (`secrets/` in `.gitignore`).
- See `SECURITY.md` for the full credential hygiene policy.

## Related

- [cline-openclaw-agent](../cline-openclaw-agent/SKILL.md) — ClinePass default
- [mcp-orchestration](../mcp-orchestration/SKILL.md) — routing strategy
- [openrouter-defaults](../openclaw-skills/references/openrouter-defaults.md) — free tier fallback
