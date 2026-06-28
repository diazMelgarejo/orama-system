#!/usr/bin/env bash
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
  local msg="${1:-}"
  printf '[json-response] %s\n' "$msg" >&2
}

json_ok() {
  local data="${1:-null}"
  printf '{"status":"ok","data":%s}\n' "$data"
  exit 0
}

json_err() {
  local msg
  msg="$(json_escape "${1:-Unknown error}")"
  printf '{"status":"error","message":"%s"}\n' "$msg"
  exit 1
}

json_warn() {
  local msg
  msg="$(json_escape "${1:-Warning}")"
  printf '{"status":"warn","message":"%s"}\n' "$msg"
  exit 0
}

require_cmd() {
  local name="${1:-}"
  if [[ -z "$name" ]]; then
    json_err 'require_cmd expects a command name'
  fi
  if ! command -v "$name" >/dev/null 2>&1; then
    json_err "Required command not found: $name"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  log 'Library loaded directly; source this file from another script.'
fi
