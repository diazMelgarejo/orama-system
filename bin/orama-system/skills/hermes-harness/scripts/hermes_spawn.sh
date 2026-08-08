#!/usr/bin/env bash
# Hermes spawn lifecycle — extracted from hermes-spawn/SKILL.md for testability.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve_perp_harness.sh
source "${SCRIPT_DIR}/resolve_perp_harness.sh"
# shellcheck source=json-response.sh
source "${SCRIPT_DIR}/json-response.sh"

JSON_OUT=0
SKILL_ID="hermes-spawn"
COMMAND_NAME="hermes-spawn"

# sanitize_session_id validates HERMES_SPAWN_SESSION and stores the resulting safe session identifier in SESSION_ID.
sanitize_session_id() {
  local raw="${HERMES_SPAWN_SESSION:-default}"
  case "$raw" in
    *[!a-zA-Z0-9_-]*|*..*|""|"."|"..")
      if (( JSON_OUT )); then
        hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "start" "invalid_session" \
          "HERMES_SPAWN_SESSION must match [a-zA-Z0-9_-]+ (got: $raw)" \
          '["set HERMES_SPAWN_SESSION to a safe session id"]'
      fi
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

# verify_hermes_pid confirms that a process ID belongs to the resolved Perpetua Tools script and, when provided, matches the expected start time.
# @param pid The process ID to verify.
# @param expected_started The expected process start timestamp, if available.
verify_hermes_pid() {
  local pid="$1"
  local expected_started="${2:-}"
  local args="" actual_started=""
  [[ -n "$pid" ]] || return 1
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  args="$(pid_command "$pid")"
  [[ -n "$args" ]] || return 1
  # Match resolved PT script path (macOS ps may show "Python" not "python3").
  case "$args" in
    *"${PERP_SCRIPT}"*) ;;
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

# recover_stale_lock removes an unused session lock or exits when the lock has an active or missing owner.
recover_stale_lock() {
  local lock_pid=""
  if [[ ! -d "$LOCK_DIR" ]]; then
    return 0
  fi
  if [[ ! -f "${LOCK_DIR}/pid" ]]; then
    if (( JSON_OUT )); then
      hermes_result_blocked "$SKILL_ID" "$COMMAND_NAME" "start" \
        "lock exists without owner metadata" '["wait for the other session or remove stale lock"]'
    fi
    echo "ERROR: lock exists without owner metadata — busy" >&2
    exit 1
  fi
  lock_pid="$(tr -d '\r' <"${LOCK_DIR}/pid" | head -1)"
  if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
    if (( JSON_OUT )); then
      hermes_result_blocked "$SKILL_ID" "$COMMAND_NAME" "start" \
        "another hermes-spawn session is active for ${SESSION_ID} (lock pid $lock_pid)" \
        '["run hermes-spawn stop or use a different HERMES_SPAWN_SESSION"]'
    fi
    echo "ERROR: another hermes-spawn session is active for ${SESSION_ID} (lock pid $lock_pid)" >&2
    exit 1
  fi
  rm -rf "$LOCK_DIR"
}

