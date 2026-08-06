#!/usr/bin/env bash
# Canonical Hermes result envelope emitter (stdout=JSON only; stderr=logs).
# See ../references/hermes-universal-invocation-protocol.md
set -euo pipefail

json_escape() {
  local s="${1:-}"
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/\\r}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

log() {
  printf '[json-response] %s\n' "${1:-}" >&2
}

_emit_result() {
  local status="${1:-error}"
  local skill_id="${2:-}"
  local command="${3:-}"
  local action="${4:-}"
  local data="${5:-{}}"
  local files_modified="${6:-[]}"
  local follow_up_actions="${7:-[]}"
  local warnings="${8:-[]}"
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return default

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
    "error": load_obj(error_raw, None) if error_raw not in ("", "null") else None,
}
print(json.dumps(payload, separators=(",", ":")))
PY
}

hermes_result_ok() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local data="${4:-{}}"
  _emit_result "ok" "$skill_id" "$command" "$action" "$data" "[]" "[]" "[]" "null"
  exit 0
}

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
  err_obj="$(printf '{"code":"%s","message":"%s"}' "$(json_escape "$code")" "$msg_escaped")"
  _emit_result "error" "$skill_id" "$command" "$action" "{}" "[]" "$follow_up" "[]" "$err_obj"
  exit 1
}

hermes_result_blocked() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local message="${4:-Precondition failed}"
  local follow_up="${5:-[]}"
  local msg_escaped
  msg_escaped="$(json_escape "$message")"
  local err_obj
  err_obj="$(printf '{"code":"%s","message":"%s"}' "$(json_escape "${command}_blocked")" "$msg_escaped")"
  _emit_result "blocked" "$skill_id" "$command" "$action" "{}" "[]" "$follow_up" "[]" "$err_obj"
  exit 1
}

hermes_result_partial() {
  local skill_id="${1:-}"
  local command="${2:-}"
  local action="${3:-}"
  local data="${4:-{}}"
  local warnings="${5:-[]}"
  local follow_up="${6:-[]}"
  _emit_result "partial" "$skill_id" "$command" "$action" "$data" "[]" "$follow_up" "$warnings" "null"
  exit 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  log 'Library loaded directly; source this file from another script.'
fi
