#!/usr/bin/env bash
# coord_pulse.sh — Mac/Linux 15-minute coord pulse (Tier 0 idle gate + optional agent)
# PLAN: references/coord-pulse-plan.md
set -euo pipefail

ORAMA="${ORAMA_SYSTEM_PATH:-$(git -C "$(dirname "$0")/../../.." rev-parse --show-toplevel 2>/dev/null || pwd)}"
PT="${PERPETUA_TOOLS_PATH:-}"
LOG_DIR="${HOME}/.openclaw/state/lan_peer"
LOCK="${LOG_DIR}/mac_pulse.lock"
SEEN="${LOG_DIR}/last_pulse_seen.json"
LOG="${LOG_DIR}/coord-pulse.log"
DRY_RUN=0

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

mkdir -p "$LOG_DIR"

# Idle gate: skip if lock held by live pid
if [[ -f "$LOCK" ]]; then
  pid=$(head -1 "$LOCK" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    log "skip: pulse lock held by pid $pid"
    exit 0
  fi
fi

log "pulse start dry_run=$DRY_RUN"

python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py" --json >>"$LOG" 2>&1 || true

# Snapshot inbox filenames for diff on next pulse
python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py" list 2>/dev/null \
  | python3 -c "import sys,json; json.dump([x['filename'] for x in json.load(sys.stdin).get('files',[])], open('$SEEN','w'), indent=2)" || true

MAC_QUEUE="$ORAMA/bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py"
python3 "$MAC_QUEUE" enqueue >>"$LOG" 2>&1 || true
QUEUE_IDLE=$(python3 "$MAC_QUEUE" status 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('idle',True))" || echo "True")

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: queue_idle=$QUEUE_IDLE; would invoke cursor-agent if actionable (coord-pulse-plan.md)"
  exit 0
fi

if [[ "$QUEUE_IDLE" != "True" && "$QUEUE_IDLE" != "true" ]]; then
  log "skip: mac_job_queue has pending/active work (pulse defers to manual cycle)"
  exit 0
fi

# Tier 1: one-shot cursor-agent (operator must install cursor-agent)
if command -v cursor-agent >/dev/null 2>&1; then
  echo $$ >"$LOCK"
  trap 'rm -f "$LOCK"' EXIT
  cursor-agent --print --model composer-2.5 \
    "Follow $ORAMA/.cursor/agents/mac-orchestrator-queue.md — execute ONE inbox/backlog job, PT learn+dream, push main." \
    >>"$LOG" 2>&1 || log "cursor-agent exit=$?"
else
  log "skip: cursor-agent not on PATH"
fi

log "pulse end"
