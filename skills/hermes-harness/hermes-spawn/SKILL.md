---
name: hermes-spawn
description: >
  Start, stop, or check a Hermes AIAgent session programmatically.
  Use when you need to spawn a Hermes agent for a task, check its status,
  or stop a running session. Requires credentials in the process environment;
  missing variables fail clearly (no automatic .env loading).
argument-hint: "<start|stop|status> [task description]"
disable-model-invocation: true
---
```bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_ROOT="$(python3 -c "import hermes; print(hermes.__file__)" 2>/dev/null | sed 's|/hermes/__init__.py||' || echo "${HERMES_HOME:-$HOME/.hermes}")"
PERP_SCRIPT="${REPO_ROOT}/perpetua-tools/src/hermes_harness.py"
SESSION_ID="${HERMES_SPAWN_SESSION:-default}"
PID_DIR="${TMPDIR:-/tmp}/hermes-spawn"
PID_FILE="${PID_DIR}/${SESSION_ID}.pid"
LOCK_FILE="${PID_DIR}/${SESSION_ID}.lock"

ACTION="${1:-status}"
shift || true
TASK="$*"

validate_paths() {
  if [ ! -d "$HARNESS_ROOT" ]; then
    echo "ERROR: Hermes harness root not found: $HARNESS_ROOT" >&2
    exit 1
  fi
  if [ ! -f "$PERP_SCRIPT" ]; then
    echo "ERROR: Hermes harness script not found: $PERP_SCRIPT" >&2
    exit 1
  fi
}

pid_command() {
  local pid="$1"
  ps -p "$pid" -o args= 2>/dev/null || true
}

acquire_lock() {
  mkdir -p "$PID_DIR"
  if ! mkdir "$LOCK_FILE" 2>/dev/null; then
    echo "ERROR: another hermes-spawn session is active for ${SESSION_ID}" >&2
    exit 1
  fi
  trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
}

case "$ACTION" in
  start)
    if [[ -z "$TASK" ]]; then
      echo "Usage: start <task description>" >&2
      exit 1
    fi
    validate_paths
    acquire_lock
    if [[ -f "$PID_FILE" ]]; then
      existing_pid="$(cat "$PID_FILE")"
      if kill -0 "$existing_pid" 2>/dev/null && pid_command "$existing_pid" | grep -q 'hermes_harness.py'; then
        echo "ERROR: Hermes already running for session ${SESSION_ID} (pid $existing_pid)" >&2
        exit 1
      fi
      rm -f "$PID_FILE"
    fi
    echo "🚀 Spawning Hermes agent for: $TASK"
    (
      cd "$HARNESS_ROOT"
      PYTHONDOTENV_SKIP=1 python3 "$PERP_SCRIPT" "$TASK"
    ) &
    child_pid=$!
    if ! kill -0 "$child_pid" 2>/dev/null; then
      echo "ERROR: Hermes failed to start" >&2
      exit 1
    fi
    sleep 1
    if ! kill -0 "$child_pid" 2>/dev/null; then
      echo "ERROR: Hermes exited immediately after launch" >&2
      exit 1
    fi
    echo "$child_pid" >"$PID_FILE"
    echo "✅ Hermes started (pid $child_pid, session ${SESSION_ID})"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]]; then
      pid="$(cat "$PID_FILE")"
      if kill -0 "$pid" 2>/dev/null && pid_command "$pid" | grep -q 'hermes_harness.py'; then
        kill "$pid"
        for _ in $(seq 1 10); do
          kill -0 "$pid" 2>/dev/null || break
          sleep 0.2
        done
        if kill -0 "$pid" 2>/dev/null; then
          echo "ERROR: Hermes pid $pid did not stop cleanly" >&2
          exit 1
        fi
        echo "✅ Hermes stopped (pid $pid)"
      else
        echo "ℹ️ No active Hermes process for pid $pid"
      fi
      rm -f "$PID_FILE"
    else
      echo "ℹ️ No Hermes pid file at $PID_FILE"
    fi
    ;;
  status)
    validate_paths
    (cd "$HARNESS_ROOT" && PYTHONDOTENV_SKIP=1 python3 -c "from run_agent import AIAgent; a = AIAgent(quiet_mode=True, skip_memory=True); print(a.chat('Reply with: HERMES_OK'))")
    ;;
  *)
    echo "Unknown action: $ACTION (expected start|stop|status)" >&2
    exit 1
    ;;
esac
```
