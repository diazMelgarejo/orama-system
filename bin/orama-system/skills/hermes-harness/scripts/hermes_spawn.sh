#!/usr/bin/env bash
# Hermes spawn lifecycle — extracted from hermes-spawn/SKILL.md for testability.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve_perp_harness.sh
source "${SCRIPT_DIR}/resolve_perp_harness.sh"

PERP_SCRIPT="$(resolve_perp_harness_script)"

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
  if [[ -n "${HERMES_HOME:-}" && -d "${HERMES_HOME}" ]]; then
    HARNESS_ROOT="${HERMES_HOME}"
    return 0
  fi
  if hfile="$(PYTHONDOTENV_SKIP=1 python3 -I -c "import hermes; print(hermes.__file__)" 2>/dev/null)"; then
    HARNESS_ROOT="${hfile%/hermes/__init__.py}"
    HARNESS_ROOT="${HARNESS_ROOT%/hermes.py}"
    return 0
  fi
  HARNESS_ROOT="${HOME}/.hermes"
}

require_safe_dir() {
  local d="$1"
  if [[ -L "$d" ]]; then
    echo "ERROR: refusing symlinked path: $d" >&2
    exit 1
  fi
  if [[ -e "$d" && ! -d "$d" ]]; then
    echo "ERROR: expected directory, got file: $d" >&2
    exit 1
  fi
}

pid_command() {
  local pid="$1"
  ps -p "$pid" -o args= 2>/dev/null | sed 's/^[[:space:]]*//' || true
}

verify_hermes_pid() {
  local pid="$1"
  local expected_started="${2:-}"
  local args="" actual_started=""
  [[ -n "$pid" ]] || return 1
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  args="$(pid_command "$pid")"
  [[ -n "$args" ]] || return 1
  case "$args" in
    *python3*"${PERP_SCRIPT}"*) ;;
    *python*"${PERP_SCRIPT}"*) ;;
    *) return 1 ;;
  esac
  if [[ -n "$expected_started" ]]; then
    actual_started="$(ps -p "$pid" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//')"
    [[ "$actual_started" = "$expected_started" ]] || return 1
  fi
  return 0
}

read_pid_file() {
  local line=""
  SPAWN_PID=""
  SPAWN_STARTED=""
  [[ -f "$PID_FILE" ]] || return 1
  line="$(tr -d '\r' <"$PID_FILE" | head -1)"
  SPAWN_PID="${line%% *}"
  SPAWN_STARTED="${line#"$SPAWN_PID"}"
  SPAWN_STARTED="${SPAWN_STARTED# }"
  [[ "$SPAWN_PID" =~ ^[0-9]+$ ]] || return 1
  return 0
}

write_pid_file() {
  local pid="$1"
  local started="" tmp="${PID_FILE}.tmp.$$"
  started="$(ps -p "$pid" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//')"
  printf '%s %s\n' "$pid" "$started" >"$tmp"
  mv -f "$tmp" "$PID_FILE"
}

release_lock() {
  rm -rf "$LOCK_DIR" 2>/dev/null || true
}

recover_stale_lock() {
  local lock_pid=""
  if [[ ! -d "$LOCK_DIR" ]]; then
    return 0
  fi
  if [[ ! -f "${LOCK_DIR}/pid" ]]; then
    echo "ERROR: lock exists without owner metadata — busy" >&2
    exit 1
  fi
  lock_pid="$(tr -d '\r' <"${LOCK_DIR}/pid" | head -1)"
  if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
    echo "ERROR: another hermes-spawn session is active for ${SESSION_ID} (lock pid $lock_pid)" >&2
    exit 1
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
  local tmp="${LOCK_DIR}/pid.tmp.$$"
  printf '%s\n' "$$" >"$tmp"
  mv -f "$tmp" "${LOCK_DIR}/pid"
  trap 'release_lock' EXIT
}

cleanup_spawn() {
  if [[ -n "${child_pid:-}" ]] && verify_hermes_pid "$child_pid"; then
    kill "$child_pid" 2>/dev/null || true
    wait "$child_pid" 2>/dev/null || true
  fi
  release_lock
}

