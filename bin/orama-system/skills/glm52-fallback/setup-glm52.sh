#!/bin/bash
set -euo pipefail

printf '%s\n' "Configuring glm-5.3-flash BigModel fallback for OpenClaw agents..."

# 1. Require the API key from env — fail fast instead of prompting
#    interactively (safe for unattended/CI use). NEVER hardcode it.
if [ -z "${GLM52_API_KEY:-}" ] && [ -n "${OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY:-}" ]; then
  GLM52_API_KEY="$OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY"
fi
# A previous install stores the key in the operator environment file. Load it
# in this process before the fail-fast exit, which otherwise ignores that file.
if [ -z "${GLM52_API_KEY:-}" ] && [ -f "$HOME/.openclaw/.env.glm52" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.openclaw/.env.glm52"
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
# Caller-shell activator. The installer is a subprocess and cannot export
# back to its parent; the parent sources this file instead.
cat > "$HOME/.openclaw/glm52-activate.sh" <<'ACTIVATE'
# shellcheck source=/dev/null
source "$HOME/.openclaw/.env.glm52"
ACTIVATE
chmod 600 "$HOME/.openclaw/glm52-activate.sh"

# 3. Shell profile persistence is OPT-IN (GLM52_PERSIST_SHELL_PROFILE=1).
#    start.sh already sources ~/.openclaw/.env.glm52 at runtime, so profile
#    persistence is not required for the fallback to work — only add it
#    when the caller explicitly wants glm-5.3-flash available outside orama runs.
if [ "${GLM52_PERSIST_SHELL_PROFILE:-0}" = "1" ]; then
  for profile in "$HOME/.zshrc" "$HOME/.bashrc"; do
    if [ -e "$profile" ] && ! grep -q "source ~/.openclaw/.env.glm52" "$profile" 2>/dev/null; then
      {
        printf '\n%s\n' "# glm-5.3-flash BigModel fallback (added by glm52-fallback skill)"
        printf '%s\n' "source ~/.openclaw/.env.glm52 2>/dev/null || true"
      } >> "$profile"
      printf '%s\n' "Added glm-5.3-flash fallback source line to $profile"
    fi
  done
else
  printf '%s\n' "Skipping shell profile persistence (set GLM52_PERSIST_SHELL_PROFILE=1 to opt in); start.sh sources the fallback at runtime."
fi

# 4. Test connection
printf '\n%s\n' "Testing glm-5.3-flash connection..."
# shellcheck source=/dev/null
source "$HOME/.openclaw/.env.glm52"
if curl -s -f -X POST "$GLM52_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GLM52_API_KEY" \
  --connect-timeout 5 --max-time 30 \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"Reply with only OK."}],"max_tokens":512,"reasoning_effort":"high"}' \
  | jq -e '.choices[0].message.content | select(type == "string" and test("\\S"))' >/dev/null; then
  printf '%s\n' "✓ glm-5.3-flash healthy"
else
  printf '%s\n' "✗ glm-5.3-flash unreachable (check credits at https://open.bigmodel.cn)"
  printf '%s\n' "Fallback files were written, but the endpoint check failed." >&2
  exit 1
fi

printf '\n%s\n' "Setup complete. glm-5.3-flash will be available to all agents on next startup."
printf '%s\n' "To activate now: source ~/.openclaw/.env.glm52"
printf '%s\n' "Calling shell: source ~/.openclaw/glm52-activate.sh"
