#!/bin/bash
set -euo pipefail

echo "Configuring GLM-5.2 BigModel fallback for OpenClaw agents..."

# 1. Store API key securely — read from env var or prompt (NEVER hardcode)
mkdir -p ~/.openclaw/secrets ~/.openclaw/logs
if [ -n "${GLM52_API_KEY:-}" ]; then
  printf '%s' "$GLM52_API_KEY" > ~/.openclaw/secrets/glm52-api-key
elif [ -n "${OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY:-}" ]; then
  printf '%s' "$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY" > ~/.openclaw/secrets/glm52-api-key
else
  echo "Enter your BigModel GLM-5.2 API key (from https://open.bigmodel.cn):"
  read -r GLM52_KEY_INPUT
  [ -z "$GLM52_KEY_INPUT" ] && { echo "ERROR: no API key provided"; exit 1; }
  printf '%s' "$GLM52_KEY_INPUT" > ~/.openclaw/secrets/glm52-api-key
fi
chmod 600 ~/.openclaw/secrets/glm52-api-key

# 2. Setup environment
cat > ~/.openclaw/.env.glm52 <<'ENVEOF'
export GLM52_API_KEY=$(cat ~/.openclaw/secrets/glm52-api-key)
export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"
ENVEOF
chmod 600 ~/.openclaw/.env.glm52

# 3. Add to shell profile (sourced at agent startup)
if ! grep -q "source ~/.openclaw/.env.glm52" ~/.zshrc 2>/dev/null; then
  echo "" >> ~/.zshrc
  echo "# GLM-5.2 BigModel fallback (added by glm52-fallback skill)" >> ~/.zshrc
  echo "source ~/.openclaw/.env.glm52 2>/dev/null || true" >> ~/.zshrc
  echo "✓ Added to ~/.zshrc"
fi

if ! grep -q "source ~/.openclaw/.env.glm52" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "# GLM-5.2 BigModel fallback (added by glm52-fallback skill)" >> ~/.bashrc
  echo "source ~/.openclaw/.env.glm52 2>/dev/null || true" >> ~/.bashrc
  echo "✓ Added to ~/.bashrc"
fi

# 4. Test connection
echo ""
echo "Testing GLM-5.2 connection..."
# shellcheck source=/dev/null
source ~/.openclaw/.env.glm52
curl -s -f -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 5 --max-time 30 \
  -d '{"model":"glm-5.2","messages":[{"role":"user","content":"ok"}],"max_tokens":10}' \
  | jq .choices[0].message.content 2>/dev/null && echo "✓ GLM-5.2 healthy" || echo "✗ GLM-5.2 unreachable (check credits at https://open.bigmodel.cn)"

echo ""
echo "Setup complete. GLM-5.2 will be available to all agents on next startup."
echo "To activate now: source ~/.openclaw/.env.glm52"
