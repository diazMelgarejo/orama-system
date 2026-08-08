#!/usr/bin/env bash
# Canonical Hermes result envelope emitter (stdout=JSON only; stderr=logs).
# See ../references/hermes-universal-invocation-protocol.md
set -euo pipefail

# json_escape escapes backslashes, double quotes, and control characters in a string for JSON output.
json_escape() {
  local s="${1:-}"
  jq -Rn --arg s "$s" '$s'
}

# log writes a prefixed message to standard error.
log() {
  printf '[json-response] %s\n' "${1:-}" >&2
}

# _emit_result emits a JSON result envelope to stdout, applying defaults and structured handling for malformed fields.
_emit_result() {
  local status="${1:-error}"
  local skill_id="${2:-}"
  local command="${3:-}"
  local action="${4:-}"
  local data="${5:-"{}"}"
  local files_modified="${6:-"[]"}"
  local follow_up_actions="${7:-"[]"}"
  local warnings="${8:-"[]"}"
  local error_json="${9:-null}"
  local agent_id="${10:-hermes}"
  local executor_id="${11:-hermes}"

  PYTHONDOTENV_SKIP=1 python3 - "$status" "$skill_id" "$agent_id" "$executor_id" \
    "$command" "$action" "$data" "$files_modified" "$follow_up_actions" \
    "$warnings" "$error_json" <<'PY'
import json
import sys

(
    status,
    skill_id,
    agent_id,
    executor_id,
    command,
    action,
    data_raw,
    files_raw,
    follow_raw,
    warnings_raw,
    error_raw,
) = sys.argv[1:12]

def load_obj(raw, default):
    if not raw:
        return default
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON payload for envelope field: {exc}", file=sys.stderr)
        sys.exit(1)
    if isinstance(default, dict) and not isinstance(value, dict):
        print(f"invalid JSON payload for envelope field: expected dict, got {type(value).__name__}", file=sys.stderr)
        sys.exit(1)
    if isinstance(default, list) and not isinstance(value, list):
        print(f"invalid JSON payload for envelope field: expected list, got {type(value).__name__}", file=sys.stderr)
        sys.exit(1)
    return value

def load_error(raw):
    if raw in ("", "null"):
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"code": "invalid_error", "message": raw}
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {"code": "invalid_error", "message": str(value)}

payload = {
    "status": status,
    "skill_id": skill_id or None,
    "agent_id": agent_id or "hermes",
    "executor_id": executor_id or "hermes",
    "command": command or None,
    "action": action or None,
    "data": load_obj(data_raw, {}),
    "files_modified": load_obj(files_raw, []),
    "follow_up_actions": load_obj(follow_raw, []),
    "warnings": load_obj(warnings_raw, []),
    "error": load_error(error_raw),
}
print(json.dumps(payload, separators=(",", ":")))
PY
}

# hermes_result_ok emits a successful result envelope with the supplied skill, command, action, and data, then exits with status 0.
hermes_result_ok() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local data="${4:-"{}"}"
  _emit_result "ok" "$skill_id" "$command" "$action" "$data" "[]" "[]" "[]" "null"
  exit 0
}

# hermes_result_error emits an error result with the supplied error details and exits with status 1.
# @param skill_id The identifier of the skill associated with the result.
# @param command The command associated with the result.
# @param action The action associated with the result.
# @param code The error code, defaulting to `command_error`.
# @param message The error message, defaulting to `Unknown error`.
# @param follow_up JSON-encoded follow-up actions for the result, defaulting to `[]`.
hermes_result_error() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local code="${4:-command_error}"
  local message="${5:-Unknown error}"
  local follow_up="${6:-[]}"
  local msg_escaped
  msg_escaped="$(json_escape "$message")"
  local err_obj
  err_obj="$(printf '{"code":%s,"message":%s}' "$(json_escape "$code")" "$msg_escaped")"
  _emit_result "error" "$skill_id" "$command" "$action" "{}" "[]" "$follow_up" "[]" "$err_obj"
  exit 1
}

# hermes_result_blocked emits a blocked result with a command-specific error and exits with status 1.
hermes_result_blocked() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local message="${4:-Precondition failed}"
  local follow_up="${5:-[]}"
  local msg_escaped
  msg_escaped="$(json_escape "$message")"
  local err_obj
  err_obj="$(printf '{"code":%s,"message":%s}' "$(json_escape "${command}_blocked")" "$msg_escaped")"
  _emit_result "blocked" "$skill_id" "$command" "$action" "{}" "[]" "$follow_up" "[]" "$err_obj"
  exit 1
}

# hermes_result_partial emits a partial Hermes result with required follow-up actions.
hermes_result_partial() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local data="${4:-"{}"}"
  local warnings="${5:-"[]"}"
  local follow_up="${6:-"[]"}"
  # partial means follow-up is required — reject empty follow-up lists
  if [[ -z "$follow_up" || "$follow_up" == "[]" ]]; then
    hermes_result_error "$skill_id" "$command" "$action" "partial_missing_follow_up" \
      "partial results require non-empty follow_up_actions" \
      '["provide follow_up_actions or emit ok when no follow-up is needed"]'
  fi
  _emit_result "partial" "$skill_id" "$command" "$action" "$data" "[]" "$follow_up" "$warnings" "null"
  exit 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  log 'Library loaded directly; source this file from another script.'
fi
