#!/usr/bin/env bash
# load-local.sh — Source gitignored repo env files (no secrets in tracked files).
# Order: .env (base) then .env.local (override). Optional: ~/.orama-system/env
#
# Usage (from repo root or any subdir):
#   source scripts/env/load-local.sh
#   # or: . scripts/env/load-local.sh
#
# Idempotent — safe to source multiple times.
set -euo pipefail

_load_local_repo_root() {
  if [ -n "${REPO_ROOT:-}" ] && [ -f "${REPO_ROOT}/.env.example" ]; then
    printf '%s\n' "$REPO_ROOT"
    return 0
  fi
  local src="${BASH_SOURCE[0]:-$0}"
  local d
  d="$(cd "$(dirname "$src")/../.." && pwd)"
  if [ -f "$d/.env.example" ] && [ -d "$d/bin/orama-system" ]; then
    printf '%s\n' "$d"
    return 0
  fi
  d="$(pwd)"
  while [ "$d" != "/" ]; do
    if [ -f "$d/.env.example" ] && [ -d "$d/bin/orama-system" ]; then
      printf '%s\n' "$d"
      return 0
    fi
    d="$(dirname "$d")"
  done
  return 1
}

if [ -z "${REPO_ROOT:-}" ]; then
  REPO_ROOT="$(_load_local_repo_root)" || REPO_ROOT=""
  export REPO_ROOT
fi

_load_local_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  set -a
  # shellcheck disable=SC1090
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -n "$line" ] || continue
    case "$line" in
      *=*)
        key="${line%%=*}"
        val="${line#*=}"
        key="$(printf '%s' "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        val="$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")"
        [ -n "$key" ] && export "$key=$val"
        ;;
    esac
  done <"$f"
  set +a
}

if [ -n "$REPO_ROOT" ]; then
  _load_local_file "$REPO_ROOT/.env"
  _load_local_file "$REPO_ROOT/.env.local"
fi

if [ -f "${HOME}/.orama-system/env" ]; then
  _load_local_file "${HOME}/.orama-system/env"
fi

# Auto-export OPENCLAW_ROOT when layout matches package install
if [ -z "${OPENCLAW_ROOT:-}" ] && [ -n "$REPO_ROOT" ]; then
  _parent="$(dirname "$REPO_ROOT")"
  if [ -d "$_parent" ]; then
    export OPENCLAW_ROOT="$_parent"
  fi
fi
