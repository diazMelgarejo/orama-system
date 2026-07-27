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
PERP_SCRIPT="${REPO_ROOT}/perpetua-tools/src/hermes_harness.py"

sanitize_session_id() {
  local raw="${HERMES_SPAWN_SESSION:-default}"
  case "$raw" in
    *[!a-zA-Z0-9_-]*|*..*|""|"."|"..")
      echo "ERROR: HERMES_SPAWN_SESSION must match [a-zA-Z0-9_-]+ (got: $raw)" >&2
      exit 1
      ;;
  esac
  SESSION_ID="$raw"
}

resolve_harness_root() {
  local hfile=""
  if hfile="$(python3 -c "import hermes; print(hermes.__file__)" 2>/dev/null)"; then
    HARNESS_ROOT="${hfile%/hermes/__init__.py}"
  elif [ -n "${HERMES_HOME:-}" ] && [ -d "${HERMES_HOME}" ]; then
    HARNESS_ROOT="${HERMES_HOME}"
  else
    HARNESS_ROOT="${HOME}/.hermes"
  fi
}

sanitize_session_id
resolve_harness_root

PID_DIR="${XDG_RUNTIME_DIR:-${HOME}/.cache}/hermes-spawn"
umask 077
mkdir -p "$PID_DIR"
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
    printf '%s\n' "$child_pid" >"$PID_FILE"
    echo "✅ Hermes started (pid $child_pid, session ${SESSION_ID})"
    ;;
  stop)
    acquire_lock
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
      if [[ "$(cat "$PID_FILE" 2>/dev/null || true)" == "$pid" ]]; then
        rm -f "$PID_FILE"
      fi
    else
      echo "ℹ️ No Hermes pid file at $PID_FILE"
    fi
    ;;
  status)
    validate_paths
    if [[ -f "$PID_FILE" ]]; then
      pid="$(cat "$PID_FILE")"
      if kill -0 "$pid" 2>/dev/null && pid_command "$pid" | grep -q 'hermes_harness.py'; then
        echo "✅ Hermes running (pid $pid, session ${SESSION_ID})"
        exit 0
      fi
      echo "⚠️ Stale pid file — recorded pid $pid is not a running hermes_harness.py" >&2
      exit 1
    fi
    echo "ℹ️ No active Hermes session ${SESSION_ID} (no pid file)"
    exit 1
    ;;
  *)
    echo "Unknown action: $ACTION (expected start|stop|status)" >&2
    exit 1
    ;;
esac
```
