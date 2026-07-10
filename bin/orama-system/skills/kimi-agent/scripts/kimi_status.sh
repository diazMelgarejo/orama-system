#!/usr/bin/env bash
# kimi_status.sh — non-destructive health probe for the Kimi Code CLI fan-out agent.
# Mirrors the openclaw-status skill's health-check shape. Never mutates state;
# safe to call from a pulse cron before dispatching a fan-out task.
set -uo pipefail

export PATH="$HOME/.kimi-code/bin:$PATH"

if ! command -v kimi >/dev/null 2>&1; then
  echo '{"kimi_installed": false}'
  exit 2
fi

VERSION="$(kimi --version 2>/dev/null || echo "unknown")"
DOCTOR_OK="false"
kimi doctor >/dev/null 2>&1 && DOCTOR_OK="true"

PROVIDER_COUNT="$(kimi provider list 2>/dev/null | grep -vc "No providers configured")"
PROVIDER_COUNT="${PROVIDER_COUNT:-0}"
SERVER_CLIENTS="$(kimi server ps --json 2>/dev/null || echo "[]")"

cat <<JSON
{
  "kimi_installed": true,
  "version": "${VERSION}",
  "doctor_ok": ${DOCTOR_OK},
  "provider_lines": ${PROVIDER_COUNT},
  "server_clients": ${SERVER_CLIENTS}
}
JSON

[ "$DOCTOR_OK" = "true" ] || exit 1
exit 0
