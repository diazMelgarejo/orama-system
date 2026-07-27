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
PERP_SCRIPT="$(python3 -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())" "$PERP_SCRIPT")"

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

require_safe_dir() {
  local d="$1"
  if [ -L "$d" ]; then
    echo "ERROR: refusing symlinked path: $d" >&2
    exit 1
  fi
  if [ -e "$d" ] && [ ! -d "$d" ]; then
    echo "ERROR: expected directory, got file: $d" >&2
    exit 1
  fi
}

sanitize_session_id
resolve_harness_root

RUNTIME_BASE="${XDG_RUNTIME_DIR:-${HOME}/.cache}"
require_safe_dir "$RUNTIME_BASE"
PID_DIR="${RUNTIME_BASE}/hermes-spawn-${USER:-$(id -un)}"
LOCK_DIR="${PID_DIR}/${SESSION_ID}.lock"
PID_FILE="${PID_DIR}/${SESSION_ID}.pid"

umask 077
mkdir -p "$PID_DIR"
chmod 700 "$PID_DIR" 2>/dev/null || true
require_safe_dir "$PID_DIR"

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
  ps -p "$pid" -o args= 2>/dev/null | sed 's/^[[:space:]]*//' || true
}

verify_hermes_pid() {
  local pid="$1"
  local args=""
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  args="$(pid_command "$pid")"
  [ -n "$args" ] || return 1
  case "$args" in
    *python3*"${PERP_SCRIPT}"*) return 0 ;;
    *python*"${PERP_SCRIPT}"*) return 0 ;;
  esac
  return 1
}

write_pid_file() {
  local pid="$1"
  local tmp="${PID_FILE}.tmp.$$"
  printf '%s\n' "$pid" >"$tmp"
  mv -f "$tmp" "$PID_FILE"
}

release_lock() {
  rm -rf "$LOCK_DIR" 2>/dev/null || true
}

recover_stale_lock() {
  if [ ! -d "$LOCK_DIR" ]; then
    return 0
  fi
  if [ -f "${LOCK_DIR}/pid" ]; then
    local lock_pid=""
    lock_pid="$(cat "${LOCK_DIR}/pid" 2>/dev/null || true)"
    if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
      echo "ERROR: another hermes-spawn session is active for ${SESSION_ID} (lock pid $lock_pid)" >&2
      exit 1
    fi
  fi
  rm -rf "$LOCK_DIR"
}

acquire_lock() {
  recover_stale_lock
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    recover_stale_lock
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "ERROR: could not acquire lock for ${SESSION_ID}" >&2
      exit 1
    fi
  fi
  printf '%s\n' "$$" >"${LOCK_DIR}/pid"
  trap 'release_lock' EXIT
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
      if verify_hermes_pid "$existing_pid"; then
        echo "ERROR: Hermes already running for session ${SESSION_ID} (pid $existing_pid)" >&2
        exit 1
      fi
      rm -f "$PID_FILE"
    fi
    echo "🚀 Spawning Hermes agent for: $TASK"
    (
      cd "$HARNESS_ROOT"
      PYTHONDOTENV_SKIP=1 exec python3 "$PERP_SCRIPT" "$TASK"
    ) &
    child_pid=$!
    if ! kill -0 "$child_pid" 2>/dev/null; then
      echo "ERROR: Hermes failed to start" >&2
      exit 1
    fi
    sleep 1
    if ! verify_hermes_pid "$child_pid"; then
      echo "ERROR: Hermes exited immediately after launch" >&2
      exit 1
    fi
    write_pid_file "$child_pid"
    echo "✅ Hermes started (pid $child_pid, session ${SESSION_ID})"
    ;;
  stop)
    acquire_lock
    if [[ -f "$PID_FILE" ]]; then
      pid="$(cat "$PID_FILE")"
      if verify_hermes_pid "$pid"; then
        kill "$pid"
        for _ in $(seq 1 10); do
          verify_hermes_pid "$pid" || break
          sleep 0.2
        done
        if verify_hermes_pid "$pid"; then
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
      if verify_hermes_pid "$pid"; then
        echo "✅ Hermes running (pid $pid, session ${SESSION_ID})"
        exit 0
      fi
      echo "⚠️ Stale pid file — recorded pid $pid is not the expected hermes_harness.py process" >&2
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
