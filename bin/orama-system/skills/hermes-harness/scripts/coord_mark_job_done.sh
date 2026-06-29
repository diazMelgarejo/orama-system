#!/usr/bin/env bash
# coord_mark_job_done.sh — reset idle listen timer (longest-wait-wins semantics)
# Call after each completed coord job (learn + push).
set -euo pipefail
LOG_DIR="${HOME}/.openclaw/state/lan_peer"
mkdir -p "$LOG_DIR"
TS=$(date +%s)
echo "$TS" >"${LOG_DIR}/last_job_finished_at"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) job_done epoch=$TS" >>"${LOG_DIR}/job_cycle_listen.log"
