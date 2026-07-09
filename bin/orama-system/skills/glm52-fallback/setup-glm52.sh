#!/bin/bash
set -euo pipefail

printf '%s\n' "Configuring GLM-5.2 fallback for OpenClaw agents..."

if [ -z "${GLM52_API_KEY:-}" ]; then
  printf '%s\n' "ERROR: GLM52_API_KEY must be set before running this script." >&2
  printf '%s\n' "Example: export GLM52_API_KEY='<BigModel.API.key>'" >&2
  exit 1
fi

mkdir -p "$HOME/.openclaw/secrets" "$HOME/.openclaw/logs"
printf '%s\n' "$GLM52_API_KEY" > "$HOME/.openclaw/secrets/glm52-api-key"
chmod 600 "$HOME/.openclaw/secrets/glm52-api-key"

cat > "$HOME/.openclaw/.env.glm52" <<'ENVEOF'
export GLM52_API_KEY=$(cat "$HOME/.openclaw/secrets/glm52-api-key")
export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"
ENVEOF
chmod 600 "$HOME/.openclaw/.env.glm52"

for profile in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [ -e "$profile" ] && ! grep -q "source ~/.openclaw/.env.glm52" "$profile" 2>/dev/null; then
    {
      printf '\n%s\n' "# GLM-5.2 fallback (added by glm52-fallback skill)"
      printf '%s\n' "source ~/.openclaw/.env.glm52 2>/dev/null || true"
    } >> "$profile"
    printf '%s\n' "Added GLM-5.2 fallback source line to $profile"
  fi
done

printf '%s\n' "Setup complete. GLM-5.2 fallback is configured from GLM52_API_KEY."
printf '%s\n' "To activate now: source ~/.openclaw/.env.glm52"
