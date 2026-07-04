#!/usr/bin/env bash
# fallback-chain-verify.sh — Verify all model fallback tiers are healthy
#
# Usage: bash fallback-chain-verify.sh [--setup-openrouter]
#        bash fallback-chain-verify.sh [--status-only]
#
# Called by start.sh after all model providers are initialized.
# Ensures OpenRouter (tier 5) is configured and ready as final fallback.

set -uo pipefail

log() { printf '[fallback-verify] %s\n' "$*"; }
warn() { printf '[fallback-verify] ⚠️  %s\n' "$*" >&2; }
err() { printf '[fallback-verify] ❌ %s\n' "$*" >&2; }

# Directories
SECRETS_DIR="$HOME/.openclaw/secrets"
ENV_FILE="$HOME/.openclaw/.env.openrouter"

# Parse flags
SETUP_OPENROUTER=false
STATUS_ONLY=false

while [ $# -gt 0 ]; do
  case "$1" in
    --setup-openrouter) SETUP_OPENROUTER=true; shift ;;
    --status-only) STATUS_ONLY=true; shift ;;
    *) shift ;;
  esac
done

# Color codes
GREEN=$'\033[32m'
RED=$'\033[31m'
YELLOW=$'\033[33m'
RESET=$'\033[0m'

# Tier status mapping
check_tier() {
  local tier=$1
  local name=$2
  local check_cmd=$3

  if eval "$check_cmd" >/dev/null 2>&1; then
    printf "%d. %-38s ${GREEN}[AVAILABLE]${RESET}\n" "$tier" "$name"
    return 0
  else
    printf "%d. %-38s ${RED}[OFFLINE]${RESET}\n" "$tier" "$name"
    return 1
  fi
}

check_tier_configured() {
  local tier=$1
  local name=$2
  local file=$3

  if [ -f "$file" ]; then
    printf "%d. %-38s ${GREEN}[CONFIGURED]${RESET}\n" "$tier" "$name"
    return 0
  else
    printf "%d. %-38s ${YELLOW}[NOT CONFIGURED]${RESET}\n" "$tier" "$name"
    return 1
  fi
}

log "Model Fallback Chain Verification"
log ""

# Tier 1: ClinePass (local Claude)
check_tier 1 "ClinePass (local Claude)" "command -v cline >/dev/null 2>&1"
TIER1=$?

# Tier 2: LM Studio (Win GPU)
WIN_IP="${LM_STUDIO_WIN_ENDPOINTS:-192.168.254.104:1234}"
check_tier 2 "LM Studio (Windows GPU)" "curl -s --max-time 2 http://$WIN_IP/v1/models >/dev/null 2>&1"
TIER2=$?

# Tier 3: Ollama (Mac local)
check_tier 3 "Ollama (Mac local)" "curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1"
TIER3=$?

# Tier 4: GLM-5.2 (BigModel fallback)
check_tier_configured 4 "GLM-5.2 (BigModel fallback)" "$SECRETS_DIR/glm52-api-key"
TIER4=$?

# Tier 5: OpenRouter (cloud fallback)
check_tier_configured 5 "OpenRouter (cloud fallback)" "$SECRETS_DIR/openrouter-api-key"
TIER5=$?

log ""

# If status-only, exit now
if [ "$STATUS_ONLY" = true ]; then
  exit 0
fi

# Check if any tier is available
AVAILABLE_COUNT=0
[ $TIER1 -eq 0 ] && ((AVAILABLE_COUNT++))
[ $TIER2 -eq 0 ] && ((AVAILABLE_COUNT++))
[ $TIER3 -eq 0 ] && ((AVAILABLE_COUNT++))
[ $TIER4 -eq 0 ] && ((AVAILABLE_COUNT++))
[ $TIER5 -eq 0 ] && ((AVAILABLE_COUNT++))

if [ $AVAILABLE_COUNT -eq 0 ]; then
  warn "No model tiers are currently available!"
  warn "At least one tier should be online. Check:"
  warn "  • Tier 1 (ClinePass): cline --version"
  warn "  • Tier 2 (LM Studio): curl http://$WIN_IP/v1/models"
  warn "  • Tier 3 (Ollama): ollama list"
  warn "  • Tier 4 (GLM-5.2): ls -l ~/.openclaw/secrets/glm52-api-key"
  warn "  • Tier 5 (OpenRouter): setup-openrouter.sh"
fi

# Prompt for OpenRouter setup if not configured and flag is set
if [ $TIER5 -ne 0 ] && [ "$SETUP_OPENROUTER" = true ]; then
  log "Tier 5 (OpenRouter) not configured. Setting up now..."

  # Locate setup script
  SETUP_SCRIPT=$(find ~/code -name "setup-openrouter.sh" 2>/dev/null | head -1)

  if [ -n "$SETUP_SCRIPT" ]; then
    bash "$SETUP_SCRIPT"
    if [ -f "$SECRETS_DIR/openrouter-api-key" ]; then
      log "✅ OpenRouter setup complete!"
    fi
  else
    warn "setup-openrouter.sh not found. Install it from bin/orama-system/skills/openrouter-fallback/"
  fi
fi

log ""
log "Fallback chain: If tier N becomes unavailable, tier N+1 will automatically take over."
log "Ensure ALL tiers are AVAILABLE or CONFIGURED for maximum resilience."
log ""

# Final gate: at least tier 3 or 5 should be available
if [ $TIER3 -eq 0 ] || [ $TIER5 -eq 0 ]; then
  log "✅ Fallback chain healthy: $([ $TIER3 -eq 0 ] && echo "Ollama OR ")OpenRouter available"
  exit 0
else
  warn "⚠️  Fallback chain degraded: Ollama offline AND OpenRouter not configured"
  warn "    Run: bash setup-openrouter.sh (in bin/orama-system/skills/openrouter-fallback/)"
  exit 1
fi
