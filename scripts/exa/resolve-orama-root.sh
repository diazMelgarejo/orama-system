#!/usr/bin/env bash
# resolve-orama-root.sh — find the orama-system checkout without assuming
# a fixed offset from any single root var.
#
# Why this exists: orama-system's location relative to a caller repo is
# NOT constant across checkouts. Observed topologies: sibling to the
# caller ("$X/orama-system" and "$X/perplexity-api/Perpetua-Tools" both
# under "$X"), or one level removed ("aunt" — Perpetua-Tools nested under
# perplexity-api/, so orama-system is its parent's sibling, not its own).
# Hardcoding "$OPENCLAW_ROOT/orama-system" or "$HOME/code/OpenClaw/orama-
# system" (both seen in this workspace's MCP configs) breaks the moment a
# checkout doesn't match that one assumed layout — see
# docs/v2/47-portable-memory-local-topology-invariant.md for the general
# no-hardcoded-topology rule this follows.
#
# Resolution order (first match wins, cheapest checks first):
#   1. Cached result from a prior run (~/.openclaw/state/orama-root.cache),
#      re-validated (dir still exists + still looks like orama-system)
#      before trusting it — cheap, and avoids re-walking on every MCP
#      server launch.
#   2. ORAMA_SYSTEM_ROOT env var, if set and valid.
#   3. Walk up from this script's own location (works when this exact
#      copy of the script is the one being invoked from inside a real
#      orama-system checkout).
#   4. Walk up from $PWD looking for a sibling or aunt "orama-system" dir.
#   5. Bounded find under $HOME (maxdepth 4) as the last resort.
#
# Usage: ORAMA_ROOT="$(bash resolve-orama-root.sh)" — prints the absolute
# path on stdout, nothing else. Exits non-zero with a message on stderr
# if no valid orama-system checkout is found.

set -euo pipefail

CACHE_FILE="${HOME}/.openclaw/state/orama-root.cache"

_is_orama_root() {
  # A real orama-system checkout has this marker script AND a .git dir —
  # cheap, hard-to-false-positive check.
  [[ -d "$1/.git" && -f "$1/scripts/exa/exa-mcp-wrapper.sh" ]]
}

_try_cache() {
  [[ -f "$CACHE_FILE" ]] || return 1
  local cached
  cached="$(cat "$CACHE_FILE" 2>/dev/null || true)"
  [[ -n "$cached" ]] && _is_orama_root "$cached" && { echo "$cached"; return 0; }
  return 1
}

_try_env() {
  [[ -n "${ORAMA_SYSTEM_ROOT:-}" ]] && _is_orama_root "$ORAMA_SYSTEM_ROOT" && { echo "$ORAMA_SYSTEM_ROOT"; return 0; }
  return 1
}

_try_self_location() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # This script lives at <orama-root>/scripts/exa/resolve-orama-root.sh
  local candidate="${script_dir}/../.."
  candidate="$(cd "$candidate" 2>/dev/null && pwd || true)"
  [[ -n "$candidate" ]] && _is_orama_root "$candidate" && { echo "$candidate"; return 0; }
  return 1
}

_try_pwd_walk() {
  local dir="$PWD"
  for _ in 1 2 3 4; do
    # Sibling case: <dir>/orama-system
    if _is_orama_root "$dir/orama-system"; then echo "$dir/orama-system"; return 0; fi
    # Aunt case: <dir>/../orama-system
    local aunt="$dir/../orama-system"
    aunt="$(cd "$aunt" 2>/dev/null && pwd || true)"
    if [[ -n "$aunt" ]] && _is_orama_root "$aunt"; then echo "$aunt"; return 0; fi
    dir="$(cd "$dir/.." 2>/dev/null && pwd || true)"
    [[ -z "$dir" || "$dir" == "/" ]] && break
  done
  return 1
}

_try_bounded_find() {
  local found
  found="$(find "$HOME" -maxdepth 4 -type d -name orama-system 2>/dev/null | while read -r d; do
    _is_orama_root "$d" && { echo "$d"; break; }
  done)"
  [[ -n "$found" ]] && { echo "$found"; return 0; }
  return 1
}

RESULT=""
for _resolver in _try_cache _try_env _try_self_location _try_pwd_walk _try_bounded_find; do
  if RESULT="$($_resolver)"; then
    break
  fi
done

if [[ -z "$RESULT" ]]; then
  echo "resolve-orama-root.sh: could not locate an orama-system checkout" >&2
  exit 1
fi

mkdir -p "$(dirname "$CACHE_FILE")" 2>/dev/null || true
echo "$RESULT" > "$CACHE_FILE" 2>/dev/null || true
echo "$RESULT"
