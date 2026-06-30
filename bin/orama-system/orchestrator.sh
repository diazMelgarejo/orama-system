#!/bin/bash
# MacOS Orchestrator for Dual-path dispatch (OpenClaw Mac + Hermes Win)
# Runs every 15 minutes via cron, looks for tasks 5 mins after a job.

set -euo pipefail

LOG_FILE="/tmp/orchestrator.log"
FAIL_COUNT_FILE="/tmp/orchestrator_fails"
MAX_RETRIES=10

log() {
    echo "$(date -Iseconds) - $1" | tee -a "$LOG_FILE"
}

alert_user() {
    log "ALERT: Max retries reached. Check $LOG_FILE"
    # Placeholder for actual OpenClaw alert mechanism
}

fails=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || echo "0")

if [ "$fails" -ge "$MAX_RETRIES" ]; then
    alert_user
    exit 1
fi

dispatch_cursor() {
    log "Dispatching cursor-agent..."
    # Simulate cursor-agent dispatch
    sleep 2
    return 0
}

dispatch_openclaw() {
    log "Dispatching OpenClaw+ollama..."
    # Simulate OpenClaw dispatch to Hermes Win
    sleep 3
    return 0
}

# Run in parallel and wait for first to succeed
dispatch_cursor &
PID_CURSOR=$!

dispatch_openclaw &
PID_OPENCLAW=$!

wait -n
FIRST_EXIT=$?

if [ $FIRST_EXIT -eq 0 ]; then
    log "Task successful."
    echo "0" > "$FAIL_COUNT_FILE"
    kill $PID_CURSOR $PID_OPENCLAW 2>/dev/null || true
else
    fails=$((fails + 1))
    echo "$fails" > "$FAIL_COUNT_FILE"
    log "Task failed. Fail count: $fails"
fi

log "Sleeping for 5 minutes before checking next job..."
# In a real daemon, it would sleep 300. But for cron, we just exit and let cron re-trigger or we trigger a one-off.
