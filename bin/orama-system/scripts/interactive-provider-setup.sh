#!/bin/bash
# Idempotent LLM-provider onboarding: human-terminal fallback for
# bin/orama-system/references/interactive-provider-setup.md.
# Agent-mediated runs should use AskUserQuestion instead of this script.
set -euo pipefail

ENV_FILE="$HOME/.openclaw/.env.providers"
TIMEOUT=60
NON_INTERACTIVE=0
FORCE_PRIMARY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --non-interactive) NON_INTERACTIVE=1; shift ;;
    --timeout) TIMEOUT="${2:-60}"; shift 2 ;;
    --primary) FORCE_PRIMARY="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

# name|primary_env|alt_env
PROVIDERS='
Claude (Anthropic)|ANTHROPIC_API_KEY|
Codex (OpenAI)|OPENAI_API_KEY|CODEX_API_KEY
Antigravity/Gemini (Google)|GEMINI_API_KEY|GOOGLE_API_KEY
Cline (ClinePass)|CLINE_API_KEY|CLINEPASS_TOKEN
BigModel (GLM-5.2)|GLM52_API_KEY|OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY
Perplexity API|PERPLEXITY_API_KEY|
'

is_configured() {
  # $1=primary_env $2=alt_env — non-empty env var OR non-empty placeholder file counts as configured
  primary="$1"; alt="$2"
  pval="${!primary:-}"
  [ -n "$pval" ] && [ "$pval" != "null" ] && return 0
  if [ -n "$alt" ]; then
    aval="${!alt:-}"
    [ -n "$aval" ] && [ "$aval" != "null" ] && return 0
  fi
  slug=$(printf '%s' "$primary" | tr '[:upper:]_' '[:lower:]-' | sed 's/-api-key$//')
  keyfile="$HOME/.openclaw/secrets/${slug}-api-key"
  [ -s "$keyfile" ] && return 0
  return 1
}

mkdir -p "$HOME/.openclaw/secrets"

configured=""
unconfigured=""
while IFS='|' read -r name primary alt; do
  [ -z "$name" ] && continue
  if is_configured "$primary" "$alt"; then
    configured="$configured$name ($primary)\n"
  else
    unconfigured="$unconfigured$name ($primary)\n"
  fi
done <<EOF
$PROVIDERS
EOF

printf '%s\n' "Configured providers (will be used as fallback):"
[ -n "$configured" ] && printf "$configured" || printf '%s\n' "  (none yet)"

# Idempotent early exit: nothing to ask if everything is configured and no override requested
if [ -z "$unconfigured" ] && [ -z "$FORCE_PRIMARY" ]; then
  printf '%s\n' "All providers already configured — nothing to do."
  exit 0
fi

interactive_possible=0
if [ "$NON_INTERACTIVE" = "0" ] && [ -t 0 ]; then
  interactive_possible=1
fi

primary_choice="$FORCE_PRIMARY"
if [ "$interactive_possible" = "1" ] && [ -z "$primary_choice" ]; then
  printf '\n%s\n' "Unconfigured providers (opt-in, ${TIMEOUT}s to respond, Enter to skip):"
  printf "$unconfigured"
  printf '%s' "Pick a primary provider to configure now (or press Enter to skip): "
  if read -r -t "$TIMEOUT" primary_choice; then
    :
  else
    printf '\n%s\n' "(timed out — skipping)"
    primary_choice=""
  fi
fi

# Write/refresh the placeholder env file — idempotent: never clobber an
# already-non-null value; only fill genuinely-missing entries with null.
: > "$ENV_FILE.tmp"
printf '%s\n' "# Written by interactive-provider-setup.sh — do not hand-edit values here." >> "$ENV_FILE.tmp"
printf '%s\n' "# null = not yet configured (opt-in prompt was skipped or declined)." >> "$ENV_FILE.tmp"
while IFS='|' read -r name primary alt; do
  [ -z "$name" ] && continue
  if is_configured "$primary" "$alt"; then
    existing="${!primary:-null}"
    printf '%s=%s\n' "$primary" "${existing:-\$(kept)}" >> "$ENV_FILE.tmp"
  else
    printf '%s=null\n' "$primary" >> "$ENV_FILE.tmp"
  fi
done <<EOF
$PROVIDERS
EOF
printf 'ORAMA_PRIMARY_PROVIDER=%s\n' "${primary_choice:-null}" >> "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE"

printf '\n%s\n' "Provider config written to $ENV_FILE (mode 600). No credential values were printed."
if [ -n "$primary_choice" ]; then
  printf '%s\n' "Primary provider set to: $primary_choice"
  printf '%s\n' "Run that provider's own setup skill (e.g. glm52-fallback/setup-glm52.sh) to store the actual key."
fi
