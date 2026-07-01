#!/usr/bin/env bash
# Probe the Cline CLI: presence, version, and configured providers.
# Sourced by bind_cline_backend.sh; also runnable standalone.

set -euo pipefail

cline_bin=""
if command -v cline >/dev/null 2>&1; then
  cline_bin="$(command -v cline)"
fi

if [[ -z "$cline_bin" ]]; then
  echo '{"present":false}'
  exit 0
fi

version="$(cline version 2>/dev/null || echo 'unknown')"
providers_file="$HOME/.cline/data/settings/providers.json"
last_provider=""
if [[ -f "$providers_file" ]]; then
  last_provider="$(jq -r '.lastUsedProvider // ""' "$providers_file" 2>/dev/null || echo '')"
fi

echo "{\"present\":true,\"bin\":\"$cline_bin\",\"version\":\"$version\",\"lastUsedProvider\":\"$last_provider\"}"