validate_paths() {
  if [[ ! -d "$HARNESS_ROOT" ]]; then
    echo "ERROR: Hermes harness root not found: $HARNESS_ROOT" >&2
    exit 1
  fi
  if [[ ! -f "$PERP_SCRIPT" ]]; then
    echo "ERROR: Hermes harness script not found: $PERP_SCRIPT" >&2
    exit 1
  fi
}

main() {
  sanitize_session_id
  resolve_harness_root

  RUNTIME_BASE="${XDG_RUNTIME_DIR:-${HOME}/.cache}"
  require_safe_dir "$RUNTIME_BASE"
  STATE_UID="$(id -u)"
  PID_DIR="${RUNTIME_BASE}/hermes-spawn-${STATE_UID}"
  LOCK_DIR="${PID_DIR}/${SESSION_ID}.lock"
  PID_FILE="${PID_DIR}/${SESSION_ID}.pid"

  umask 077
  mkdir -p "$PID_DIR"
  chmod 700 "$PID_DIR"
  require_safe_dir "$PID_DIR"

  local ACTION="${1:-status}"
  shift || true
  local TASK="$*"

  case "$ACTION" in
    start)
      if [[ -z "$TASK" ]]; then
        echo "Usage: start <task description>" >&2
        exit 1
      fi
      validate_paths
      acquire_lock
      if [[ -f "$PID_FILE" ]]; then
        local existing_pid=""
        if read_pid_file; then
          existing_pid="$SPAWN_PID"
        else
          echo "⚠️ Ignoring malformed pid file at $PID_FILE" >&2
          rm -f "$PID_FILE"
          existing_pid=""
        fi
        if [[ -n "${existing_pid:-}" ]] && verify_hermes_pid "$existing_pid" "${SPAWN_STARTED:-}"; then
          echo "ERROR: Hermes already running for session ${SESSION_ID} (pid $existing_pid)" >&2
          exit 1
        fi
        rm -f "$PID_FILE"
      fi
      echo "🚀 Spawning Hermes agent for: $TASK"
      local log_file="${PID_DIR}/${SESSION_ID}.log"
      nohup env PYTHONDOTENV_SKIP=1 bash -c \
        "cd \"${HARNESS_ROOT}\" && exec python3 \"${PERP_SCRIPT}\" $(printf '%q' "$TASK")" \
        >"$log_file" 2>&1 &
      child_pid=$!
      disown "$child_pid" 2>/dev/null || true
      trap 'cleanup_spawn' EXIT
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
      child_pid=""
      trap 'release_lock' EXIT
      echo "✅ Hermes started (pid $child_pid, session ${SESSION_ID})"
      ;;
    stop)
      acquire_lock
      local pid=""
      if [[ -f "$PID_FILE" ]]; then
        if ! read_pid_file; then
          echo "⚠️ Ignoring malformed pid file at $PID_FILE" >&2
          rm -f "$PID_FILE"
        elif verify_hermes_pid "$SPAWN_PID" "$SPAWN_STARTED"; then
          pid="$SPAWN_PID"
          kill "$pid"
          local _ i
          for i in $(seq 1 10); do
            verify_hermes_pid "$pid" "$SPAWN_STARTED" || break
            sleep 0.2
          done
          if verify_hermes_pid "$pid" "$SPAWN_STARTED"; then
            echo "ERROR: Hermes pid $pid did not stop cleanly" >&2
            exit 1
          fi
          echo "✅ Hermes stopped (pid $pid)"
          rm -f "$PID_FILE"
        else
          echo "ℹ️ No active Hermes process for pid $SPAWN_PID" >&2
          rm -f "$PID_FILE"
        fi
      else
        echo "ℹ️ No Hermes pid file at $PID_FILE"
      fi
      ;;
    status)
      validate_paths
      if [[ -f "$PID_FILE" ]]; then
        if ! read_pid_file; then
          echo "⚠️ Ignoring malformed pid file at $PID_FILE" >&2
          rm -f "$PID_FILE"
          exit 1
        elif verify_hermes_pid "$SPAWN_PID" "$SPAWN_STARTED"; then
          echo "✅ Hermes running (pid $SPAWN_PID, session ${SESSION_ID})"
          exit 0
        fi
        echo "⚠️ Stale pid file — recorded pid $SPAWN_PID is not the expected hermes_harness.py process" >&2
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
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