# acquire_lock obtains the per-session lock, records the current process ID as its owner, and registers cleanup on exit.
acquire_lock() {
  recover_stale_lock
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    recover_stale_lock
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
      if (( JSON_OUT )); then
        hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "start" "lock_failed" \
          "could not acquire lock for ${SESSION_ID}" \
          '["inspect lock dir under XDG_RUNTIME_DIR"]'
      fi
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

# validate_paths verifies that the Hermes harness root and Perpetua Tools script exist, reporting an error and exiting if either path is unavailable.
validate_paths() {
  if [[ ! -d "$HARNESS_ROOT" ]]; then
    if (( JSON_OUT )); then
      hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "${ACTION:-status}" "harness_missing" \
        "Hermes harness root not found: $HARNESS_ROOT" \
        '["set HERMES_HOME or install Hermes"]'
    fi
    echo "ERROR: Hermes harness root not found: $HARNESS_ROOT" >&2
    exit 1
  fi
  if [[ ! -f "$PERP_SCRIPT" ]]; then
    if (( JSON_OUT )); then
      hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "${ACTION:-status}" "pt_script_missing" \
        "Hermes harness script not found: $PERP_SCRIPT" \
        '["set PERPETUA_TOOLS_ROOT or clone Perpetua-Tools"]'
    fi
    echo "ERROR: Hermes harness script not found: $PERP_SCRIPT" >&2
    exit 1
  fi
}

# emit_json_data emits a successful JSON response containing the provided data.
emit_json_data() {
  local data="$1"
  hermes_result_ok "$SKILL_ID" "$COMMAND_NAME" "$ACTION" "$data"
}

# main manages the Hermes agent lifecycle for a session, supporting start, stop, and status actions with optional JSON output.
main() {
  local args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json)
        JSON_OUT=1
        shift
        ;;
      *)
        args+=("$1")
        shift
        ;;
    esac
  done

  ACTION="${args[0]:-status}"
  local TASK=""
  if ((${#args[@]} > 1)); then
    TASK="${args[*]:1}"
  fi

  sanitize_session_id
  resolve_harness_root
  if ! PERP_SCRIPT="$(resolve_perp_harness_script)"; then
    if (( JSON_OUT )); then
      hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "$ACTION" "pt_root_unresolved" \
        "Perpetua-Tools root not resolved" \
        '["set PERPETUA_TOOLS_ROOT or clone Perpetua-Tools"]'
    fi
    echo "ERROR: Perpetua-Tools root not resolved" >&2
    exit 1
  fi

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

  case "$ACTION" in
    start)
      if [[ -z "$TASK" ]]; then
        if (( JSON_OUT )); then
          hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "start" "usage" \
            "Usage: start <task description>" \
            '["provide a task description"]'
        fi
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
          if (( JSON_OUT )); then
            hermes_result_blocked "$SKILL_ID" "$COMMAND_NAME" "start" \
              "Hermes already running for session ${SESSION_ID} (pid $existing_pid)" \
              '["run hermes-spawn stop first"]'
          fi
          echo "ERROR: Hermes already running for session ${SESSION_ID} (pid $existing_pid)" >&2
          exit 1
        fi
        rm -f "$PID_FILE"
      fi
      echo "🚀 Spawning Hermes agent for: $TASK" >&2
      local log_file="${PID_DIR}/${SESSION_ID}.log"
      nohup env PYTHONDOTENV_SKIP=1 bash -c \
        "cd \"${HARNESS_ROOT}\" && exec python3 \"${PERP_SCRIPT}\" $(printf '%q' "$TASK")" \
        >"$log_file" 2>&1 &
      child_pid=$!
      disown "$child_pid" 2>/dev/null || true
      trap 'cleanup_spawn' EXIT
      if ! kill -0 "$child_pid" 2>/dev/null; then
        if (( JSON_OUT )); then
          hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "start" "start_failed" \
            "Hermes failed to start" \
            '["inspect spawn log file"]'
        fi
        echo "ERROR: Hermes failed to start" >&2
        exit 1
      fi
      sleep 1
      if ! verify_hermes_pid "$child_pid"; then
        if (( JSON_OUT )); then
          hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "start" "immediate_exit" \
            "Hermes exited immediately after launch" \
            '["inspect spawn log file"]'
        fi
        echo "ERROR: Hermes exited immediately after launch" >&2
        exit 1
      fi
      local started_pid="$child_pid"
      write_pid_file "$started_pid"
      child_pid=""
      trap 'release_lock' EXIT
      if (( JSON_OUT )); then
        local log_escaped
        log_escaped="$(json_escape "$log_file")"
        # hermes_result_ok (called by emit_json_data) exits internally,
        # so the unconditional human-readable echo below is unreachable
        # once we take this branch -- print it here, to stderr so it
        # doesn't interfere with JSON stdout parsing, for operator
        # visibility even in JSON/automation mode.
        echo "✅ Hermes started (pid $started_pid, session ${SESSION_ID})" >&2
        emit_json_data "{\"pid\":${started_pid},\"session\":\"${SESSION_ID}\",\"log_file\":${log_escaped}}"
      fi
      echo "✅ Hermes started (pid $started_pid, session ${SESSION_ID})"
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
            if (( JSON_OUT )); then
              hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "stop" "stop_failed" \
                "Hermes pid $pid did not stop cleanly" \
                '["kill -9 manually if needed"]'
            fi
            echo "ERROR: Hermes pid $pid did not stop cleanly" >&2
            exit 1
          fi
          rm -f "$PID_FILE"
          if (( JSON_OUT )); then
            emit_json_data "{\"pid\":${pid},\"session\":\"${SESSION_ID}\",\"stopped\":true}"
          fi
          echo "✅ Hermes stopped (pid $pid)"
        else
          echo "ℹ️ No active Hermes process for pid $SPAWN_PID" >&2
          rm -f "$PID_FILE"
          if (( JSON_OUT )); then
            emit_json_data "{\"session\":\"${SESSION_ID}\",\"stopped\":false,\"reason\":\"stale_pid\"}"
          fi
        fi
      else
        if (( JSON_OUT )); then
          emit_json_data "{\"session\":\"${SESSION_ID}\",\"stopped\":false,\"reason\":\"no_pid_file\"}"
        fi
        echo "ℹ️ No Hermes pid file at $PID_FILE"
      fi
      ;;
    status)
      validate_paths
      if [[ -f "$PID_FILE" ]]; then
        if ! read_pid_file; then
          if (( JSON_OUT )); then
            hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "status" "malformed_pid" \
              "malformed pid file at $PID_FILE" \
              '["remove stale pid file or run stop"]'
          fi
          echo "⚠️ Ignoring malformed pid file at $PID_FILE" >&2
          rm -f "$PID_FILE"
          exit 1
        elif verify_hermes_pid "$SPAWN_PID" "$SPAWN_STARTED"; then
          if (( JSON_OUT )); then
            emit_json_data "{\"pid\":${SPAWN_PID},\"session\":\"${SESSION_ID}\",\"running\":true}"
          fi
          echo "✅ Hermes running (pid $SPAWN_PID, session ${SESSION_ID})"
          exit 0
        fi
        if (( JSON_OUT )); then
          hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "status" "stale_pid" \
            "stale pid file — recorded pid $SPAWN_PID is not the expected hermes_harness.py process" \
            '["run hermes-spawn stop to clean up"]'
        fi
        echo "⚠️ Stale pid file — recorded pid $SPAWN_PID is not the expected hermes_harness.py process" >&2
        exit 1
      fi
      if (( JSON_OUT )); then
        emit_json_data "{\"session\":\"${SESSION_ID}\",\"running\":false}"
      fi
      echo "ℹ️ No active Hermes session ${SESSION_ID} (no pid file)"
      exit 1
      ;;
    *)
      if (( JSON_OUT )); then
        hermes_result_error "$SKILL_ID" "$COMMAND_NAME" "$ACTION" "unknown_action" \
          "Unknown action: $ACTION (expected start|stop|status)" \
          '["use start, stop, or status"]'
      fi
      echo "Unknown action: $ACTION (expected start|stop|status)" >&2
      exit 1
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
