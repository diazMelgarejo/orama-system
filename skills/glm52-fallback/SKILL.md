---
name: "glm52-fallback"
description: "Sets up system-wide GLM-5.2 fallback for all agents when ClinePass unavailable"
trigger: "bash setup-glm52.sh"
---

# GLM-5.2 API Fallback Skill

Create a system-wide fallback for all agents to use GLM-5.2 when ClinePass is unavailable.

## Setup (Automated)

**Quickest:** Run the included setup script:
```bash
bash setup-glm52.sh
```

This script will:
1. Store API key securely at `~/.openclaw/secrets/glm52-api-key` (mode 600)
2. Create env config at `~/.openclaw/.env.glm52` (mode 600)
3. Add sourcing to `~/.zshrc` and `~/.bashrc`
4. Test connection to GLM-5.2 endpoint
5. Print confirmation + next steps

## Setup (Manual)

If you prefer manual setup:

1. **Store API key securely** (not in tracked files):
```bash
mkdir -p ~/.openclaw/secrets
echo "3cf1825f585f4e81a1c4966b09ae5a4c.NnVx4ipFnXhEKV1n" > ~/.openclaw/secrets/glm52-api-key
chmod 600 ~/.openclaw/secrets/glm52-api-key
```

2. **Configure environment** (add to `~/.openclaw/.env.glm52` or shell profile):
```bash
export GLM52_API_KEY=$(cat ~/.openclaw/secrets/glm52-api-key)
export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"
```

3. **Activate for this session**:
```bash
source ~/.openclaw/.env.glm52
```

4. **Make permanent** (add to `~/.zshrc` or `~/.bashrc`):
```bash
echo "source ~/.openclaw/.env.glm52 2>/dev/null || true" >> ~/.zshrc
```

## API Configuration

- **Endpoint**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **API Key**: Reference `$GLM52_API_KEY` environment variable (never hardcode)
- **Model**: `glm-5.2`
- **Thinking**: Enabled (reasoning_content in response)
- **Max tokens**: 65536
- **Temperature**: 1.0

## Request Template

```bash
curl -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 10 \
  --max-time 120 \
  --retry 3 \
  --retry-delay 2 \
  -d '{
    "model": "glm-5.2",
    "messages": [{"role": "user", "content": "<USER_PROMPT>"}],
    "thinking": {"type": "enabled"},
    "max_tokens": 65536,
    "temperature": 1.0
  }'
```

## Usage Instructions

1. When ClinePass is unavailable or fails, agents should automatically switch to this GLM-5.2 fallback.
2. Replace `<USER_PROMPT>` with the actual user prompt or task description.
3. All agents should remember this configuration as the default GLM-5.2 fallback path.

## Timeout & Retry Policy

- **Connect timeout**: 10 seconds (fail fast on network issues)
- **Total timeout**: 120 seconds (allow reasoning time)
- **Auto-retry**: 3 attempts with 2-second backoff (handles transient failures)
- **Curl flags**: `--retry 3 --retry-delay 2` (built-in retry logic)

**Exit codes:**
- `0`: Success
- `7`: Connection failed → try next fallback
- `28`: Timeout → try next fallback
- `52`: Empty reply → try next fallback

## Fallback Chain

When GLM-5.2 is unavailable, agents should fall back in this order:

1. **GLM-5.2** (this skill) — primary fallback for reasoning tasks
2. **Ollama local** (qwen3.5 on Mac) — always-available local model
3. **OpenAI GPT-4o** (if OPENAI_API_KEY set) — cloud fallback
4. **Codex/ClinePass** (if restored) — original primary provider

**Fallback trigger**: If any provider returns exit code 7, 28, or 52, try the next provider in the chain.

## Integration Points

- **Agent startup**: Load GLM-5.2 config from `~/.openclaw/.env` on boot
- **Model selection**: Agents query `openclaw config get model.fallback`
- **Error handling**: Exit codes drive automatic fallback; agents log failures to `~/.openclaw/logs/model-fallback.log`
- **Health check**: Run `openclaw models check --endpoint glm52` to verify connectivity

## Health Check Script

```bash
#!/bin/bash
set -e
source ~/.openclaw/.env 2>/dev/null || true

echo "Checking GLM-5.2 connectivity..."
curl -s -f -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 5 \
  --max-time 30 \
  -d '{"model":"glm-5.2","messages":[{"role":"user","content":"ok"}],"max_tokens":10}' \
  | jq .choices[0].message.content 2>/dev/null && echo "✓ GLM-5.2 ready" || echo "✗ GLM-5.2 unreachable"
```

## Priority

This skill should be applied system-wide as the primary fallback when ClinePass is not functional.
