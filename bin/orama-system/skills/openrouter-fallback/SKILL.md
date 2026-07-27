---
name: openrouter-fallback
description: >-
  OpenRouter cloud fallback for when local models are unavailable.
  Ultimate failover (5 of 5) when ClinePass, LM Studio, Ollama, and GLM-5.2 are all down.
version: 1.0.0
license: Apache 2.0
compatibility: openrouter, claude-code, openai, gpt-4o
agent_compatibility:
  - Codex
  - OpenClaw
  - Claude
  - Subagents
layer: "Fallback 5 of 5 — Cloud (OpenRouter GPT-4o, after Ollama/LM Studio/GLM-5.2)"
upstream: https://openrouter.ai
upstream_path: $OPENROUTER_ENDPOINT
origin: OpenClaw ultimate fallback chain
triggers:
  - openrouter setup
  - fallback setup
  - cloud model fallback
  - when ollama is down
allowed-tools: bash, curl, file-operations
---

# OpenRouter Fallback

## Purpose

OpenRouter is the **5th and final fallback** in the OpenClaw model chain:
1. ClinePass (local Claude)
2. LM Studio (Windows GPU)
3. Ollama (Mac local)
4. GLM-5.2 (BigModel)
5. **OpenRouter (this)** ← cloud fallback, always available

When all local/regional models fail, agents queue tasks for OpenRouter (GPT-4o, Gemini, Claude via OpenRouter) as the ultimate safety net.

## Setup (One-Time)

```bash
bash $ORAMA_ROOT/bin/orama-system/skills/openrouter-fallback/setup-openrouter.sh
```

This:
1. Prompts for your OpenRouter API key
2. Stores it securely in `~/.openclaw/secrets/openrouter-api-key` (mode 600)
3. Creates `~/.openclaw/.env.openrouter` (sourced by shells; migrates legacy `openclaw-openrouter-env` if present)
4. Tests connectivity
5. Wires into shell profiles (~/.zshrc, ~/.bashrc)

**Status check:**
```bash
bash $ORAMA_ROOT/bin/orama-system/skills/openrouter-fallback/setup-openrouter.sh --status
```

## How It Works

### Environment Variables (Runtime, NOT Tracked)

```bash
# Auto-loaded by ~/.zshrc / ~/.bashrc after setup
source ~/.openclaw/.env.openrouter

# Then available to all scripts:
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
export OPENROUTER_MODEL=openai/gpt-4o
export OPENROUTER_TIMEOUT=120
```

### Curl Pattern (from scripts)

```bash
source ~/.openclaw/.env.openrouter

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: OPENROUTER_API_KEY is unset; run setup-openrouter.sh" >&2
  exit 1
fi

curl -X POST "$OPENROUTER_ENDPOINT" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"${OPENROUTER_MODEL}"'",
    "messages": [{"role": "user", "content": "your prompt"}]
  }'
```

### Node.js Pattern (from agents)

```javascript
const apiKey = process.env.OPENROUTER_API_KEY;
if (!apiKey) {
  throw new Error('OPENROUTER_API_KEY is unset; run setup-openrouter.sh');
}
const response = await fetch(process.env.OPENROUTER_ENDPOINT || 
  'https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: process.env.OPENROUTER_MODEL || 'openai/gpt-4o',
    messages: [{role: 'user', content: 'your prompt'}],
  }),
});
```

## Security Model

### What's Protected
- **API key stored securely:** `~/.openclaw/secrets/openrouter-api-key` (mode 600)
  - Not tracked in git
  - Only readable by owner
  - Sourced at runtime by shells

### What's Tracked
- **Setup script:** `setup-openrouter.sh` (tracked, no secrets)
- **Documentation:** This SKILL.md (tracked, no secrets)
- **Usage patterns:** In agent skills (tracked, references env vars, not hardcoded keys)

### Rotation
```bash
# To rotate the key:
bash $ORAMA_ROOT/bin/orama-system/skills/openrouter-fallback/setup-openrouter.sh
# Prompts to replace or keep existing key
```

## Fallback Chain Status (in start.sh & start.ps1)

After startup, all fallback tiers are printed:

```
✅ Model Fallback Chain Ready:
  1. ClinePass (local Claude) ............ [status]
  2. LM Studio (Win GPU) ................ [status]
  3. Ollama (Mac local) ................. [status]
  4. GLM-5.2 (BigModel) ................. [status]
  5. OpenRouter (cloud GPT-4o) .......... [status]
```

When tier 1–4 are DOWN, OpenRouter takes all queued tasks.

## Usage in Skills

Add to any skill that needs model fallback:

```bash
# Preamble
source ~/.openclaw/.env.openrouter 2>/dev/null || \
  { echo "WARN: OpenRouter not configured; run setup-openrouter.sh"; exit 1; }

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: OPENROUTER_API_KEY is unset after sourcing .env.openrouter" >&2
  exit 1
fi

# When fallback needed
if [ $primary_model_failed -eq 1 ]; then
  curl -X POST "$OPENROUTER_ENDPOINT" ...
fi
```

## Health Checks

Check if OpenRouter is working:

```bash
# Quick test
curl -s -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-4o","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' | jq .

# Or use status command
bash $ORAMA_ROOT/bin/orama-system/skills/openrouter-fallback/setup-openrouter.sh --status
```

## Cost & Rate Limits

- **Model:** openai/gpt-4o (via OpenRouter routing)
- **Rate limit:** OpenRouter default (depends on your plan)
- **Cost:** Per-token, billed by OpenRouter
- **Docs:** https://openrouter.ai/docs

**Best practice:** Only fallback to OpenRouter when local tiers fail; it's slower and costs money.

## Common Issues

| Issue | Fix |
|-------|-----|
| `curl: (401) Unauthorized` | API key is invalid or expired. Run setup script to replace it. |
| `curl: (429) Too Many Requests` | Rate limited. Check OpenRouter dashboard for quota. |
| `curl: (28) Operation timeout` | Request took >120s. Reduce max_tokens or increase OPENROUTER_TIMEOUT. |
| `env vars not loading` | Shell profile not sourced. Run `source ~/.zshrc` manually; then verify `echo $OPENROUTER_API_KEY`. |

## References

- **OpenRouter Dashboard:** https://openrouter.ai
- **API Docs:** https://openrouter.ai/docs
- **Fallback chain:** See start.sh § Model Fallback Status
- **GLM-5.2 pattern:** `bin/orama-system/skills/glm52-fallback/SKILL.md` (same security model)

---

## Status: PRODUCTION READY

OpenRouter fallback is wired into the default startup. After `setup-openrouter.sh`, it's transparent to agents: when all local models fail, agents automatically fallback to OpenRouter with zero code changes.


## Optional: Interactive Provider Setup

Idempotent, opt-in onboarding for provider selection (Claude, Codex,
Antigravity/Gemini, Cline, BigModel, Perplexity API) — same pattern vanilla
OpenClaw/Hermes onboarding uses.

- **Agent-mediated run:** use `AskUserQuestion` to pick a primary provider;
  already-configured providers are auto-added as fallback.
- **Human terminal:** `bash bin/orama-system/scripts/interactive-provider-setup.sh`
  (60s opt-in prompt, `[ -t 0 ]`-gated).
- **Non-interactive (CI/subagent):** skipped automatically; unset providers
  get `null` placeholders, never a blocking prompt.

Full doctrine: [`references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md)
