#!/usr/bin/env bash
# resolve-openclaw.sh — canonical OpenClaw CLI resolver ("look at the right
# places when it seems broken").
#
# WHY THIS EXISTS
# ~/.local/bin/openclaw is a pnpm cmd-shim reached through a symlink. The shim
# computes basedir=$(dirname "$0"), but $0 is the *symlink* path
# (~/.local/bin/openclaw), so it resolves ../openclaw/openclaw.mjs to
# ~/.local/openclaw/openclaw.mjs — which does not exist. Result:
#   Error: Cannot find module '.../.local/openclaw/openclaw.mjs'
# Meanwhile THREE openclaw installs can coexist on one machine:
#   - npm global under nvm node (e.g. v24) — RUNS THE GATEWAY, newest, canonical
#   - $OPENCLAW_TREE/AlphaClaw/node_modules/openclaw (pnpm) — older
#   - ~/.alphaclaw/node_modules/openclaw — STALE orphan (do NOT use)
# This resolver always finds a WORKING openclaw, prefers the one that actually
# runs the gateway, and never resolves to the stale install.
#
# USAGE
#   resolve-openclaw.sh <args...>   # exec openclaw with args (drop-in CLI)
#   resolve-openclaw.sh --which     # print "<node>\t<entrypoint>" and exit 0
#   OPENCLAW_NODE=/path/node OPENCLAW_ENTRY=/path/index.js resolve-openclaw.sh …
#                                   # force a specific invocation (override)
#
# CONTRACT: prints nothing to stdout except in --which mode; diagnostics go to
# stderr. Exit 0 if a working openclaw is found, 3 if none verifies.

set -u

STALE_PREFIX="$HOME/.alphaclaw/node_modules/openclaw"   # 2026.4.24 orphan — blacklisted

# Derive the OpenClaw tree from this script's own location, so no workstation
# path is ever hardcoded. This file lives at:
#   <tree>/orama-system/scripts/openclaw/resolve-openclaw.sh
_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd)"
OPENCLAW_TREE="$(cd "$_SELF_DIR/../../.." >/dev/null 2>&1 && pwd || echo "$HOME")"

_have() { command -v "$1" >/dev/null 2>&1; }

# Bounded version check (macOS has no `timeout`; prefer gtimeout, else run bare).
_verify() {
  # $1=node $2=entry  -> 0 if `node entry --version` prints "OpenClaw"
  local node="$1" entry="$2" out
  [ -x "$node" ] || node="$(command -v node 2>/dev/null)"
  [ -n "$node" ] && [ -e "$entry" ] || return 1
  case "$entry" in "$STALE_PREFIX"/*) return 1 ;; *".disabled"*) return 1 ;; esac
  if _have gtimeout; then
    out="$(gtimeout 30 "$node" "$entry" --version 2>/dev/null)"
  else
    out="$("$node" "$entry" --version 2>/dev/null)"
  fi
  printf '%s' "$out" | grep -qi "OpenClaw"
}

# Candidate 0: explicit override.
_cand_override() {
  [ -n "${OPENCLAW_ENTRY:-}" ] || return 1
  printf '%s\t%s\n' "${OPENCLAW_NODE:-$(command -v node)}" "$OPENCLAW_ENTRY"
}

# Candidate 1: whatever the launchd gateway actually runs (source of truth).
_cand_gateway() {
  local plist="$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist" node="" entry="" a
  [ -f "$plist" ] || return 1
  _have /usr/libexec/PlistBuddy || return 1
  while IFS= read -r a; do
    case "$a" in
      */bin/node) node="$a" ;;
      *index.js|*openclaw.mjs) entry="$a" ;;
    esac
  done <<EOF
$(/usr/libexec/PlistBuddy -c "Print :ProgramArguments" "$plist" 2>/dev/null | sed -e 's/^[[:space:]]*//' -e '/^Array {/d' -e '/^}/d')
EOF
  [ -n "$entry" ] || return 1
  printf '%s\t%s\n' "${node:-$(command -v node)}" "$entry"
}

# Candidate 2: npm global openclaw under any nvm node (globbed paths sort
# ascending, so the last match wins == newest version directory).
_cand_npm_global() {
  local d node entry best=""
  for d in "$HOME"/.nvm/versions/node/*/lib/node_modules/openclaw; do
    [ -d "$d" ] || continue
    node="${d%/lib/node_modules/openclaw}/bin/node"
    if   [ -e "$d/dist/index.js" ]; then entry="$d/dist/index.js"
    elif [ -e "$d/openclaw.mjs" ];  then entry="$d/openclaw.mjs"
    else continue; fi
    best="$node	$entry"
  done
  [ -n "$best" ] || return 1
  printf '%s\n' "$best"
}

# Candidate 3: AlphaClaw repo pnpm install (NOT the ~/.alphaclaw stale one).
_cand_alphaclaw_repo() {
  local e="$OPENCLAW_TREE/AlphaClaw/node_modules/openclaw/openclaw.mjs"
  [ -e "$e" ] || return 1
  printf '%s\t%s\n' "$(command -v node)" "$e"
}

_resolve() {
  local pair node entry fn
  for fn in _cand_override _cand_gateway _cand_npm_global _cand_alphaclaw_repo; do
    pair="$($fn 2>/dev/null)" || continue
    node="${pair%%	*}"; entry="${pair#*	}"
    if _verify "$node" "$entry"; then
      printf '%s\t%s\n' "$node" "$entry"
      return 0
    fi
  done
  return 3
}

PAIR="$(_resolve)" || {
  echo "resolve-openclaw: no working OpenClaw install found (checked gateway, npm-global, AlphaClaw repo; stale ~/.alphaclaw excluded)" >&2
  exit 3
}
NODE="${PAIR%%	*}"; ENTRY="${PAIR#*	}"

if [ "${1:-}" = "--which" ]; then
  printf '%s\t%s\n' "$NODE" "$ENTRY"
  exit 0
fi

exec "$NODE" "$ENTRY" "$@"
