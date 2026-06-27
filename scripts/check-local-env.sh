#!/usr/bin/env bash
# check-local-env.sh — Report OK/MISSING for local env catch-up (no secrets printed)
# Reference: docs/local-env-catch-up.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_LOCAL="$REPO_ROOT/.env.local"
OPENCLAW_ENV_LIB="$REPO_ROOT/bin/orama-system/scripts/lib/openclaw-env.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_failures=0
_warnings=0

_status() {
  local label="$1"
  local state="$2"
  case "$state" in
    OK) printf '  %-42s %bOK%b\n' "$label" "$GREEN" "$NC" ;;
    MISSING)
      printf '  %-42s %bMISSING%b\n' "$label" "$RED" "$NC"
      _failures=$((_failures + 1))
      ;;
    WARN)
      printf '  %-42s %bWARN%b\n' "$label" "$YELLOW" "$NC"
      _warnings=$((_warnings + 1))
      ;;
    SKIP) printf '  %-42s (skip)\n' "$label" ;;
  esac
}

_load_dotenv_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  # shellcheck disable=SC1090
  set -a
  # Export KEY=VAL lines; ignore comments and empty lines
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -n "$line" ] || continue
    case "$line" in
      *=*)
        key="${line%%=*}"
        val="${line#*=}"
        key="$(printf '%s' "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        val="$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")"
        [ -n "$key" ] && export "$key=$val"
        ;;
    esac
  done <"$f"
  set +a
}

_check_nonempty() {
  local name="$1"
  local val="${!name-}"
  if [ -n "${val// }" ]; then
    echo OK
  else
    echo MISSING
  fi
}

echo "Local env check — $REPO_ROOT"
echo ""

# Load repo dotenv (same order as scripts/env/load-local.sh / portal_server.py)
if [ -f "$REPO_ROOT/scripts/env/load-local.sh" ]; then
  # shellcheck source=env/load-local.sh
  source "$REPO_ROOT/scripts/env/load-local.sh"
else
  _load_dotenv_file "$REPO_ROOT/.env"
  _load_dotenv_file "$ENV_LOCAL"
fi

if [ -f "$REPO_ROOT/.env.local" ]; then
  _status ".env.local present" OK
elif [ -f "$REPO_ROOT/.env" ]; then
  _status ".env.local present" WARN
  echo "    (hint: cp .env.example .env.local for secrets after redaction)"
else
  _status ".env.local present" MISSING
  echo "    (hint: cp .env.example .env.local)"
fi

echo ""
echo "Layout:"

if [ -f "$OPENCLAW_ENV_LIB" ]; then
  # shellcheck source=bin/orama-system/scripts/lib/openclaw-env.sh
  source "$OPENCLAW_ENV_LIB"
  if detected="$(detect_openclaw_root 2>/dev/null || true)" && [ -n "$detected" ]; then
    _status "OPENCLAW_ROOT (detected)" OK
    echo "    → $detected"
  else
    _status "OPENCLAW_ROOT (detected)" MISSING
  fi
  if pt="$(detect_perpetua_tools_root 2>/dev/null || true)" && [ -n "$pt" ]; then
    _status "PERPETUA_TOOLS_ROOT (detected)" OK
    echo "    → $pt"
  else
    _status "PERPETUA_TOOLS_ROOT (detected)" WARN
  fi
else
  _status "openclaw-env.sh" MISSING
fi

if [ -n "${OPENCLAW_ROOT:-}" ]; then
  _status "OPENCLAW_ROOT (exported)" "$(_check_nonempty OPENCLAW_ROOT)"
fi
if [ -n "${PERPETUA_TOOLS_ROOT:-}" ]; then
  _status "PERPETUA_TOOLS_ROOT (exported)" "$(_check_nonempty PERPETUA_TOOLS_ROOT)"
fi

echo ""
echo "Secrets (required for config/mac-orchestrator.json placeholders):"

for var in \
  OPENCLAW_TELEGRAM_BOT_TOKEN \
  OPENCLAW_GATEWAY_AUTH_TOKEN \
  OPENCLAW_MODELS_PROVIDERS_GEMINI_MAIN_APIKEY \
  OPENCLAW_MODELS_PROVIDERS_GEMINI_FALLBACK_APIKEY; do
  state="$(_check_nonempty "$var")"
  _status "$var" "$state"
  if [ "$state" = "MISSING" ]; then
    echo "    → Add to $ENV_LOCAL (see .env.example)"
  fi
done

echo ""
echo "Recommended:"

if [ -n "${SETUP_PASSWORD// }" ]; then
  _status "SETUP_PASSWORD" OK
else
  _status "SETUP_PASSWORD" WARN
fi

echo ""
echo "Hardware (Mac — optional probe):"

if command -v curl >/dev/null 2>&1; then
  ollama_url="${OLLAMA_MAC_ENDPOINT:-http://127.0.0.1:11434}"
  ollama_url="${ollama_url%/}"
  if curl -sf --max-time 2 "${ollama_url}/api/tags" >/dev/null 2>&1; then
    _status "Ollama API ($ollama_url)" OK
    for model in qwen3.5:9b-nvfp4 bge-m3; do
      if curl -sf --max-time 2 "${ollama_url}/api/tags" | grep -q "$model"; then
        _status "  model $model" OK
      else
        _status "  model $model" WARN
      fi
    done
  else
    _status "Ollama API ($ollama_url)" WARN
  fi
else
  _status "Ollama API" SKIP
fi

echo ""
echo "LM Studio security:"

_lm_token="${LM_STUDIO_API_TOKEN:-}"
if [ -z "$(printf '%s' "$_lm_token" | tr -d '[:space:]')" ]; then
  _status "LM_STUDIO_API_TOKEN" WARN
  echo "    → Set a non-empty token in .env.local before production use"
elif [ "$_lm_token" = "lm-studio" ] || [ "$_lm_token" = "lmstudio" ]; then
  _status "LM_STUDIO_API_TOKEN (default dev value)" WARN
  echo "    → Rotate LM_STUDIO_API_TOKEN — public default is not safe for production"
else
  _status "LM_STUDIO_API_TOKEN (non-default)" OK
fi

echo ""
if [ "$_failures" -gt 0 ]; then
  echo "Result: $_failures required item(s) missing — see docs/local-env-catch-up.md"
  exit 1
fi
if [ "$_warnings" -gt 0 ]; then
  echo "Result: required vars OK; $_warnings warning(s)"
  exit 0
fi
echo "Result: all required checks passed"
exit 0
