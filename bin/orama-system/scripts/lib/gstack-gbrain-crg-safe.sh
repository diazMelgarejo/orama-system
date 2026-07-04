#!/usr/bin/env bash
# gstack-gbrain-crg-safe.sh — error-resilient library for gstack/gbrain/CRG
# Source this in any skill that uses these tools. Provides:
#   - _detect_errors: pre-flight checks (non-fatal)
#   - _with_lock: file-lock guards for concurrent safety
#   - _retry_with_backoff: exponential backoff
#   - _handle_error: exit code interpretation
#   - _err_actionable: developer-friendly error messages
#   - _log_diagnostic: central diagnostic logging
#   - _health_check: post-operation verification
#
# Usage:
#   source "$ORAMA_ROOT/scripts/lib/gstack-gbrain-crg-safe.sh"
#   _detect_errors || { echo "cannot proceed"; return 1; }
#   _with_lock ~/.gstack/.gbrain-sync-state.json gbrain sync --repo .

set -uo pipefail

# Export timeouts as env vars (agents can override)
export GBRAIN_TIMEOUT=${GBRAIN_TIMEOUT:-120}
export GIT_TIMEOUT=${GIT_TIMEOUT:-30}
export CURL_CONNECT_TIMEOUT=${CURL_CONNECT_TIMEOUT:-10}
export CURL_MAX_TIME=${CURL_MAX_TIME:-120}

# Central diagnostic log (mode 644, auto-rotate weekly)
DIAG_LOG="${DIAG_LOG:-$HOME/.openclaw/logs/gstack-gbrain-crg.log}"

# Helper: simple logging (used before _log_diagnostic is called)
_log_safe() {
  local level=$1 message=$2
  printf '[gstack-safe] %s %s\n' "$level" "$message"
}

# Phase 0: Initialize diagnostic log (once per session)
_init_diagnostic_log() {
  local logdir="${DIAG_LOG%/*}"
  mkdir -p "$logdir" 2>/dev/null || true
  if [ ! -f "$DIAG_LOG" ]; then
    touch "$DIAG_LOG" 2>/dev/null || true
    chmod 644 "$DIAG_LOG" 2>/dev/null || true
  fi
}
_init_diagnostic_log

# Diagnostic logging (central record for all gstack/gbrain/CRG operations)
_log_diagnostic() {
  local level=$1 message=$2
  local ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '[%s] %s %s\n' "$ts" "$level" "$message" >> "$DIAG_LOG" 2>/dev/null || true
}

# Phase 1: Error Detection (PRE-FLIGHT CHECKS)
# Returns 0 if all checks pass, 1 + prints errors if any fail
_detect_errors() {
  local errors=() severity=()

  # Check 1: gbrain CLI available
  if ! command -v gbrain >/dev/null 2>&1; then
    errors+=("gbrain CLI not installed")
    severity+=("FATAL")
  fi

  # Check 2: gbrain local engine status
  if command -v gstack-gbrain-detect >/dev/null 2>&1; then
    local status=$(gstack-gbrain-detect 2>/dev/null | grep -o '"gbrain_local_status":[^,}]*' | sed 's/.*://; s/[ "]//g')
    case "$status" in
      "no-cli")
        errors+=("gbrain CLI not installed (detected)")
        severity+=("FATAL")
        ;;
      "missing-config")
        errors+=("gbrain config missing (call /setup-gbrain)")
        severity+=("WARN")
        ;;
      "broken-config")
        errors+=("gbrain config broken (point to missing engine)")
        severity+=("FATAL")
        ;;
      "broken-db")
        errors+=("gbrain database unreachable")
        severity+=("FATAL")
        ;;
    esac
  fi

  # Check 3: Autopilot jam detection
  if pgrep -f 'gbrain autopilot' >/dev/null 2>&1; then
    local ap_pid=$(pgrep -f 'gbrain autopilot' | head -1)
    local ap_cwd=$(lsof -a -p "$ap_pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
    if [ "${ap_cwd:-/}" = "/" ]; then
      errors+=("autopilot jam: cwd=/ (will jam sync)")
      severity+=("WARN")
      _log_diagnostic "WARN" "autopilot jam detected (pid $ap_pid, cwd=/)"
    fi
  fi

  # Check 4: Stale lock file (older than 10 min = stale)
  if [ -f ~/.gstack/.sync-gbrain.lock ]; then
    local age=$(( $(date +%s) - $(stat -f %m ~/.gstack/.sync-gbrain.lock 2>/dev/null || echo $(date +%s)) ))
    if [ "$age" -gt 600 ]; then
      errors+=("stale sync lock (age=${age}s, > 600s)")
      severity+=("WARN")
      _log_diagnostic "WARN" "stale sync lock detected (age=${age}s)"
    fi
  fi

  # Check 5: Concurrent write detection
  if [ -f ~/.gstack/.gbrain-sync-state.json ]; then
    if ! flock -n ~/.gstack/.gbrain-sync-state.json true 2>/dev/null; then
      errors+=("gbrain sync in progress (state file locked)")
      severity+=("WARN")
      _log_diagnostic "WARN" "concurrent sync detected (state file locked)"
    fi
  fi

  # Report errors
  if [ ${#errors[@]} -gt 0 ]; then
    _log_safe "WARN" "pre-flight errors detected:"
    for i in "${!errors[@]}"; do
      local sev="${severity[$i]:-INFO}"
      printf '  [%s] %s\n' "$sev" "${errors[$i]}"
      _log_diagnostic "$sev" "pre-flight: ${errors[$i]}"
    done

    # Fatal errors = return 1; warnings = return 0
    for sev in "${severity[@]}"; do
      [ "$sev" = "FATAL" ] && return 1
    done
    return 0
  fi

  return 0
}

# Phase 2: Retry with Exponential Backoff
# Usage: _retry_with_backoff <cmd> [args...]
_retry_with_backoff() {
  local max_attempts=3 attempt=1 delay=1
  while [ $attempt -le $max_attempts ]; do
    "$@" && return 0
    if [ $attempt -lt $max_attempts ]; then
      _log_diagnostic "INFO" "retry $attempt/$max_attempts failed; waiting ${delay}s"
      sleep $delay
      delay=$((delay * 2))
    fi
    attempt=$((attempt + 1))
  done
  _log_diagnostic "ERR" "max retries ($max_attempts) exceeded"
  return 1
}

# Phase 3: File-based Locking (prevent concurrent writes)
# Usage: _with_lock <lockfile> <cmd> [args...]
_with_lock() {
  if [ $# -lt 2 ]; then
    _log_safe "ERR" "_with_lock: usage: _with_lock <lockfile> <cmd> [args...]"
    return 1
  fi

  local lockfile="$1" timeout=10
  local cmd=("${@:2}")
  local lockfd=9  # Use FD 9 to avoid conflicts

  # Acquire lock
  exec {lockfd}>"$lockfile" 2>/dev/null || {
    _log_diagnostic "ERR" "cannot open lock file $lockfile"
    return 1
  }

  if ! flock -n -x -w $timeout $lockfd 2>/dev/null; then
    _log_diagnostic "WARN" "lock contention on $lockfile (timeout ${timeout}s)"
    exec {lockfd}>&-
    return 8  # Special exit code for lock contention
  fi

  # Execute command under lock
  _log_diagnostic "INFO" "acquired lock on $lockfile"
  "${cmd[@]}"
  local ret=$?

  # Release lock
  flock -u -x $lockfd 2>/dev/null || true
  exec {lockfd}>&-
  _log_diagnostic "INFO" "released lock on $lockfile (exit $ret)"
  return $ret
}

# Phase 4: Exit Code Interpretation & Recovery
# Usage: _handle_error <exit_code> <operation_name>
_handle_error() {
  if [ $# -lt 2 ]; then
    _log_safe "ERR" "_handle_error: usage: _handle_error <exit_code> <operation_name>"
    return 1
  fi

  local exit_code=$1 operation=$2
  case $exit_code in
    0)
      return 0
      ;;
    7|124)
      _log_diagnostic "WARN" "$operation timed out (code $exit_code)"
      printf 'TIMEOUT\n'  # Signal to caller to retry
      return $exit_code
      ;;
    8)
      _log_diagnostic "WARN" "$operation lock contention (code $exit_code)"
      printf 'LOCK_CONTENTION\n'  # Signal to caller to wait
      return $exit_code
      ;;
    127)
      _log_diagnostic "ERR" "$operation command not found (code $exit_code)"
      printf 'NOT_FOUND\n'  # Signal to caller: run setup
      return 1
      ;;
    *)
      _log_diagnostic "ERR" "$operation failed (exit code $exit_code)"
      printf 'FAILED\n'  # Signal to caller: fatal
      return 1
      ;;
  esac
}

