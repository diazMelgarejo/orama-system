#!/bin/bash
set -euo pipefail

printf '%s\n' "Configuring GLM-5.2 BigModel fallback for OpenClaw agents..."

# 1. Require the API key from env — fail fast instead of prompting
#    interactively (safe for unattended/CI use). NEVER hardcode it.
if [ -z "${GLM52_API_KEY:-}" ] && [ -n "${OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY:-}" ]; then
  GLM52_API_KEY="$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY"
fi
if [ -z "${GLM52_API_KEY:-}" ]; then
  printf '%s\n' "ERROR: GLM52_API_KEY must be set before running this script." >&2
  printf '%s\n' "Example: export GLM52_API_KEY='<BigModel.API.key>'" >&2
  exit 1
fi

mkdir -p "$HOME/.openclaw/secrets" "$HOME/.openclaw/logs"
printf '%s' "$GLM52_API_KEY" > "$HOME/.openclaw/secrets/glm52-api-key"
chmod 600 "$HOME/.openclaw/secrets/glm52-api-key"

# 2. Setup environment
cat > "$HOME/.openclaw/.env.glm52" <<'ENVEOF'
export GLM52_API_KEY=$(cat "$HOME/.openclaw/secrets/glm52-api-key")
export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"
ENVEOF
chmod 600 "$HOME/.openclaw/.env.glm52"

# 3. Add to shell profile (sourced at agent startup) — only for profiles
#    that already exist, and without duplicating the source line.
for profile in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [ -e "$profile" ] && ! grep -q "source ~/.openclaw/.env.glm52" "$profile" 2>/dev/null; then
    {
      printf '\n%s\n' "# GLM-5.2 BigModel fallback (added by glm52-fallback skill)"
      printf '%s\n' "source ~/.openclaw/.env.glm52 2>/dev/null || true"
    } >> "$profile"
    printf '%s\n' "Added GLM-5.2 fallback source line to $profile"
  fi
done

# 4. Test connection
printf '\n%s\n' "Testing GLM-5.2 connection..."
# shellcheck source=/dev/null
source "$HOME/.openclaw/.env.glm52"
curl -s -f -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 5 --max-time 30 \
  -d '{"model":"glm-5.2","messages":[{"role":"user","content":"ok"}],"max_tokens":10}' \
  | jq .choices[0].message.content 2>/dev/null && printf '%s\n' "✓ GLM-5.2 healthy" || printf '%s\n' "✗ GLM-5.2 unreachable (check credits at https://open.bigmodel.cn)"

printf '\n%s\n' "Setup complete. GLM-5.2 will be available to all agents on next startup."
printf '%s\n' "To activate now: source ~/.openclaw/.env.glm52"
