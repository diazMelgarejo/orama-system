#!/usr/bin/env bash
# job_cycle_listen.sh — N×15m listen after last job; timer resets if a new job finishes
#
# Longest-wait-wins: each wait runs until (last_job_finished_at + INTERVAL). If
# coord_mark_job_done.sh runs during the wait, the deadline moves forward.
#
# Usage:
#   job_cycle_listen.sh [--rounds 3] [--tag coord-016-018]
set -euo pipefail

ORAMA="${ORAMA_SYSTEM_PATH:-$(git -C "$(dirname "$0")/../../.." rev-parse --show-toplevel 2>/dev/null || pwd)}"
PT="${PERPETUA_TOOLS_PATH:-}"
LOG_DIR="${HOME}/.openclaw/state/lan_peer"
LOG="${LOG_DIR}/job_cycle_listen.log"
LAST_JOB="${LOG_DIR}/last_job_finished_at"
INTERVAL="${COORD_LISTEN_INTERVAL_SEC:-900}"
ROUNDS=3
TAG="listen"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rounds) ROUNDS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    *) shift ;;
  esac
done

mkdir -p "$LOG_DIR"
[[ -f "$LAST_JOB" ]] || date +%s >"$LAST_JOB"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

# Wait until INTERVAL seconds after last job; reset if last_job file changes.
wait_since_last_job() {
  local poll=30
  local anchor
  anchor=$(cat "$LAST_JOB" 2>/dev/null || date +%s)
  log "wait anchor=$anchor interval=${INTERVAL}s (reset if job_done)"
  while true; do
    local now anchor_now deadline
    now=$(date +%s)
    anchor_now=$(cat "$LAST_JOB" 2>/dev/null || echo "$now")
    if [[ "$anchor_now" != "$anchor" ]]; then
      log "wait reset: job finished at $anchor_now (was $anchor)"
      anchor="$anchor_now"
    fi
    deadline=$((anchor + INTERVAL))
    if [[ "$now" -ge "$deadline" ]]; then
      log "wait complete: idle ${INTERVAL}s since job at $anchor"
      return 0
    fi
    sleep "$poll"
  done
}

sync_repos() {
  for R in "$ORAMA" "$PT"; do
    [[ -d "$R/.git" ]] || continue
    cd "$R"
    git fetch origin --prune >>"$LOG" 2>&1 || true
    git pull --rebase origin main >>"$LOG" 2>&1 | tail -1 >>"$LOG" || true
    git push origin main >>"$LOG" 2>&1 | tail -1 >>"$LOG" || true
    log "$(basename "$R") $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  done
}

listen_tick() {
  local round=$1
  python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py" --json 2>>"$LOG" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('round',$round,'probe',d.get('status'))" >>"$LOG" 2>&1 || true
  python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py" list 2>>"$LOG" \
    | python3 -c "import sys,json; w=[x['filename'] for x in json.load(sys.stdin).get('files',[]) if x.get('source')=='win']; print('round',$round,'win_latest',w[-4:])" >>"$LOG" 2>&1 || true
  python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py" pulse-gate --seen-file "$LOG_DIR/last_pulse_seen.json" 2>>"$LOG" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('round',$round,'gate',d.get('status'))" >>"$LOG" 2>&1 || true
}

log ""
log "=== ${ROUNDS}x${INTERVAL}s listen start tag=$TAG ==="

for ROUND in $(seq 1 "$ROUNDS"); do
  log "--- round $ROUND wait ${INTERVAL}s since last job ---"
  wait_since_last_job
  log "--- round $ROUND sync ---"
  sync_repos
  listen_tick "$ROUND"
  log "=== round $ROUND done ==="
done

log "=== ${ROUNDS}x listen complete tag=$TAG ==="
