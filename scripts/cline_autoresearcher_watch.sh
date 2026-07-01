#!/bin/bash
# cline_autoresearcher_watch.sh — AutoResearcher 15-min checkback watcher (MacOS)
#
# Called by start.sh with three args:
#   $1 = REPO_ROOT   (orama-system repo root)
#   $2 = US_PYTHON   (Python interpreter path)
#   $3 = LOG_DIR     (.logs directory)
#
# Runs an infinite loop checking every 15 minutes whether the ClinePass
# AutoResearcher fallback should be active. When the OpenClaw Gateway is
# paused, not running, or rate-limited, and ollama is idle, the Cline Bot
# takes over as AutoResearcher.
#
# Resilience: 10x peer unreachable → solo mode (lan_peer_session.py).
# In solo mode, checks back every 15 minutes if the peer is online.

set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
US_PYTHON="${2:-python3}"
LOG_DIR="${3:-$REPO_ROOT/.logs}"

AUTORESEARCHER="$REPO_ROOT/scripts/cline_autoresearcher.py"
SESSION="$REPO_ROOT/bin/orama-system/skills/hermes-harness/scripts/lan_peer_session.py"
AR_LOG="$LOG_DIR/autoresearcher-watch.log"

mkdir -p "$LOG_DIR"

_ar_log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [autoresearcher] $*" | tee -a "$AR_LOG"
}

_ar_log "AutoResearcher watcher started (MacOS) — 15-min checkback cycle"
_ar_log "  REPO_ROOT=$REPO_ROOT"
_ar_log "  US_PYTHON=$US_PYTHON"
_ar_log "  LOG_DIR=$LOG_DIR"

while true; do
  # Check if ClinePass fallback should be active
  if [ -f "$AUTORESEARCHER" ]; then
    _check="$("$US_PYTHON" "$AUTORESEARCHER" --platform macos --check --json 2>/dev/null || echo '{}')"
    _should="$(echo "$_check" | "$US_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('should_fallback',False))" 2>/dev/null || echo "False")"

    if [ "$_should" = "True" ]; then
      _reason="$(echo "$_check" | "$US_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('reason',''))" 2>/dev/null || echo "")"
      _ar_log "fallback active: $_reason"

      # Check peer session — 10x unreachable → solo mode
      if [ -f "$SESSION" ]; then
        if ! "$US_PYTHON" "$SESSION" should-retry >/dev/null 2>&1; then
          _ar_log "solo mode: peer unreachable 10x — 15-min checkback active"
        else
          _ar_log "co-orchestration: peer reachable — retrying"
        fi
      fi
    else
      _reason="$(echo "$_check" | "$US_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('reason',''))" 2>/dev/null || echo "")"
      _ar_log "fallback inactive: $_reason"
    fi
  else
    _ar_log "ERROR: cline_autoresearcher.py not found at $AUTORESEARCHER"
  fi

  sleep 900  # 15 minutes
done