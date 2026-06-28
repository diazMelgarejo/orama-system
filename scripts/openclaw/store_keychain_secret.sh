#!/usr/bin/env bash
# store_keychain_secret.sh — read secret from stdin (never argv), store in macOS Keychain.
# Usage: printf '%s' "$secret" | scripts/openclaw/store_keychain_secret.sh <service> [account]
set -euo pipefail

service="${1:?keychain service required (e.g. openclaw.my-secret)}"
account="${2:-${USER:?USER must be set}}"

if [ ! -t 0 ] && [ -p /dev/stdin ]; then
  secret="$(cat)"
else
  read -rs secret
  printf '\n' >&2
fi

if [ -z "$secret" ]; then
  echo "store_keychain_secret: empty secret on stdin" >&2
  exit 1
fi

tmp="$(mktemp -t openclaw-kc.XXXXXX)"
chmod 600 "$tmp"
cleanup() {
  rm -f "$tmp"
}
trap cleanup EXIT

printf '%s' "$secret" > "$tmp"
unset secret

/usr/bin/security add-generic-password -a "$account" -s "$service" -w "$(cat "$tmp")" -U
