#!/usr/bin/env bash
# Load OpenClaw secrets from macOS Keychain into environment variables.
# Source this file: source scripts/openclaw/load_keychain_secrets.sh
#
# If a secret is missing from Keychain, the var is not exported and a WARN
# is printed to stderr. Secrets from .env (already exported) are not overwritten.
#
# Usage:
#   source "$OPENCLAW_ROOT/orama-system/scripts/openclaw/load_keychain_secrets.sh"

set -euo pipefail

_kc_get() {
  local service="$1"
  /usr/bin/security find-generic-password -s "$service" -w 2>/dev/null || true
}

_kc_load() {
  local service="$1" var="$2"
  local val
  val=$(_kc_get "$service")
  if [ -n "$val" ]; then
    export "${var}=${val}"
  else
    echo "[load_keychain_secrets] WARN: keychain item '${service}' not found — ${var} not set" >&2
  fi
}

# Gemini
_kc_load "openclaw.gemini-main-apikey"     "OPENCLAW_MODELS_PROVIDERS_GEMINI_MAIN_APIKEY"
_kc_load "openclaw.gemini-fallback-apikey" "OPENCLAW_MODELS_PROVIDERS_GEMINI_FALLBACK_APIKEY"

# Telegram
_kc_load "openclaw.telegram-bot-token"     "OPENCLAW_TELEGRAM_BOT_TOKEN"

# Gateway
_kc_load "openclaw.gateway-auth-token"     "OPENCLAW_GATEWAY_AUTH_TOKEN"

unset -f _kc_get _kc_load
