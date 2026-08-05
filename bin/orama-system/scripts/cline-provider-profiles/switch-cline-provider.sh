#!/bin/bash
# switch-cline-provider.sh — hot-swap Cline's openai-compatible provider slot
#
# Cline (v3.0.49 as of this writing) stores exactly ONE active
# "openai-compatible" provider at a time in
# ~/.cline/data/settings/providers.json. This script lets that single
# slot be swapped between named, checked-in profile templates without
# ever storing a literal secret in a tracked file.
#
# Profiles (this directory):
#   google-gemini-3.1-pro   — real Gemini 3.1 Pro via Google's OpenAI-
#                             compatible shim (note the required /openai
#                             path segment on the base URL). Corrected
#                             2026-08-05: the config this replaced had
#                             model="bigmodel/glm-5.2" pointed at this
#                             same Google endpoint — a mislabeled
#                             leftover, not a real BigModel route. This
#                             key's Gemini project currently has 0 free-
#                             tier quota (verified via a live 429) — the
#                             endpoint/model are now correct, but real
#                             requests will still fail until the project
#                             has quota/billing configured.
#   wandb-deepseek-v4-flash — DeepSeek-V4-Flash via wanDB.ai (Weave
#                             tracing), per the cline-wandb skill.
#   bigmodel-glm52          — the REAL BigModel GLM-5.2 endpoint, per
#                             the glm52-fallback skill.
#
# Secret values never live in this script or in providers.json in
# tracked form — they resolve from ~/.openclaw/.env.<profile-loader> at
# swap time, which itself reads from ~/.openclaw/secrets/<name> (0600).
#
# Usage:
#   switch-cline-provider.sh <profile-name>
#   switch-cline-provider.sh --list

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVIDERS_JSON="$HOME/.cline/data/settings/providers.json"
BACKUP_DIR="$HOME/.claude-config-backups"

usage() {
  echo "Usage: $0 <profile-name>" >&2
  echo "" >&2
  echo "Available profiles:" >&2
  for f in "$SCRIPT_DIR"/*.json.tmpl; do
    basename "$f" .json.tmpl
  done | sed 's/^/  /' >&2
}

if [ "${1:-}" = "--list" ] || [ -z "${1:-}" ]; then
  usage
  [ "${1:-}" = "--list" ] && exit 0 || exit 1
fi

PROFILE="$1"
TMPL="$SCRIPT_DIR/$PROFILE.json.tmpl"

if [ ! -f "$TMPL" ]; then
  echo "ERROR: unknown profile '$PROFILE'" >&2
  usage
  exit 1
fi

# Each profile knows which .env.<loader> file(s) it needs sourced first.
case "$PROFILE" in
  google-gemini-3.1-pro)
    ENV_FILES=("$HOME/.openclaw/.env.cline-google-gemini")
    REQUIRED_VARS=("CLINE_GOOGLE_GEMINI_API_KEY")
    ;;
  wandb-deepseek-v4-flash)
    ENV_FILES=("$HOME/.openclaw/.env.wandb-deepseek")
    REQUIRED_VARS=("DEEPSEEK_V4_FLASH_WANDB" "DEEPSEEK_V4_FLASH_WANDB_PROJECT")
    ;;
  bigmodel-glm52)
    ENV_FILES=("$HOME/.openclaw/.env.glm52")
    REQUIRED_VARS=("GLM52_API_KEY")
    ;;
  *)
    echo "ERROR: profile '$PROFILE' has no env-loader mapping in this script" >&2
    exit 1
    ;;
esac

for ef in "${ENV_FILES[@]}"; do
  # shellcheck source=/dev/null
  [ -f "$ef" ] && source "$ef" 2>/dev/null || true
done

MISSING=()
for v in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!v:-}" ]; then
    MISSING+=("$v")
  fi
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "ERROR: profile '$PROFILE' requires the following unset variable(s):" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  echo "See ${ENV_FILES[*]} for setup instructions." >&2
  exit 1
fi

TS=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"
cp "$PROVIDERS_JSON" "$BACKUP_DIR/cline-providers.json.pre-switch-to-${PROFILE}-${TS}"

# Resolve ${VAR} placeholders and splice into providers.json's
# "openai-compatible" slot via python — never prints resolved values.
python3 - "$PROVIDERS_JSON" "$TMPL" "$PROFILE" <<'PYEOF'
import json, os, re, sys
from datetime import datetime, timezone

providers_path, tmpl_path, profile = sys.argv[1], sys.argv[2], sys.argv[3]

with open(tmpl_path) as f:
    raw = f.read()

def resolve(m):
    name = m.group(1)
    val = os.environ.get(name)
    if val is None:
        raise SystemExit(f"ERROR: template references unset env var {name}")
    return val

resolved = re.sub(r"\$\{([A-Z0-9_]+)\}", resolve, raw)
new_block = json.loads(resolved)

with open(providers_path) as f:
    cfg = json.load(f)

new_block["updatedAt"] = datetime.now(timezone.utc).isoformat()
new_block["tokenSource"] = f"switch-cline-provider.sh:{profile}"

cfg["providers"]["openai-compatible"] = new_block
cfg["lastUsedProvider"] = "openai-compatible"

with open(providers_path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

print(f"Activated profile: {profile}")
PYEOF
