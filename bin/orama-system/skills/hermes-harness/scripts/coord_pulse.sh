#!/usr/bin/env bash
# coord_pulse.sh — Mac/Linux 15-minute coord pulse (Tier 0 idle gate + optional agent)
# PLAN: references/coord-pulse-plan.md
set -euo pipefail

ORAMA="${ORAMA_SYSTEM_PATH:-$(git -C "$(dirname "$0")/../../.." rev-parse --show-toplevel 2>/dev/null || pwd)}"
PT="${PERPETUA_TOOLS_PATH:-}"
LOG_DIR="${HOME}/.openclaw/state/lan_peer"
LOCK="${LOG_DIR}/mac_pulse.lock"
LOCK_DIR="${LOG_DIR}/mac_pulse.lockdir"
SEEN="${LOG_DIR}/last_pulse_seen.json"
LOG="${LOG_DIR}/coord-pulse.log"
MAC_QUEUE="$ORAMA/bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py"
DRY_RUN=0

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

mkdir -p "$LOG_DIR"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

_release_lock() {
  rm -rf "$LOCK_DIR"
}

_acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    rm -f "$LOCK"
    trap _release_lock EXIT INT TERM
    return 0
  fi

  local owner=""
  if [[ -f "$LOCK_DIR/pid" ]]; then
    owner="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  fi
  if [[ -n "$owner" ]] && kill -0 "$owner" 2>/dev/null; then
    log "skip: pulse lock held by pid=$owner ($LOCK_DIR)"
    exit 2
  fi

  log "stale pulse lock cleared ($LOCK_DIR)"
  rm -rf "$LOCK_DIR"
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    rm -f "$LOCK"
    trap _release_lock EXIT INT TERM
    return 0
  fi

  log "skip: pulse lock acquired by another process ($LOCK_DIR)"
  exit 2
}

_snapshot_seen() {
  python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py" list 2>/dev/null \
    | python3 -c "import sys,json; json.dump([x['filename'] for x in json.load(sys.stdin).get('files',[])], open('$SEEN','w'), indent=2)" || true
}

# Idle gate: atomic directory lock held for the full pulse, including cursor-agent.
if [[ -f "$LOCK" && ! -d "$LOCK_DIR" ]]; then
  log "clearing legacy pulse lock file ($LOCK)"
  rm -f "$LOCK"
fi
_acquire_lock

log "pulse start dry_run=$DRY_RUN"

# Tier 0 — fetch both repos (no pull; agent/post-job handles rebase)
if [[ -d "$ORAMA/.git" ]]; then
  git -C "$ORAMA" fetch origin --prune >>"$LOG" 2>&1 || true
fi
if [[ -n "$PT" && -d "$PT/.git" ]]; then
  git -C "$PT" fetch origin --prune >>"$LOG" 2>&1 || true
fi

python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py" --json \
  --timeout "${LAN_PEER_PROBE_TIMEOUT:-2}" \
  --status-timeout "${LAN_PEER_STATUS_TIMEOUT:-3}" \
  --ws-timeout "${LAN_PEER_WS_TIMEOUT:-2}" >>"$LOG" 2>&1 || true
python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py" \
  flush-outbox --peer --timeout "${LAN_PEER_HTTP_TIMEOUT:-2}" >>"$LOG" 2>&1 || true

GATE_JSON=$(python3 "$MAC_QUEUE" pulse-gate --seen-file "$SEEN" 2>>"$LOG" || echo '{"status":"error"}')
GATE_STATUS=$(echo "$GATE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")
PICK_ROLE=$(echo "$GATE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('pick') or {}; print(p.get('role',''))" 2>/dev/null || true)
PICK_ID=$(echo "$GATE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('pick') or {}; print(p.get('id',''))" 2>/dev/null || true)
NEW_N=$(echo "$GATE_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('new_files',[])))" 2>/dev/null || echo "0")

log "gate status=$GATE_STATUS new_files=$NEW_N pick=${PICK_ROLE:+$PICK_ROLE:}$PICK_ID"

_snapshot_seen

if [[ "$GATE_STATUS" != "actionable" ]]; then
  log "idle: gate=$GATE_STATUS (frugal exit)"
  log "pulse end"
  exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: would invoke cursor-agent role=$PICK_ROLE job=$PICK_ID"
  log "pulse end"
  exit 0
fi

if ! command -v cursor-agent >/dev/null 2>&1; then
  log "skip: cursor-agent not on PATH"
  log "pulse end"
  exit 0
fi

AGENT_CARD="$ORAMA/.cursor/agents/mac-orchestrator-queue.md"
if [[ "$PICK_ROLE" == "researcher" ]]; then
  AGENT_CARD="$ORAMA/.cursor/agents/win-autoresearcher-queue.md"
fi
PROMPT="Follow $AGENT_CARD — execute ONE $PICK_ROLE job ($PICK_ID) from mac_job_queue / inbox. PT learn+dream, push main."

log "cursor-agent start role=$PICK_ROLE job=$PICK_ID"
cursor-agent --print --model composer-2.5 "$PROMPT" >>"$LOG" 2>&1 || log "cursor-agent exit=$?"

log "pulse end"
