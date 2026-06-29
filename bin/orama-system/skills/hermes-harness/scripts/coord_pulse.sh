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
MAC_QUEUE="$ORAMA/bin/orama-system/skills/hermes-harness/scripts/mac_job_queue.py"
DRY_RUN=0

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

mkdir -p "$LOG_DIR"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

_snapshot_seen() {
  python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py" list 2>/dev/null \
    | python3 -c "import sys,json; json.dump([x['filename'] for x in json.load(sys.stdin).get('files',[])], open('$SEEN','w'), indent=2)" || true
}

# Idle gate: flock held by live pulse (includes cursor-agent run)
if [[ -f "$LOCK" ]]; then
  if flock -n "$LOCK" -c "true" 2>/dev/null; then
    rm -f "$LOCK"
  else
    log "skip: pulse lock held ($LOCK)"
    exit 2
  fi
fi

log "pulse start dry_run=$DRY_RUN"

# Tier 0 — fetch both repos (no pull; agent/post-job handles rebase)
if [[ -d "$ORAMA/.git" ]]; then
  git -C "$ORAMA" fetch origin --prune >>"$LOG" 2>&1 || true
fi
if [[ -n "$PT" && -d "$PT/.git" ]]; then
  git -C "$PT" fetch origin --prune >>"$LOG" 2>&1 || true
fi

python3 "$ORAMA/bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py" --json >>"$LOG" 2>&1 || true

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
(
  flock -x 9
  cursor-agent --print --model composer-2.5 "$PROMPT" >>"$LOG" 2>&1 || log "cursor-agent exit=$?"
) 9>"$LOCK"

log "pulse end"
