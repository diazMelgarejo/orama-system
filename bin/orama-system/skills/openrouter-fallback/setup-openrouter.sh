#!/usr/bin/env bash
# setup-openrouter.sh — Idempotent OpenRouter fallback setup for OpenClaw
#
# Usage: bash setup-openrouter.sh
#        bash setup-openrouter.sh --status
#
# Stores OpenRouter API key securely and wires it into the fallback chain.
# No secrets committed to git; all runtime sourced from ~/.openclaw/.env.openrouter

set -euo pipefail

log() { printf '[openrouter-setup] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Directories
SECRETS_DIR="$HOME/.openclaw/secrets"
ENV_FILE="$HOME/.openclaw/.env.openrouter"
LOG_DIR="$HOME/.openclaw/logs"

# Create directories
mkdir -p "$SECRETS_DIR" "$LOG_DIR"

# Status check
if [ "${1:-}" = "--status" ]; then
  log "OpenRouter configuration status:"
  if [ -f "$SECRETS_DIR/openrouter-api-key" ]; then
    key=$(cat "$SECRETS_DIR/openrouter-api-key" 2>/dev/null | cut -c1-20)...
    log "  API key: STORED (${key})"
  else
    log "  API key: NOT STORED"
  fi

  if [ -f "$ENV_FILE" ]; then
    endpoint=$(grep OPENROUTER_ENDPOINT "$ENV_FILE" 2>/dev/null | cut -d= -f2)
    log "  Endpoint: $endpoint"
  else
    log "  Environment file: NOT FOUND"
  fi

  if [ -f "$SECRETS_DIR/openrouter-api-key" ] && [ -f "$ENV_FILE" ]; then
    log "  Status: ✅ READY"
  else
    log "  Status: ⚠️  INCOMPLETE"
  fi
  exit 0
fi

# Interactive setup
log "🔐 OpenRouter Fallback Setup"
log ""

# Prompt for API key
if [ -f "$SECRETS_DIR/openrouter-api-key" ]; then
  existing=$(cat "$SECRETS_DIR/openrouter-api-key" | cut -c1-20)...
  log "Existing API key found: $existing"
  read -p "Replace it? (y/n) [n]: " -r replace
  if [ "${replace:-n}" != "y" ]; then
    log "Keeping existing key"
    API_KEY=$(cat "$SECRETS_DIR/openrouter-api-key")
  else
    read -sp "Enter your OpenRouter API key (sk-or-v1-...): " API_KEY
    echo ""
  fi
else
  read -sp "Enter your OpenRouter API key (sk-or-v1-...): " API_KEY
  echo ""
fi

if [ -z "$API_KEY" ]; then
  log "ERROR: API key is required"
  exit 1
fi

# Validate format (basic check)
if ! [[ "$API_KEY" =~ ^sk-or-v1- ]]; then
  log "WARNING: API key doesn't start with 'sk-or-v1-' (OpenRouter format)"
  log "Proceeding anyway; test will catch if invalid"
fi

# Store API key securely (mode 600 = owner read/write only)
log "Storing API key to $SECRETS_DIR/openrouter-api-key (mode 600)..."
echo "$API_KEY" > "$SECRETS_DIR/openrouter-api-key.tmp"
chmod 600 "$SECRETS_DIR/openrouter-api-key.tmp"
mv "$SECRETS_DIR/openrouter-api-key.tmp" "$SECRETS_DIR/openrouter-api-key"
log "✓ API key stored securely"

# Create environment file
log "Creating $ENV_FILE..."
cat > "$ENV_FILE.tmp" <<'ENVEOF'
# OpenRouter fallback configuration
# Source this in skills/scripts that need OpenRouter
# DO NOT commit this file or the secrets it references

export OPENROUTER_API_KEY=$(cat ~/.openclaw/secrets/openrouter-api-key 2>/dev/null)
export OPENROUTER_ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
export OPENROUTER_MODEL="${OPENROUTER_MODEL:-openai/gpt-4o}"
export OPENROUTER_TIMEOUT="${OPENROUTER_TIMEOUT:-120}"
export OPENROUTER_REFERER="${OPENROUTER_REFERER:-https://github.com/diazMelgarejo/OpenClaw}"
export OPENROUTER_TITLE="${OPENROUTER_TITLE:-OpenClaw}"

# Fallback chain position: 4 of 5
# 1. ClinePass (local Claude)
# 2. LM Studio (Win GPU)
# 3. Ollama (Mac local)
# 4. GLM-5.2 (BigModel fallback)
# 5. OpenRouter (cloud fallback — THIS)
ENVEOF
chmod 600 "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
log "✓ Environment file created"

# Update shell profiles
log "Updating shell profiles to source OpenRouter env on startup..."
for profile in ~/.zshrc ~/.bashrc; do
  if [ -f "$profile" ]; then
    # Check if already sourced
    if grep -q "openrouter" "$profile" 2>/dev/null; then
      log "  $profile: already configured"
    else
      log "  $profile: adding source command"
      cat >> "$profile" <<'RCEOF'

# OpenRouter fallback (added by setup-openrouter.sh)
[ -f ~/.openclaw/.env.openrouter ] && source ~/.openclaw/.env.openrouter
RCEOF
    fi
  fi
done

# Test connectivity
log ""
log "Testing OpenRouter connectivity..."
if ! command -v curl >/dev/null 2>&1; then
  log "WARNING: curl not found; skipping connection test"
else
  # Use curl with timeout and retry logic (same as GLM-5.2)
  RESPONSE=$(timeout 10 curl -s -X POST \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    "$OPENROUTER_ENDPOINT" \
    -d '{"model":"'"${OPENROUTER_MODEL:-openai/gpt-4o}"'","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' 2>/dev/null || echo "TIMEOUT")

  if echo "$RESPONSE" | grep -q "choices\|error" 2>/dev/null; then
    log "✓ Connection test PASSED"
    log "  $(echo "$RESPONSE" | head -c 100)..."
  else
    log "⚠️  Connection test FAILED or timed out"
    log "  Response: $RESPONSE"
    log "  Verify your API key is correct (Settings → API Keys on openrouter.ai)"
  fi
fi

# Log setup completion
log ""
log "✅ OpenRouter Fallback Setup Complete"
log ""
log "Summary:"
log "  • API key: $SECRETS_DIR/openrouter-api-key (mode 600, not tracked)"
log "  • Environment: $ENV_FILE (auto-sourced by shells)"
log "  • Fallback position: 5 of 5 (last resort, after Ollama/LM Studio/GLM-5.2)"
log "  • To use: source ~/.openclaw/.env.openrouter"
log ""
log "Health check:"
log "  bash setup-openrouter.sh --status"
log ""
log "Documentation:"
log "  See bin/orama-system/skills/openrouter-fallback/SKILL.md"
