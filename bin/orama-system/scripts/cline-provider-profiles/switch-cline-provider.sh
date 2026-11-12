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
#   google-gemini-3.8-flash — Gemini 3.8 Flash (medium reasoning) via
#                             Google's OpenAI-compatible shim (note the
#                             required /openai path segment on the base
#                             URL). 2026-11-03: repointed from the stale
#                             gemini-3.1-pro-preview@high profile. The
#                             2026-08-05 note still stands: this key's
#                             Gemini project had 0 free-tier quota
#                             (verified via a live 429) — real requests
#                             fail until the project has quota/billing
#                             configured.
#   wandb-deepseek-v4-flash — DeepSeek V4.1-Flash-1017 via wanDB.ai (Weave
#                             tracing), per the cline-wandb skill. Model
#                             order 1017 -> V4.1-Flash -> V4-Flash-0731
#                             (2026-11-12: the old bare DeepSeek-V4-Flash id
#                             returns 404 on W&B).
#   bigmodel-glm53-flash    — the REAL BigModel glm-5.3-flash endpoint, per
#                             the glm52-fallback skill. "bigmodel-glm52" is
#                             kept as a legacy alias of this profile.
#
# Reasoning effort (operator rule, 2026-11-12): medium, else high, else low;
# never xhigh or max; always explicit (BigModel defaults to max when it is
# omitted). The checked-in static value is the last live-verified choice
# (high on both profiles today). Optional live checks:
#   --resolve        free GET /models: pick the first served model candidate
#   --verify-effort  tiny BILLED probes: also pick the first accepted effort
#                    (implies --resolve). Opt-in only. A balance, auth or
#                    rate-limit error is reported as inconclusive, never as
#                    "rejected", and providers.json is left unchanged.
#
# Secret values never live in this script or in providers.json in
# tracked form — they resolve from ~/.openclaw/.env.<profile-loader> at
# swap time, which itself reads from ~/.openclaw/secrets/<name> (0600).
#
# Session-backup history (2026-08-05): before overwriting the live
# "openai-compatible" slot, the previous state is snapshotted to
# ~/.cline/data/settings/openai-compatible-history/ (outside this repo —
# a snapshot holds a real resolved secret, never checked in). Idempotent:
# skipped if the outgoing config is functionally identical to the most
# recent snapshot (no manual-override drift to capture). Rotates to a
# maximum of 10 snapshots, oldest evicted first. This exists so a
# manual override that turns out to work has a "last known good" trail
# future sessions can inspect or graduate into a new checked-in
# .json.tmpl profile — not just the 3 profiles this script ships with.
# The whole read-decide-write sequence (including the backup decision)
# runs under an flock'd lock file so two concurrent invocations serialize
# instead of racing, and every write (backup or live config) goes through
# a same-directory temp file + atomic os.replace — never a direct "w"
# open of a file another process might be mid-read on.
#
# Usage:
#   switch-cline-provider.sh <profile-name> [--resolve] [--verify-effort]
#   switch-cline-provider.sh --list
#   switch-cline-provider.sh --list-backups

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVIDERS_JSON="$HOME/.cline/data/settings/providers.json"
BACKUP_HISTORY_DIR="$HOME/.cline/data/settings/openai-compatible-history"
LOCK_FILE="$HOME/.cline/data/settings/.switch-cline-provider.lock"

usage() {
  echo "Usage: $0 <profile-name> [--resolve] [--verify-effort]" >&2
  echo "" >&2
  echo "Available profiles:" >&2
  for f in "$SCRIPT_DIR"/*.json.tmpl; do
    basename "$f" .json.tmpl
  done | sed 's/^/  /' >&2
}

if [ "${1:-}" = "--list-backups" ]; then
  mkdir -p "$BACKUP_HISTORY_DIR"
  ls -1t "$BACKUP_HISTORY_DIR" 2>/dev/null | sed 's/^/  /'
  exit 0
fi

if [ "${1:-}" = "--list" ] || [ -z "${1:-}" ]; then
  usage
  [ "${1:-}" = "--list" ] && exit 0 || exit 1
fi

PROFILE="$1"
shift
EXTRA_FLAGS=("$@")
# Legacy alias: the BigModel profile was renamed once its model name was
# corrected from glm52 to glm-5.3-flash. Old callers keep working.
if [ "$PROFILE" = "bigmodel-glm52" ]; then
  echo "NOTE: profile 'bigmodel-glm52' is now 'bigmodel-glm53-flash' (alias still accepted)" >&2
  PROFILE="bigmodel-glm53-flash"
fi
TMPL="$SCRIPT_DIR/$PROFILE.json.tmpl"

if [ ! -f "$TMPL" ]; then
  echo "ERROR: unknown profile '$PROFILE'" >&2
  usage
  exit 1
fi

# Each profile knows which .env.<loader> file(s) it needs sourced first.
case "$PROFILE" in
  google-gemini-3.8-flash)
    ENV_FILES=("$HOME/.openclaw/.env.cline-google-gemini")
    REQUIRED_VARS=("CLINE_GOOGLE_GEMINI_API_KEY")
    ;;
  wandb-deepseek-v4-flash)
    ENV_FILES=("$HOME/.openclaw/.env.wandb-deepseek")
    # DEEPSEEK_V4_FLASH_WANDB_PROJECT is NOT required here -- verified
    # 2026-08-05 that sending it as an OpenAI-Project header on
    # /v1/chat/completions causes a 401 invalid_api_key on an otherwise
    # valid key (confirmed via /v1/models succeeding with the same key,
    # no project header). Kept in .env.wandb-deepseek for the Python/
    # weave.init() tracing path, which is unrelated to this Cline route.
    REQUIRED_VARS=("DEEPSEEK_V4_FLASH_WANDB")
    ;;
  bigmodel-glm53-flash)
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

# Resolve ${VAR} placeholders and splice into providers.json's
# "openai-compatible" slot — never prints resolved values. Whole critical
# section runs under a fcntl.flock'd lock file (a real POSIX syscall via
# Python's stdlib -- the GNU coreutils `flock` *command* is util-linux-only
# and not present on macOS/BSD by default, confirmed missing on this
# machine, so locking happens in Python, not bash). Every write is
# temp-file-then-atomic-rename; no dict is ever mutated in place. Logic
# lives in switch_cline_provider.py (extracted for pytest coverage --
# see tests/test_switch_cline_provider.py).
mkdir -p "$BACKUP_HISTORY_DIR"

# Some macOS Python builds ship without a CA bundle; point OpenSSL at the system
# one for the optional live checks (TLS verification stays on).
if [ -z "${SSL_CERT_FILE:-}" ] && [ -f /etc/ssl/cert.pem ]; then
  export SSL_CERT_FILE=/etc/ssl/cert.pem
fi

python3 "$SCRIPT_DIR/switch_cline_provider.py" "$PROVIDERS_JSON" "$TMPL" "$PROFILE" "$BACKUP_HISTORY_DIR" "$LOCK_FILE" ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}
