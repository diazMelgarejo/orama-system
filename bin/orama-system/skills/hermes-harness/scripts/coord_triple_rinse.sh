#!/usr/bin/env bash
# coord_triple_rinse.sh — outer rinse loop: drain queue → learn/push → 3×15m listen
#
# Default: 3 outer rinses; each rinse runs up to COORD_MAX_JOBS_PER_RINSE coord_pulse
# jobs (when gate actionable), then learn+dream+push, then job_cycle_listen --rounds 3.
#
# Usage:
#   coord_triple_rinse.sh [--outer 3] [--max-jobs 8] [--tag coord-rinse]
set -euo pipefail

ORAMA="${ORAMA_SYSTEM_PATH:-$(git -C "$(dirname "$0")/../../.." rev-parse --show-toplevel 2>/dev/null || pwd)}"
PT="${PERPETUA_TOOLS_PATH:-}"
LOG_DIR="${HOME}/.openclaw/state/lan_peer"
LOG="${LOG_DIR}/coord_triple_rinse.log"
OUTER=3
MAX_JOBS=8
TAG="coord-rinse"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --outer) OUTER="$2"; shift 2 ;;
    --max-jobs) MAX_JOBS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    *) shift ;;
  esac
done

mkdir -p "$LOG_DIR"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

post_job_learn_push() {
  if [[ -n "$PT" && -f "$PT/.agent/tools/learn.py" ]]; then
    python3 "$PT/.agent/tools/learn.py" "coord triple rinse tick: pulse job done, pushed sync" \
      --rationale "${TAG}" >>"$LOG" 2>&1 || true
    python3 "$PT/.agent/memory/auto_dream.py" >>"$LOG" 2>&1 || true
  fi
  for R in "$ORAMA" "$PT"; do
    [[ -d "${R:-}/.git" ]] || continue
    git -C "$R" pull --rebase origin main >>"$LOG" 2>&1 || true
    git -C "$R" push origin main >>"$LOG" 2>&1 || true
  done
  "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_mark_job_done.sh" >>"$LOG" 2>&1 || true
}

log "=== triple rinse start outer=$OUTER max_jobs=$MAX_JOBS tag=$TAG ==="

for O in $(seq 1 "$OUTER"); do
  log "--- outer rinse $O/$OUTER ---"
  JOBS=0
  while [[ "$JOBS" -lt "$MAX_JOBS" ]]; do
    GATE_JSON=$(python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py" \
      pulse-gate --seen-file "$LOG_DIR/last_pulse_seen.json" 2>>"$LOG" || echo '{"status":"error"}')
    STATUS=$(echo "$GATE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo error)
    if [[ "$STATUS" != "actionable" ]]; then
      log "outer $O: gate=$STATUS after $JOBS jobs (stop drain)"
      break
    fi
    PICK=$(echo "$GATE_JSON" | python3 -c "import sys,json; print((json.load(sys.stdin).get('pick') or {}).get('id',''))" 2>/dev/null || true)
    log "outer $O job $((JOBS + 1)): pulse pick=$PICK"
    if ! "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh" >>"$LOG" 2>&1; then
      log "outer $O: coord_pulse failed — stop drain"
      break
    fi
    post_job_learn_push
    JOBS=$((JOBS + 1))
  done
  log "outer $O: starting 3x15m listen"
  "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/job_cycle_listen.sh" \
    --rounds 3 --tag "${TAG}-o${O}" >>"$LOG" 2>&1
  log "--- outer rinse $O/$OUTER complete ---"
done

log "=== triple rinse complete tag=$TAG ==="