# Phase 5: Actionable Error Messages (FOR NEW AGENTS)
# Usage: _err_actionable <symptom> <root_cause> <fix>
_err_actionable() {
  if [ $# -lt 3 ]; then
    _log_safe "ERR" "_err_actionable: usage: _err_actionable <symptom> <root_cause> <fix>"
    return 1
  fi

  local symptom=$1 root_cause=$2 fix=$3
  local msg="
❌ $symptom

ROOT CAUSE:
  $root_cause

FIX:
  $fix

IF THIS PERSISTS:
  1. Check status: gbrain doctor --fast
  2. Run heal: bash ~/.claude/skills/gstack/bin/gstack-gbrain-detect
  3. Check logs: tail -20 ~/.openclaw/logs/gstack-gbrain-crg.log
  4. Open issue: https://github.com/diazMelgarejo/orama-system/issues
"
  printf '%s\n' "$msg" >&2
  _log_diagnostic "ERR" "actionable error: $symptom (root: $root_cause)"
}

# Phase 6: Health Verification (AFTER OPERATIONS)
# Usage: _health_check <operation_name>
# Returns 0 if ≥2 checks pass, 1 if <2 pass
_health_check() {
  if [ $# -lt 1 ]; then
    _log_safe "ERR" "_health_check: usage: _health_check <operation_name>"
    return 1
  fi

  local operation=$1
  local checks_passed=0 checks_total=0

  # Check 1: gbrain CLI works
  checks_total=$((checks_total + 1))
  if gbrain doctor --fast --json 2>/dev/null | jq -e '.status == "ok"' >/dev/null 2>&1; then
    checks_passed=$((checks_passed + 1))
    _log_diagnostic "INFO" "health check $operation: gbrain OK"
  else
    _log_diagnostic "WARN" "health check $operation: gbrain not OK"
  fi

  # Check 2: gstack config valid
  checks_total=$((checks_total + 1))
  if gstack-config get proactive >/dev/null 2>&1; then
    checks_passed=$((checks_passed + 1))
    _log_diagnostic "INFO" "health check $operation: gstack config OK"
  else
    _log_diagnostic "WARN" "health check $operation: gstack config not OK"
  fi

  _log_diagnostic "INFO" "health check after $operation: $checks_passed/$checks_total passed"
  [ "$checks_passed" -ge 2 ] && return 0 || return 1
}

# Export all functions
export -f _log_safe _log_diagnostic _detect_errors _retry_with_backoff
export -f _with_lock _handle_error _err_actionable _health_check
