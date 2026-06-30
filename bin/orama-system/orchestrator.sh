#!/bin/bash
# MacOS Orchestrator for Dual-path dispatch (OpenClaw Mac + Hermes Win)
# Runs every 15 minutes via cron, looks for tasks 5 mins after a job.
#
# bash-3.2 safe (macOS default): no `wait -n` (GNU bash 4+ only).
# First-success-wins via PID polling with `kill -0` + `wait $pid`.
# Win peer down -> skip silently (Windows Coder Policy), do not fail the run
# unless ALL dispatch paths fail.

set -euo pipefail

LOG_FILE="/tmp/orchestrator.log"
FAIL_COUNT_FILE="/tmp/orchestrator_fails"
MAX_RETRIES=10
WIN_PEER="${WIN_PEER_ENDPOINT:-192.168.254.100:8002}"
WIN_PROBE_TIMEOUT=5

log() {
    echo "$(date -Iseconds) - $1" | tee -a "$LOG_FILE"
}

alert_user() {
    log "ALERT: Max retries ($MAX_RETRIES) reached. Orchestrator paused."
    log "  Logs: $LOG_FILE  Fail counter: $FAIL_COUNT_FILE"
    log "  Resume: rm -f \"$FAIL_COUNT_FILE\" (next cron tick restarts dispatch)."
    if [ -x "${OPENCLAW_ALERT_SCRIPT:-}" ]; then
        "$OPENCLAW_ALERT_SCRIPT" "orchestrator max retries reached" 2>/dev/null || true
    fi
}

# Probe the Windows peer; return 0 if PASS, 1 if down (never trips set -e).
probe_win_peer() {
    local code
    code="$(curl -s --max-time "$WIN_PROBE_TIMEOUT" -o /dev/null -w '%{http_code}' \
        "http://${WIN_PEER}/" 2>/dev/null || echo "000")"
    [ "$code" != "000" ]
}

dispatch_cursor() {
    log "Dispatching cursor-agent..."
    # TODO: real cursor-agent CLI dispatch (placeholder: simulate work)
    sleep 2
    return 0
}

dispatch_openclaw() {
    # OpenClaw+ollama -> Hermes Win path. Skip gracefully if Win peer is down
    # (Windows Coder Policy: offline -> skip silently, log WARN, do not fail).
    if ! probe_win_peer; then
        log "WARN: Win peer ${WIN_PEER} not reachable — skipping Win dispatch."
        return 1
    fi
    log "Dispatching OpenClaw+ollama (Win peer PASS)..."
    # TODO: real OpenClaw dispatch to Hermes Win (placeholder: simulate work)
    sleep 3
    return 0
}

fails=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || echo "0")

if [ "$fails" -ge "$MAX_RETRIES" ]; then
    alert_user
    exit 1
fi

# Launch both dispatch paths in parallel.
dispatch_cursor &
PID_CURSOR=$!
dispatch_openclaw &
PID_OPENCLAW=$!

# bash-3.2-safe "wait -n": poll until one child exits.
while kill -0 "$PID_CURSOR" 2>/dev/null && kill -0 "$PID_OPENCLAW" 2>/dev/null; do
    sleep 0.2
done

# Identify which exited first; reap it, and if it succeeded, kill+reap the other.
SUCCESS=0
if ! kill -0 "$PID_CURSOR" 2>/dev/null; then
    wait "$PID_CURSOR" && SUCCESS=1 || true
    [ "$SUCCESS" -eq 1 ] && { kill "$PID_OPENCLAW" 2>/dev/null || true; wait "$PID_OPENCLAW" 2>/dev/null || true; }
else
    wait "$PID_OPENCLAW" && SUCCESS=1 || true
    [ "$SUCCESS" -eq 1 ] && { kill "$PID_CURSOR" 2>/dev/null || true; wait "$PID_CURSOR" 2>/dev/null || true; }
fi

# First path failed -> wait for the other (it may still succeed).
if [ "$SUCCESS" -eq 0 ]; then
    if kill -0 "$PID_CURSOR" 2>/dev/null; then
        wait "$PID_CURSOR" && SUCCESS=1 || true
    elif kill -0 "$PID_OPENCLAW" 2>/dev/null; then
        wait "$PID_OPENCLAW" && SUCCESS=1 || true
    fi
fi

if [ "$SUCCESS" -eq 1 ]; then
    log "Task successful (a dispatch path won)."
    echo "0" > "$FAIL_COUNT_FILE"
else
    fails=$((fails + 1))
    echo "$fails" > "$FAIL_COUNT_FILE"
    log "Task failed (all paths failed/skipped). Fail count: $fails"
fi

log "Sleeping for 5 minutes before checking next job... (cron re-triggers every 15m)"
