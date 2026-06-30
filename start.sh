#!/bin/bash
# start.sh — orama-system thin delegator  v1.1.0.0
#
# orama-system is Layer 3 — orchestration / meta-intelligence / delegate runtime.
# All gateway/backend/mode decisions are PT's responsibility (Perpetua-Tools).
# This script: macOS preflight → delegate to PT lifecycle → start orama services.
#
# Starts three services:
#   :8000  Perpetua-Tools orchestrator    (PT — Layer 2)
#   :8001  orama-system reasoning engine  (US)
#   :8002  Portal dashboard
#
# Usage:
#   ./start.sh             — start all, open browser
#   ./start.sh --no-open   — start all, skip browser
#   ./start.sh --stop      — kill all three services
#   ./start.sh --status    — show which ports are listening
#   ./start.sh --discover  — re-run path discovery, rewrite .paths, exit
#   ./start.sh --hardware-policy — validate model↔hardware affinity and exit
#   ./start.sh --lan-peer    — LAN-bind PT/orama/Portal + run peer probe after start
#   ./start.sh --install-coord-pulse — install the 15-minute Mac coord pulse
#   ./start.sh --coord-pulse-status  — show Mac coord pulse launchd status
#
# Path config: .paths (gitignored, auto-generated, user-editable)
# Template:    .paths.example

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATHS_FILE="$SCRIPT_DIR/.paths"
REPO_ROOT="$SCRIPT_DIR"

# Gitignored env (.env → .env.local) before gateway/profile reads ${env:...} config
if [ -f "$SCRIPT_DIR/scripts/env/load-local.sh" ]; then
  # shellcheck source=scripts/env/load-local.sh
  source "$SCRIPT_DIR/scripts/env/load-local.sh"
fi

# ── structured logging ─────────────────────────────────────────────────────────
# Levels: INFO (normal flow), WARN (non-fatal, needs attention), ERROR (fatal),
#         DEBUG (variable tracing — set ORAMA_DEBUG=1 to enable)
# Format: [HH:MM:SS] LEVEL  stage  message
#   stage = path|ip|pt|svc — makes grep-based debugging trivial:
#   e.g.  grep '\[ip\]' start.sh.log
#         grep 'WARN'    start.sh.log
_LOG_START="$(date +%s)"
_log() {
  local level="$1" stage="$2"; shift 2
  local ts; ts="$(date +%H:%M:%S)"
  local elapsed=$(( $(date +%s) - _LOG_START ))
  local msg="[${ts}] ${level}  [${stage}]  $*  (+${elapsed}s)"
  echo "$msg"
  # Append to session log for post-mortem analysis
  echo "$msg" >> "${SCRIPT_DIR}/.logs/startup-$(date +%Y%m%d).log" 2>/dev/null || true
}
_info()  { _log "INFO " "$@"; }
_warn()  { _log "WARN " "$@"; }
_err()   { _log "ERROR" "$@"; }
_debug() { [[ "${ORAMA_DEBUG:-0}" == "1" ]] && _log "DEBUG" "$@" || true; }
_var()   {
  # Trace a variable: _var stage VAR_NAME value [source]
  local stage="$1" name="$2" val="$3" src="${4:-}"
  local src_tag="${src:+  ← ${src}}"
  _debug "$stage" "${name}=${val}${src_tag}"
}

# ── argument parsing: match platform/windows/start.ps1 flag parity ────────────

NO_OPEN=0
STOP_ONLY=0
STATUS_ONLY=0
DISCOVER_ONLY=0
HARDWARE_POLICY_ONLY=0
INSTALL_NETWORK_WATCHER=0
INSTALL_COORD_PULSE=0
COORD_PULSE_STATUS=0
_LAN_PEER_MODE=0

_usage() {
  cat <<'USAGE'
Usage: ./start.sh [options]

Options:
  --no-open              Start services without opening the Portal browser.
  --stop                 Stop PT, orama, and Portal services.
  --status               Show service status and hardware policy.
  --discover             Re-run path discovery, rewrite .paths, and exit.
  --hardware-policy      Validate model/hardware affinity and exit.
  --lan-peer             LAN-bind services, probe the peer, and ensure Mac coord pulse.
  --profile=NAME         Activate an OpenClaw profile before startup.
  --with-mcp             Register/start the orama-swarm MCP endpoint.
  --no-mcp               Disable MCP registration for this run.
  --no-ollama            Skip Ollama auto-start and warm-up.
  --install-watcher      Install the macOS network-change watcher.
  --install-coord-pulse  Install the macOS 15-minute coord pulse and exit.
  --coord-pulse-status   Show coord pulse scheduler status and exit.
  --no-coord-pulse       Do not auto-install coord pulse during --lan-peer.
  --help                 Show this help.
USAGE
}

for _arg in "$@"; do
  case "$_arg" in
    --no-open)             NO_OPEN=1 ;;
    --stop)                STOP_ONLY=1 ;;
    --status)              STATUS_ONLY=1 ;;
    --discover)            DISCOVER_ONLY=1 ;;
    --hardware-policy)     HARDWARE_POLICY_ONLY=1 ;;
    --lan-peer)            _LAN_PEER_MODE=1 ;;
    --profile=*)           export OPENCLAW_PROFILE="${_arg#--profile=}" ;;
    --with-mcp)            export WITH_MCP=1 ;;
    --no-mcp)              export WITH_MCP=0 ;;
    --no-ollama)           export OLLAMA_AUTO_START=0 ;;
    --install-watcher)     INSTALL_NETWORK_WATCHER=1 ;;
    --install-coord-pulse) INSTALL_COORD_PULSE=1 ;;
    --coord-pulse-status)  COORD_PULSE_STATUS=1 ;;
    --no-coord-pulse)      export ORAMA_COORD_PULSE=0 ;;
    --help|-h)             _usage; exit 0 ;;
    *)
      _err "args" "unknown argument: $_arg"
      _usage
      exit 2
      ;;
  esac
done

# ── path resolution: .paths → git siblings → hardcoded sibling default ─────────

_discover_pt_dir() {
  local candidate var
  for var in PERPETUA_TOOLS_PATH PT_HOME PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT; do
    candidate="${!var:-}"
    if [ -n "$candidate" ] && [ -f "${candidate}/orchestrator/fastapi_app.py" ]; then
      echo "$candidate"; return
    fi
  done
  if [ -n "${OPENCLAW_HOME:-}" ]; then
    candidate="${OPENCLAW_HOME}/Perpetua-Tools"
    if [ -f "${candidate}/orchestrator/fastapi_app.py" ]; then
      echo "$candidate"; return
    fi
  fi
  candidate="$(cd "$SCRIPT_DIR/../perplexity-api/Perpetua-Tools" 2>/dev/null && pwd || true)"
  if [ -f "${candidate}/orchestrator/fastapi_app.py" ]; then
    echo "$candidate"; return
  fi
  local root
  root="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")"
  if [ -n "$root" ]; then
    local parent; parent="$(dirname "$root")"
    for d in "$parent"/*/; do
      if [ -f "${d}orchestrator/fastapi_app.py" ]; then
        cd "$d" && pwd; return
      fi
    done
  fi
  echo "$candidate"
}

_best_python() {
  local dir="$1"
  local venv_py="${dir}/.venv/bin/python"
  if [ -x "$venv_py" ]; then echo "$venv_py"
  else which python3 2>/dev/null || which python
  fi
}

# Load .paths if it exists
PT_DIR=""; PT_PYTHON=""; US_PYTHON=""
if [ -f "$PATHS_FILE" ]; then
  # shellcheck source=/dev/null
  source "$PATHS_FILE"
  _debug "path" "loaded .paths — PT_DIR=${PT_DIR}"
else
  _debug "path" ".paths not found — will discover"
fi

# Fill in any missing values via discovery
if [ -z "${PT_DIR:-}" ]; then
  PT_DIR="$(_discover_pt_dir)"
  _debug "path" "PT_DIR discovered=${PT_DIR}"
fi
if [ -z "${PT_PYTHON:-}" ]; then
  PT_PYTHON="$(_best_python "${PT_DIR:-$SCRIPT_DIR}")"
  _debug "path" "PT_PYTHON=${PT_PYTHON}"
fi
if [ -z "${US_PYTHON:-}" ]; then
  US_PYTHON="$(_best_python "$SCRIPT_DIR")"
  _debug "path" "US_PYTHON=${US_PYTHON}"
fi

if [ -z "${PT_DIR:-}" ] || [ ! -f "${PT_DIR}/orchestrator/alphaclaw_manager.py" ]; then
  _warn "path" "PT_DIR not found or missing alphaclaw_manager.py — PT resolve will be skipped"
else
  _info "path" "PT_DIR=${PT_DIR}"
fi

PT_PORT=${PT_PORT:-8000}
US_PORT=${US_PORT:-8001}
PORTAL_PORT=${PORTAL_PORT:-8002}

pid_on_port() {
  # Cross-platform: listeners only (ignore outbound/CLOSE_WAIT clients on the port)
  if command -v lsof &>/dev/null; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1 || true
  elif command -v ss &>/dev/null; then
    ss -tlnp "sport = :$1" 2>/dev/null | grep -oP 'pid=\K\d+' | head -1 || true
  elif command -v fuser &>/dev/null; then
    fuser "$1/tcp" 2>/dev/null | awk '{print $1}' | head -1 || true
  fi
}

run_hardware_policy_check() {
  local cli="${PT_DIR}/scripts/hardware_policy_cli.py"
  if [ -n "${PT_DIR:-}" ] && [ -f "$cli" ]; then
    echo ""
    echo "=== Hardware model affinity policy ==="
    PYTHONPATH="${PT_DIR}" "$PT_PYTHON" "$cli" --list || true
    echo ""
    PYTHONPATH="${PT_DIR}" "$PT_PYTHON" "$cli" --check-openclaw
  else
    _warn "policy" "hardware policy helper not found at ${cli:-unknown}"
    return 1
  fi
}

if [ "$HARDWARE_POLICY_ONLY" = "1" ]; then
  run_hardware_policy_check
  exit $?
fi

if [ "$STOP_ONLY" = "1" ]; then
  echo "Stopping orama-system services..."
  for port in $PT_PORT $US_PORT $PORTAL_PORT; do
    pid=$(pid_on_port "$port")
    if [ -n "$pid" ]; then
      kill "$pid" 2>/dev/null && echo "  killed PID $pid (:$port)" || true
    else
      echo "  nothing on :$port"
    fi
  done
  exit 0
fi

if [ "$STATUS_ONLY" = "1" ]; then
  echo "── service status ───────────────────────────────────────────────────"
  for entry in "PT:$PT_PORT" "orama:$US_PORT" "Portal:$PORTAL_PORT"; do
    label="${entry%%:*}"
    port="${entry#*:}"
    pid="$(pid_on_port "$port")"
    if [ -n "$pid" ]; then
      printf "  %-8s :%-5s  UP    (PID %s)\n" "$label" "$port" "$pid"
    else
      printf "  %-8s :%-5s  DOWN\n" "$label" "$port"
    fi
  done
  run_hardware_policy_check || true
  if [ "$(uname -s 2>/dev/null || echo Unknown)" = "Darwin" ] && [ -f "$SCRIPT_DIR/scripts/install_coord_pulse.sh" ]; then
    bash "$SCRIPT_DIR/scripts/install_coord_pulse.sh" --status || true
  fi
  echo ""
  exit 0
fi

if [ "$COORD_PULSE_STATUS" = "1" ]; then
  if [ -f "$SCRIPT_DIR/scripts/install_coord_pulse.sh" ]; then
    PERPETUA_TOOLS_ROOT="${PT_DIR:-}" PERPETUA_TOOLS_PATH="${PT_DIR:-}" \
      bash "$SCRIPT_DIR/scripts/install_coord_pulse.sh" --status
  else
    _warn "coord-pulse" "installer missing: $SCRIPT_DIR/scripts/install_coord_pulse.sh"
    exit 1
  fi
  exit $?
fi

if [ "$INSTALL_COORD_PULSE" = "1" ]; then
  if [ "$(uname -s 2>/dev/null || echo Unknown)" != "Darwin" ]; then
    _warn "coord-pulse" "launchd coord pulse is macOS-only; Linux can run coord_pulse.sh from cron"
    exit 1
  fi
  if [ ! -f "$SCRIPT_DIR/scripts/install_coord_pulse.sh" ]; then
    _warn "coord-pulse" "installer missing: $SCRIPT_DIR/scripts/install_coord_pulse.sh"
    exit 1
  fi
  PERPETUA_TOOLS_ROOT="${PT_DIR:-}" PERPETUA_TOOLS_PATH="${PT_DIR:-}" \
    COORD_PULSE_INTERVAL_SEC="${COORD_PULSE_INTERVAL_SEC:-900}" \
    bash "$SCRIPT_DIR/scripts/install_coord_pulse.sh"
  exit $?
fi

# ── Symlink Validation (from 1675ab4 — auto-repair PT sibling symlinks) ──────
# Ensures network_autoconfig.py and lib/shared/agentic_stack are wired to live
# PT paths. Uses relative path calculation so symlinks survive directory moves.
_ensure_symlink() {
  # Usage: _ensure_symlink <link-path> <target-path>
  # Idempotent: safe to call on every startup.
  # Runs with the caller's cwd — callers must cd to the intended directory first.
  # Five-state guard (extends 4-state with stale-target detection):
  #   1. Valid symlink pointing at target       → no-op
  #   2. Valid symlink pointing at wrong target → relink (PT_DIR moved)
  #   3. Broken symlink (dangling)              → repair if target exists
  #   4. Regular file/dir occupies link path   → warn + skip (preserve user data)
  #   5. Nothing at link path                  → create
  local link="$1" target="$2"
  if [ -L "$link" ] && [ -e "$link" ]; then
    # Valid symlink — check if it already points at the right target.
    local current_target
    current_target="$(readlink "$link")"
    if [ "$current_target" = "$target" ]; then
      return 0   # already correct — true no-op
    fi
    # PT_DIR moved or target changed — relink to new location.
    _info "link" "retargeting symlink: $link ($current_target → $target)"
    rm "$link"
    ln -s "$target" "$link"
    return 0
  elif [ -L "$link" ] && [ ! -e "$link" ]; then
    # Broken symlink — attempt re-link.
    _warn "link" "broken symlink: $link — attempting re-link to $target"
    if [ -e "$target" ]; then
      rm "$link"
      ln -s "$target" "$link"
      _info "link" "re-linked: $link → $target"
    else
      _warn "link" "re-link skipped: target $target does not exist"
    fi
  elif [ -e "$link" ]; then
    # Regular file or directory occupies the link path — do not overwrite.
    # The tracked file takes precedence; symlink creation is skipped silently.
    _warn "link" "skipping symlink $link: path exists as a regular file/dir (manual migration needed if PT override is desired)"
  else
    # Nothing at link path — create the symlink.
    _info "link" "creating symlink: $link → $target"
    ln -s "$target" "$link"
  fi
}

if [ -n "${PT_DIR:-}" ]; then
  # network_autoconfig.py — Python module for LAN IP detection
  _PT_NET_CONFIG="${PT_DIR}/packages/net_utils/network_autoconfig.py"
  if [ -f "$_PT_NET_CONFIG" ]; then
    _REL_NET_CONFIG="$(_PYLINK_SRC="$_PT_NET_CONFIG" _PYLINK_BASE="$SCRIPT_DIR" \
      python3 -c "import os; print(os.path.relpath(os.environ['_PYLINK_SRC'],os.environ['_PYLINK_BASE']))" 2>/dev/null || true)"
    [ -n "$_REL_NET_CONFIG" ] && (cd "$SCRIPT_DIR" && _ensure_symlink "scripts/network_autoconfig.py" "$_REL_NET_CONFIG")
  fi

  # lib/shared/agentic_stack — shared library from PT
  _PT_STACK="${PT_DIR}/vendor/agentic-stack"
  if [ -d "$_PT_STACK" ]; then
    mkdir -p "$SCRIPT_DIR/lib/shared"
    _REL_STACK="$(_PYLINK_SRC="$_PT_STACK" _PYLINK_BASE="$SCRIPT_DIR/lib/shared" \
      python3 -c "import os; print(os.path.relpath(os.environ['_PYLINK_SRC'],os.environ['_PYLINK_BASE']))" 2>/dev/null || true)"
    if [ -n "$_REL_STACK" ]; then
      (cd "$SCRIPT_DIR/lib/shared" && _ensure_symlink "agentic_stack" "$_REL_STACK")
    fi
  fi
fi

# Write .paths on first run (or if --discover requested)
if [ ! -f "$PATHS_FILE" ] || [ "$DISCOVER_ONLY" = "1" ]; then
  cat > "$PATHS_FILE" << PATHSEOF
# .paths — auto-generated by ./start.sh on $(date '+%Y-%m-%d %H:%M:%S')
# Edit to override. See .paths.example for documentation.
# Regenerate: rm .paths && ./start.sh

PT_DIR="${PT_DIR}"
PT_PYTHON="${PT_PYTHON}"
US_PYTHON="${US_PYTHON}"
PATHSEOF
  echo "  Paths written to .paths (gitignored)"
  [ "$DISCOVER_ONLY" = "1" ] && exit 0
fi

# ── --lan-peer (enable LAN bind before host resolution) ───────────────────────
if [ "$_LAN_PEER_MODE" = "1" ]; then
  export PT_BIND_LAN="${PT_BIND_LAN:-1}"
  export ORAMA_BIND_LAN="${ORAMA_BIND_LAN:-1}"
  export PORTAL_BIND_LAN="${PORTAL_BIND_LAN:-1}"
  _info "lan-peer" "LAN bind enabled (PT/ORAMA/PORTAL) — peer HTTP on this host"
fi

PT_PORT=${PT_PORT:-8000}
US_PORT=${US_PORT:-8001}
PORTAL_PORT=${PORTAL_PORT:-8002}
PORTAL_URL="http://localhost:${PORTAL_PORT}"

_orama_all_interfaces_host() {
  python3 -c 'import os; print(os.getenv("ORAMA_LAN_BIND_HOST") or ".".join(["0"]*4))'
}

_resolve_bind_host() {
  local lan_flag="$1" host_var="$2"
  local lan_val="${!lan_flag:-}"
  if [ "$lan_val" = "1" ] || [ "$lan_val" = "true" ] || [ "$lan_val" = "yes" ]; then
    _orama_all_interfaces_host
    return
  fi
  local host_val="${!host_var:-localhost}"
  echo "${host_val:-localhost}"
}

PT_HOST="$(_resolve_bind_host PT_BIND_LAN PT_HOST)"
ORAMASYS_HOST="${ORAMASYS_HOST:-${ULTRATHINK_HOST:-}}"
US_HOST="$(_resolve_bind_host ORAMA_BIND_LAN ORAMASYS_HOST)"
PORTAL_HOST="$(_resolve_bind_host PORTAL_BIND_LAN PORTAL_HOST)"
export PT_HOST US_HOST PORTAL_HOST

# Portal and orama HTTP clients read PT's auto-generated bearer from this path.
if [ -n "${PT_DIR:-}" ]; then
  export PERPETUA_TOOLS_ROOT="${PT_DIR}"
fi

_sync_control_plane_token() {
  if [ -n "${ORAMA_CONTROL_PLANE_TOKEN:-}" ]; then
    return 0
  fi
  local token_file="${PT_DIR:-}/.state/control_plane_token"
  if [ -f "$token_file" ]; then
    ORAMA_CONTROL_PLANE_TOKEN="$(tr -d '[:space:]' < "$token_file")"
    export ORAMA_CONTROL_PLANE_TOKEN
    _info "lan-peer" "ORAMA_CONTROL_PLANE_TOKEN loaded from PT .state/control_plane_token"
  else
    _warn "lan-peer" "No ORAMA_CONTROL_PLANE_TOKEN — portal-status probe will SKIP (set in .env.local)"
  fi
}

_require_control_plane_token_for_lan() {
  case "${ORAMA_INSECURE_DEV:-}" in 1|true|yes|TRUE|YES) return 0 ;; esac
  _sync_control_plane_token
  local token="${ORAMA_CONTROL_PLANE_TOKEN:-}"
  local py="${US_PYTHON:-}"
  if [ -z "$py" ]; then
    py="$(command -v python3 2>/dev/null || true)"
  fi
  if [ -n "$token" ] && [ -d "$SCRIPT_DIR/src" ] && [ -n "$py" ]; then
    if PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
      ORAMA_CONTROL_PLANE_TOKEN="$token" \
      "$py" -c 'from utils.control_plane_auth import is_weak_control_plane_token; import os, sys; sys.exit(0 if not is_weak_control_plane_token(os.environ["ORAMA_CONTROL_PLANE_TOKEN"]) else 1)' 2>/dev/null; then
      return 0
    fi
  fi
  if [ -n "$py" ] && [ -d "$SCRIPT_DIR/src" ]; then
    token="$(
      PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
        "$py" -c 'from utils.control_plane_auth import ensure_control_plane_token; print(ensure_control_plane_token())' 2>/dev/null \
        || true
    )"
    if [ -n "$token" ]; then
      export ORAMA_CONTROL_PLANE_TOKEN="$token"
      _info "lan-peer" "generated control-plane token for LAN bind"
      return 0
    fi
  fi
  _err "LAN bind requires a strong ORAMA_CONTROL_PLANE_TOKEN (set in .env.local or allow auto-generation via PT/orama startup)"
  return 1
}

if [ "${PT_BIND_LAN:-0}" = "1" ] || [ "${ORAMA_BIND_LAN:-0}" = "1" ] || [ "${PORTAL_BIND_LAN:-0}" = "1" ]; then
  _warn "svc" "LAN bind enabled (PT_BIND_LAN/ORAMA_BIND_LAN/PORTAL_BIND_LAN) — control-plane APIs are reachable on the network"
  _require_control_plane_token_for_lan || exit 1
fi

_run_lan_peer_probe() {
  local probe="$SCRIPT_DIR/bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py"
  if [ ! -f "$probe" ]; then
    _warn "lan-peer" "probe script missing: $probe"
    return 1
  fi
  _info "lan-peer" "running probe_lan_peer.py --json ..."
  _sync_control_plane_token
  PERPETUA_TOOLS_ROOT="${PT_DIR:-}" ORAMA_CONTROL_PLANE_TOKEN="${ORAMA_CONTROL_PLANE_TOKEN:-}" \
    "$US_PYTHON" "$probe" --json || {
    _warn "lan-peer" "peer probe reported failures (Win peer may need PORTAL_BIND_LAN=1 + restart)"
    return 1
  }
}

_flush_lan_peer_outbox() {
  local assign="$SCRIPT_DIR/bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py"
  if [ ! -f "$assign" ]; then
    _warn "lan-peer" "assignment script missing: $assign"
    return 1
  fi
  _info "lan-peer" "flushing queued peer drops..."
  _sync_control_plane_token
  PERPETUA_TOOLS_ROOT="${PT_DIR:-}" ORAMA_CONTROL_PLANE_TOKEN="${ORAMA_CONTROL_PLANE_TOKEN:-}" \
    "$US_PYTHON" "$assign" flush-outbox --peer || {
    _warn "lan-peer" "queued peer drops remain pending"
    return 1
  }
}

_run_discover_force_with_timeout() {
  local seconds="$1"
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$US_PYTHON" "$_DISCOVER_SCRIPT" --force
    return $?
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$seconds" "$US_PYTHON" "$_DISCOVER_SCRIPT" --force
    return $?
  fi
  python3 - "$seconds" "$US_PYTHON" "$_DISCOVER_SCRIPT" <<'PY'
import subprocess
import sys

seconds = float(sys.argv[1])
cmd = [sys.argv[2], sys.argv[3], "--force"]
try:
    raise SystemExit(subprocess.run(cmd, timeout=seconds).returncode)
except subprocess.TimeoutExpired:
    raise SystemExit(124)
PY
}

LOG_DIR="$SCRIPT_DIR/.logs"
mkdir -p "$LOG_DIR"

# ── hard requirements probe (fail closed on Ollama + models) ─────────────────
# Runs before any service logic. Idempotent — fast when already satisfied.
# Stamps .requirements.stamp so repeat runs skip pip install unless deps change.
# Flags: ORAMA_SKIP_ENSURE=1 to bypass (CI / headless envs with pre-installed deps).
if [[ "${ORAMA_SKIP_ENSURE:-0}" != "1" ]] && [ -f "$SCRIPT_DIR/scripts/ensure_requirements.sh" ]; then
  _info "ensure" "probing hard requirements..."
  if ! bash "$SCRIPT_DIR/scripts/ensure_requirements.sh" --quiet \
       2>&1 | tee -a "$LOG_DIR/startup-$(date +%Y%m%d).log" | sed 's/^/  [ensure] /'; then
    _err "ensure" "Hard requirements not satisfied — cannot start. See output above."
    exit 1
  fi

  # Also run PT ensure_requirements if PT_DIR is resolved
  if [ -n "${PT_DIR:-}" ] && [ -f "${PT_DIR}/scripts/ensure_requirements.sh" ]; then
    _info "ensure" "probing PT (Perpetua-Tools) requirements..."
    bash "${PT_DIR}/scripts/ensure_requirements.sh" --quiet \
      2>&1 | tee -a "$LOG_DIR/startup-$(date +%Y%m%d).log" | sed 's/^/  [pt-ensure] /' || true
  fi
fi

# ── macOS pre-flight ──────────────────────────────────────────────────────────
# Applies idempotent fixes to the AlphaClaw binary (macOS compat patches).
# Non-fatal — startup continues on any error.
# Guard: skip entirely on non-macOS (Linux / CI).
_OS_NAME="$(uname -s 2>/dev/null || echo Unknown)"
if [ "$_OS_NAME" = "Darwin" ] && [ -f "$SCRIPT_DIR/scripts/setup_macos.py" ]; then
  "$US_PYTHON" "$SCRIPT_DIR/scripts/setup_macos.py" --quiet 2>&1 | sed 's/^/  /' || true
elif [ "$_OS_NAME" != "Darwin" ]; then
  _info "svc" "Non-macOS host (${_OS_NAME}) — skipping scripts/setup_macos.py"
fi

# ── Codex PATH fix (idempotent) ───────────────────────────────────────────────
# Ensures ~/.local/bin/codex → /opt/homebrew/bin/codex so Codex is always
# callable regardless of which nvm version is active in this shell session.
if [ -f "$SCRIPT_DIR/scripts/setup_codex.sh" ]; then
  bash "$SCRIPT_DIR/scripts/setup_codex.sh" 2>&1 | sed 's/^/  [codex] /' || true
fi

# ── Hardware policy cache refresh (L2 disaster recovery) ─────────────────────
# Refreshes config/hardware_policy_cache.yml from PT's authoritative source.
# Non-fatal — if PT is absent the existing cache (L2) remains valid.
if [ -f "$SCRIPT_DIR/scripts/refresh_policy_cache.py" ]; then
  "$US_PYTHON" "$SCRIPT_DIR/scripts/refresh_policy_cache.py" 2>&1 | sed 's/^/  [policy] /' || true
fi

# ── openclaw-skills submodule init (idempotent) ──────────────────────────────
# Ensures cc-openclaw submodule is initialized on fresh clones and CI.
if [ -f "$SCRIPT_DIR/scripts/install-openclaw-skills.sh" ]; then
  bash "$SCRIPT_DIR/scripts/install-openclaw-skills.sh" 2>&1 | sed 's/^/  [openclaw] /' || true
fi

# ── global Claude skills refresh (copy + auto-resync, idempotent) ────────────
# Keeps ~/.claude/skills current with the repo's canonical skills every start.
if [ -f "$SCRIPT_DIR/scripts/install-skills.sh" ]; then
  bash "$SCRIPT_DIR/scripts/install-skills.sh" 2>&1 | sed 's/^/  [skills] /' || true
fi

# ── gbrain self-heal (idempotent; backgrounded so it NEVER blocks startup) ───
# Acks transient failures, refreshes live sources, reports orphan sources /
# autopilot misconfig. Replaces the recurring manual gbrain fixes.
# Details + why: bin/orama-system/gstack/SKILL.md §GBrain Ops §7.
if [ -f "$SCRIPT_DIR/scripts/gbrain/gbrain-selfheal.sh" ]; then
  ( nohup bash "$SCRIPT_DIR/scripts/gbrain/gbrain-selfheal.sh" \
      >>"${LOG_DIR:-/tmp}/gbrain-selfheal.log" 2>&1 & ) || true
fi

# ── environment bootstrap (idempotent) — reproduce the cross-cutting fixes ───
# Write-time path-hygiene hook, PERPETUA_TOOLS_ROOT, ollama keep-alive, gateway
# orchestrator=ollama routing, .claude/skills thin-wrapper consolidation. Safe to
# run every start; a fresh clone gets all of these with no manual steps.
if [ -f "$SCRIPT_DIR/scripts/bootstrap-environment.sh" ]; then
  bash "$SCRIPT_DIR/scripts/bootstrap-environment.sh" 2>&1 | sed 's/^/  [bootstrap] /' || true
fi

# ── LAN live probe — always run on startup (LAN is dynamic) ──────────────────
# LAN topology changes: DHCP leases expire, machines reboot, IPs shift.
# We ALWAYS run discover.py --force before reading any IP so the IP detection
# block below always reads fresh data, not a cache that might be days old.
#
# discover.py --force:
#   • Probes localhost:1234 for Mac LM Studio (fast, always local)
#   • Async-scans entire subnet (0.2s timeout per host, all 254 in parallel)
#   • Writes updated IPs to ~/.openclaw/openclaw.json and state/discovery.json
#   • Patches Perpetua-Tools config/ YAML files
#   • Total time: ~0.5s if Win offline, ~4-5s if Win online (model fetch)
_DISCOVER_SCRIPT="$HOME/.openclaw/scripts/discover.py"
if [ -f "$_DISCOVER_SCRIPT" ]; then
  _info "ip" "probing LAN topology (discover.py --force)..."
  if _run_discover_force_with_timeout 30 \
       2>&1 | tee -a "$LOG_DIR/startup-$(date +%Y%m%d).log" | sed 's/^/  [discover] /'; then
    _info "ip" "LAN probe complete — openclaw.json is up to date"
  else
    _exit=$?
    if [ "$_exit" -eq 124 ]; then
      _warn "ip" "discover.py timed out (>30s, macOS ICMP limit?) — falling back to cached/static IPs"
    else
      _warn "ip" "discover.py --force exited ${_exit} — falling back to cached/static IPs"
    fi
  fi
else
  _warn "ip" "discover.py not found at $_DISCOVER_SCRIPT — skipping live LAN probe"
fi

# ── IP auto-detection (priority-based, reads fresh discover.py output above) ──
#
# Priority chain — first success wins:
#   1. ~/.openclaw/openclaw.json   (discover.py just patched it above)
#   2. discover.py --status        (reads state written by the --force run above)
#   3. network_autoconfig netifaces (dynamic interface detection — no prior state)
#   4. Subnet .103 constant        (subnet-portable: works on any /24, never a fixed IP)
#
# Old stale IPs are archived here only — NEVER used as source:
#   Windows was: .108 → .100 → .101 — all stale, replaced by dynamic detection

_IP_VARS="$("$US_PYTHON" -c "
import json, re, subprocess, sys
from pathlib import Path

MAC_IP = 'localhost'   # Mac always probes itself via localhost
WIN_IP = ''
source  = 'unknown'

# ── Priority 1: ~/.openclaw/openclaw.json ─────────────────────────────────────
# discover.py patches this file on every successful scan — authoritative.
try:
    cfg = json.loads(Path.home().joinpath('.openclaw/openclaw.json').read_text())
    url = cfg['models']['providers']['lmstudio-win']['baseUrl']
    WIN_IP = url.split('//')[-1].split(':')[0]
    source = 'openclaw.json'
except Exception:
    pass

# ── Priority 2: discover.py --status ─────────────────────────────────────────
# Reads cached discovery state (~/.openclaw/state/discovery.json). Fast, no probe.
if not WIN_IP:
    try:
        out = subprocess.check_output(
            [sys.executable, str(Path.home() / '.openclaw/scripts/discover.py'), '--status'],
            stderr=subprocess.DEVNULL, timeout=8
        ).decode()
        m = re.search(r'win:.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', out)
        if m:
            WIN_IP = m.group(1)
            source = 'discover.py'
    except Exception:
        pass

# ── Priority 3: network_autoconfig dynamic netifaces scan ────────────────────
# Uses OS network interface list — reflects current topology without prior state.
if not WIN_IP:
    try:
        sys.path.insert(0, '$SCRIPT_DIR/scripts')
        from network_autoconfig import NetworkAutoConfig
        cfg2 = NetworkAutoConfig()
        WIN_IP = cfg2.preferred_ips.get('Windows', '')
        source = 'network_autoconfig'
    except Exception:
        pass

# ── Priority 4: subnet.104 constant (subnet-portable, not a fixed IP) ────────
# Derives Win IP from Mac's own outbound interface subnet.
# If Mac is on 192.168.1.x → Win = 192.168.1.104 (works on any /24 without change).
# This is ONLY reached if discover.py failed AND openclaw.json is unreadable.
if not WIN_IP:
    try:
        import socket as _s
        with _s.socket(_s.AF_INET, _s.SOCK_DGRAM) as _sk:
            _sk.connect(('8.8.8.8', 80))
            _local = _sk.getsockname()[0]
        WIN_IP = '.'.join(_local.split('.')[:3]) + '.104'
        source = 'subnet.104'
    except Exception:
        WIN_IP = '192.168.254.104'   # absolute last resort — static /24 constant
        source = 'hardcoded-constant'

print(f'MAC_IP={MAC_IP}')
print(f'WIN_IP={WIN_IP}')
print(f'IP_SOURCE={source}')
" 2>/dev/null)"

eval "$_IP_VARS"
MAC_IP="${MAC_IP:-localhost}"
WIN_IP="${WIN_IP:-192.168.254.104}"
IP_SOURCE="${IP_SOURCE:-last-resort-constant}"

_info  "ip" "MAC_IP=${MAC_IP}  WIN_IP=${WIN_IP}  source=${IP_SOURCE}"
if [[ "$IP_SOURCE" == "last-resort-constant" ]]; then
  _warn "ip" "IP detection fell through to last-resort constant — run 'discover.py --force' if Win is unreachable"
fi
_var   "ip" "MAC_IP" "$MAC_IP" "$IP_SOURCE"
_var   "ip" "WIN_IP" "$WIN_IP" "$IP_SOURCE"

# ── PT resolve — backend probe + AlphaClaw bootstrap ─────────────────────────
# Delegates ALL gateway decisions to Perpetua-Tools (Layer 2).
# PT probes backends, determines mode, bootstraps AlphaClaw, and returns
# a JSON payload. orama reads that payload — it makes zero gateway decisions.
#
# PT owns: backend probe (was start.sh §2a), AlphaClaw bootstrap (§2b),
#          mode determination (was §2c).
# See: orchestrator/alphaclaw_manager.py
PT_RESOLVE_OK=0
PT_MODE="offline"
PT_DISTRIBUTED="no"
PT_ALPHACLAW_PORT=""

if [ -n "${PT_DIR:-}" ] && [ -f "${PT_DIR}/orchestrator/alphaclaw_manager.py" ]; then
  _info "pt" "resolving runtime — passing MAC_IP=${MAC_IP} WIN_IP=${WIN_IP}"
  _PT_ENV_EXPORTS="$(
    MAC_IP="${MAC_IP}" WIN_IP="${WIN_IP}" \
    PYTHONPATH="${PT_DIR}/src:${PT_DIR}" \
    "$PT_PYTHON" -m orchestrator.alphaclaw_manager \
      --resolve --env-only \
      --mac-ip "${MAC_IP}" --win-ip "${WIN_IP}" \
      2>&1 | tee /dev/stderr | grep '^export '
  )" && PT_RESOLVE_OK=1 || true

  if [ "$PT_RESOLVE_OK" -eq 1 ] && [ -n "$_PT_ENV_EXPORTS" ]; then
    eval "$_PT_ENV_EXPORTS"
    PT_MODE="${PT_MODE:-offline}"
    PT_DISTRIBUTED="${PT_DISTRIBUTED:-no}"
    PT_ALPHACLAW_PORT="${PT_ALPHACLAW_PORT:-}"
    export PT_AGENTS_STATE="${PT_DIR}/.state/routing.json"
    _info "pt" "resolved — mode=${PT_MODE}  distributed=${PT_DISTRIBUTED}  alphaclaw_port=${PT_ALPHACLAW_PORT}"
    _var  "pt" "PT_MODE"          "$PT_MODE"          "alphaclaw_manager"
    _var  "pt" "PT_DISTRIBUTED"   "$PT_DISTRIBUTED"   "alphaclaw_manager"
    _var  "pt" "PT_ALPHACLAW_PORT" "$PT_ALPHACLAW_PORT" "alphaclaw_manager"
    _var  "pt" "PT_AGENTS_STATE"  "$PT_AGENTS_STATE"  "derived"
  else
    # ── Warm-cache fallback ────────────────────────────────────────────────
    # PT resolve failed (Python unavailable, network timeout, etc.).
    # Read the last known good routing.json and re-export its values so
    # downstream services don't start completely blind.
    _warn "pt" "resolve non-fatal (exit=${PT_RESOLVE_OK}) — trying warm cache"
    _PT_CACHE="${PT_DIR}/.state/routing.json"
    if [ -f "$_PT_CACHE" ] && command -v python3 >/dev/null 2>&1; then
      _PT_CACHED_EXPORTS="$(
        python3 - "$_PT_CACHE" 2>/dev/null <<'PYEOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    for k, v in {
        "PT_MODE":          d.get("mode",          "cached"),
        "PT_DISTRIBUTED":   str(d.get("distributed", False)).lower(),
        "PT_ALPHACLAW_PORT": str(d.get("alphaclaw_port", "")),
        "WIN_IP":           d.get("win_ip", ""),
        "PT_SCENARIO":      d.get("scenario_name", "FULLY_OFFLINE"),
    }.items():
        if v:
            print(f"export {k}={v!r}")
    print("export PT_MODE_SOURCE=cache")
except Exception:
    pass
PYEOF
      )" || true
      if [ -n "$_PT_CACHED_EXPORTS" ]; then
        eval "$_PT_CACHED_EXPORTS"
        PT_MODE="${PT_MODE:-cached}"
        export PT_AGENTS_STATE="$_PT_CACHE"
        _warn "pt" "warm cache loaded — mode=${PT_MODE}  scenario=${PT_SCENARIO:-unknown}  (stale data — probe will retry next start)"
        _var  "pt" "PT_MODE"      "$PT_MODE"      "warm-cache"
        _var  "pt" "PT_SCENARIO"  "${PT_SCENARIO:-unknown}" "warm-cache"
      else
        _warn "pt" "warm cache unreadable — continuing with offline defaults"
      fi
    else
      _warn "pt" "no warm cache at ${_PT_CACHE} — continuing with offline defaults"
    fi
  fi
else
  # Fallback: PT manager not available — delegate to bootstrap script directly
  PT_HOME="${PT_HOME:-$HOME/Perpetua-Tools}"
  ALPHACLAW_SCRIPT="$PT_HOME/src/perpetua_tools/alphaclaw_bootstrap.py"
  if [ -f "$ALPHACLAW_SCRIPT" ]; then
    _warn "pt" "alphaclaw_manager.py not found — using fallback bootstrap module perpetua_tools.alphaclaw_bootstrap"
    PT_HOME="$PT_HOME" UTS_HOME="$SCRIPT_DIR" \
      MAC_IP="${MAC_IP}" WIN_IP="${WIN_IP}" PYTHONPATH="$PT_HOME/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$US_PYTHON" -m perpetua_tools.alphaclaw_bootstrap --bootstrap \
      </dev/null 2>&1 | sed 's/^/  /' \
      || _warn "pt" "fallback bootstrap non-fatal — continuing without gateway"
  else
    _warn "pt" "PT not found at ${PT_DIR:-$PT_HOME} — skipping AlphaClaw bootstrap entirely"
  fi
fi

# Export env vars all services read (with user overrides respected)
# _var traces show exactly what value each service will receive
export OLLAMA_MAC_ENDPOINT="${OLLAMA_MAC_ENDPOINT:-http://localhost:11434}"
export OLLAMA_WINDOWS_ENDPOINT="${OLLAMA_WINDOWS_ENDPOINT:-http://${WIN_IP}:11434}"
export LM_STUDIO_MAC_ENDPOINT="${LM_STUDIO_MAC_ENDPOINT:-http://localhost:1234}"
export LM_STUDIO_WIN_ENDPOINTS="${LM_STUDIO_WIN_ENDPOINTS:-http://${WIN_IP}:1234}"
export WINDOWS_IP="${WINDOWS_IP:-${WIN_IP}}"
export GPU_BOX="${GPU_BOX:-WINUSER@${WIN_IP}}"
# WIN_LM_STUDIO_HOST — consumed by api_server.py to enable Windows LM Studio provider
export WIN_LM_STUDIO_HOST="${WIN_LM_STUDIO_HOST:-${WIN_IP}}"

_info "env" "endpoints exported to child processes"
_var  "env" "OLLAMA_MAC_ENDPOINT"    "$OLLAMA_MAC_ENDPOINT"    "derived"
_var  "env" "OLLAMA_WINDOWS_ENDPOINT" "$OLLAMA_WINDOWS_ENDPOINT" "derived"
_var  "env" "LM_STUDIO_MAC_ENDPOINT" "$LM_STUDIO_MAC_ENDPOINT" "derived"
_var  "env" "LM_STUDIO_WIN_ENDPOINTS" "$LM_STUDIO_WIN_ENDPOINTS" "derived"
_var  "env" "WINDOWS_IP"             "$WINDOWS_IP"             "derived"

# AlphaClaw security warning — show if running on default password
_AC_PT_HOME="${PT_DIR:-${PT_HOME:-$HOME/Perpetua-Tools}}"
_AC_ONBOARDING="${_AC_PT_HOME}/.state/onboarding.json"
if [ -f "$_AC_ONBOARDING" ]; then
  if "$US_PYTHON" -c "
import json, sys, pathlib
f = pathlib.Path('${_AC_ONBOARDING}')
d = json.loads(f.read_text(encoding='utf-8'))
sys.exit(0 if d.get('alphaclaw', {}).get('password_is_default') else 1)
" 2>/dev/null; then
    echo ""
    echo "  ┌────────────────────────────────────────────────────────────────┐"
    echo "  │  SECURITY  AlphaClaw is running on the DEFAULT password         │"
    echo "  │  Set SETUP_PASSWORD=<yourpassword> in .env and restart          │"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""
  fi
fi

# ── helpers ───────────────────────────────────────────────────────────────────

_port_open() {
  # Cross-platform TCP probe: nc → /dev/tcp bash built-in
  local port=$1
  if command -v nc &>/dev/null; then
    nc -z localhost "$port" 2>/dev/null
  else
    # bash /dev/tcp built-in (works without nc on most Linux)
    (echo >/dev/tcp/localhost/"$port") 2>/dev/null
  fi
}

wait_for_port() {
  local port=$1 label=$2 tries=0
  printf "  waiting for %s (:%s)" "$label" "$port"
  while ! _port_open "$port"; do
    sleep 0.5; tries=$((tries+1))
    printf "."
    if [ $((tries % 60)) -eq 0 ] && [ $tries -gt 0 ]; then
      local elapsed=$((tries / 2))
      local logfile="$LOG_DIR/$(printf '%s' "$label" | tr '[:upper:]' '[:lower:]').log"
      printf "\n  ⚠  %s (:%s) unresponsive for %ds\n" "$label" "$port" "$elapsed"
      if [ -f "$logfile" ]; then
        echo "  last 5 lines of ${logfile}:"
        tail -5 "$logfile" | sed 's/^/    /'
      fi
      printf "  still waiting for %s (:%s)" "$label" "$port"
    fi
    if [ $tries -ge 150 ]; then
      local logfile="$LOG_DIR/$(printf '%s' "$label" | tr '[:upper:]' '[:lower:]').log"
      printf " TIMEOUT — check %s\n" "$logfile"
      return 0  # non-fatal: continue starting remaining services
    fi
  done
  echo " UP"
}

open_browser() {
  local url=$1
  if command -v open &>/dev/null; then open "$url"
  elif command -v xdg-open &>/dev/null; then xdg-open "$url"
  fi
}

# ── ollama idempotent startup ─────────────────────────────────────────────────
# Ensures ollama server is running and the Mac Orchestrator model is warm.
# Non-fatal — failures are logged and execution continues.
# Env knobs: OLLAMA_AUTO_START=0 to skip; OLLAMA_WARM_MODEL to override model.

_ollama_ensure_ready() {
  [ "${OLLAMA_AUTO_START:-1}" != "1" ] && return 0

  local model="${OLLAMA_WARM_MODEL:-qwen3.5:9b-nvfp4}"
  local endpoint="${OLLAMA_MAC_ENDPOINT:-http://localhost:11434}"

  # 1. Server check / start
  if ! curl -sf "${endpoint}/api/version" >/dev/null 2>&1; then
    _info "ollama" "server not running — starting ollama serve..."
    mkdir -p "${LOG_DIR}"
    nohup ollama serve >>"${LOG_DIR}/ollama.log" 2>&1 &
    local i=0
    while [ $i -lt 12 ]; do
      sleep 1; i=$((i+1))
      curl -sf "${endpoint}/api/version" >/dev/null 2>&1 && break
    done
    if curl -sf "${endpoint}/api/version" >/dev/null 2>&1; then
      _info "ollama" "server ready at ${endpoint}"
    else
      _warn "ollama" "server did not start in 12s — see ${LOG_DIR}/ollama.log"
      return 0
    fi
  else
    _info "ollama" "server already running at ${endpoint}"
  fi

  # 2. Model availability check / pull
  if ! ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -qxF "${model}"; then
    _info "ollama" "model ${model} not installed — pulling..."
    ollama pull "${model}" >>"${LOG_DIR}/ollama.log" 2>&1 || {
      _warn "ollama" "pull failed — continuing without model warm-up"
      return 0
    }
  fi

  # 3. Warm model into GPU memory with indefinite keep-alive (non-blocking)
  local already_loaded
  already_loaded=$(curl -sf "${endpoint}/api/ps" 2>/dev/null | \
    MODEL_NAME="$model" python3 -c "
import sys,json
ps=json.load(sys.stdin)
names=[m.get('name','') for m in ps.get('models',[])]
model = __import__('os').environ['MODEL_NAME']
base = model.split(':', 1)[0]
print('yes' if any(n == model or n.startswith(base + ':') for n in names) else 'no')
" 2>/dev/null || echo "no")

  if [ "$already_loaded" = "yes" ]; then
    _info "ollama" "model ${model} already loaded in memory"
  else
    _info "ollama" "warming ${model} into GPU memory (keep_alive=-1)..."
    curl -sf -X POST "${endpoint}/api/generate" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"${model}\",\"keep_alive\":-1}" \
      >/dev/null 2>&1 &
    _info "ollama" "warm-up dispatched (non-blocking)"
  fi
}

# ── per-profile openclaw config ───────────────────────────────────────────────
# Usage:  OPENCLAW_PROFILE=mac-orchestrator ./start.sh
#         ./start.sh --profile=mac-orchestrator
#
# Config search order:
#   ~/.openclaw/openclaw-{profile}.json   (user-level overrides)
#   {SCRIPT_DIR}/config/{profile}.json    (repo-committed defaults)
#
# Activates by symlinking ~/.openclaw/openclaw.json → selected profile.
# Original is backed up as openclaw.json.pre-{profile} on first switch.

_openclaw_select_profile() {
  local profile="${OPENCLAW_PROFILE:-}"
  [ -z "$profile" ] && return 0

  local candidates=(
    "${HOME}/.openclaw/openclaw-${profile}.json"
    "${SCRIPT_DIR}/config/openclaw-${profile}.json"
    "${SCRIPT_DIR}/config/${profile}.json"
  )
  local config_file=""
  for c in "${candidates[@]}"; do
    [ -f "$c" ] && { config_file="$c"; break; }
  done

  if [ -z "$config_file" ]; then
    _warn "profile" "no config found for '${profile}' — using global default"
    _warn "profile" "tried: ${candidates[*]}"
    return 0
  fi

  local active="${HOME}/.openclaw/openclaw.json"
  local backup="${HOME}/.openclaw/openclaw.json.pre-${profile}"

  # Back up original once (idempotent)
  if [ -f "$active" ] && [ ! -L "$active" ] && [ ! -f "$backup" ]; then
    cp "$active" "$backup"
    _info "profile" "global config backed up → ${backup}"
  fi

  # Symlink active → selected profile (replace stale symlink)
  local target_real; target_real="$(realpath "$config_file" 2>/dev/null || echo "$config_file")"
  local active_real; active_real="$(realpath "$active" 2>/dev/null || echo "")"
  if [ "$target_real" = "$active_real" ]; then
    _info "profile" "profile '${profile}' already active"
  else
    ln -sf "$config_file" "$active"
    _info "profile" "activated profile '${profile}' → ${config_file}"
  fi

  export OPENCLAW_CONFIG="${config_file}"
  _var "profile" "OPENCLAW_CONFIG" "$OPENCLAW_CONFIG" "profile selection"
}

# ── MCP endpoint registration ─────────────────────────────────────────────────
# Registers orama agent-swarm as MCP server in Claude Code, Gemini CLI, Codex.
# Enable with:  ./start.sh --with-mcp   or   WITH_MCP=1 ./start.sh
# MCP server starts on OPENCLAW_MCP_PORT (default 18790).
# All registrations are idempotent.

_register_mcp_endpoints() {
  [ "${WITH_MCP:-0}" != "1" ] && return 0

  local mcp_port="${OPENCLAW_MCP_PORT:-18790}"
  _info "mcp" "registering orama-swarm MCP (port ${mcp_port})..."

  # Claude Code — idempotent
  if command -v claude >/dev/null 2>&1; then
    claude mcp remove orama-swarm >/dev/null 2>&1 || true
    if claude mcp add orama-swarm \
        -e "OPENCLAW_CONFIG=${OPENCLAW_CONFIG:-}" \
        -e "ORAMA_PORT=${US_PORT:-8001}" \
        -- openclaw mcp serve --port "$mcp_port" \
        >/dev/null 2>&1; then
      _info "mcp" "Claude Code: orama-swarm registered"
    else
      _warn "mcp" "Claude Code: registration failed (openclaw needs Node 22+)"
    fi
  fi

  # Gemini CLI — merge into ~/.gemini/settings.json
  if command -v gemini >/dev/null 2>&1; then
    local gcfg="${HOME}/.gemini/settings.json"
    mkdir -p "$(dirname "$gcfg")"
    [ -f "$gcfg" ] || echo '{}' > "$gcfg"
    python3 -c "
import json,pathlib
p=pathlib.Path('${gcfg}')
c=json.loads(p.read_text()) if p.exists() else {}
c.setdefault('mcpServers',{})['orama-swarm']={'command':'openclaw','args':['mcp','serve','--port','${mcp_port}']}
p.write_text(json.dumps(c,indent=2))
" 2>/dev/null && _info "mcp" "Gemini CLI: orama-swarm registered" || \
      _warn "mcp" "Gemini CLI: settings.json update skipped"
  fi

  # Codex CLI — merge into ~/.codex/config.json
  if command -v codex >/dev/null 2>&1; then
    local ccfg="${HOME}/.codex/config.json"
    mkdir -p "$(dirname "$ccfg")"
    [ -f "$ccfg" ] || echo '{}' > "$ccfg"
    python3 -c "
import json,pathlib
p=pathlib.Path('${ccfg}')
c=json.loads(p.read_text()) if p.exists() else {}
c.setdefault('mcpServers',{})['orama-swarm']={'command':'openclaw','args':['mcp','serve','--port','${mcp_port}']}
p.write_text(json.dumps(c,indent=2))
" 2>/dev/null && _info "mcp" "Codex CLI: orama-swarm registered" || \
      _warn "mcp" "Codex CLI: config.json update skipped"
  fi

  # Start background MCP server
  if command -v openclaw >/dev/null 2>&1; then
    local stale; stale="$(pid_on_port "$mcp_port" 2>/dev/null || true)"
    [ -n "$stale" ] && kill "$stale" 2>/dev/null || true
    openclaw mcp serve --port "$mcp_port" >>"${LOG_DIR}/mcp.log" 2>&1 &
    echo $! > "${LOG_DIR}/mcp.pid"
    _info "mcp" "MCP server PID $(cat "${LOG_DIR}/mcp.pid") listening on :${mcp_port}"
  else
    _warn "mcp" "openclaw not in PATH — MCP server not started"
    _warn "mcp" "hint: nvm use 22 && openclaw mcp serve --port ${mcp_port}"
  fi
}

_coord_pulse_script() {
  printf '%s\n' "$SCRIPT_DIR/scripts/install_coord_pulse.sh"
}

_coord_pulse_status() {
  local installer; installer="$(_coord_pulse_script)"
  if [ ! -f "$installer" ]; then
    _warn "coord-pulse" "installer missing: $installer"
    return 1
  fi
  if [ "${_OS_NAME:-$(uname -s 2>/dev/null || echo Unknown)}" != "Darwin" ]; then
    _warn "coord-pulse" "launchd coord pulse is macOS-only; Linux can run coord_pulse.sh from cron"
    return 1
  fi
  PERPETUA_TOOLS_ROOT="${PT_DIR:-}" PERPETUA_TOOLS_PATH="${PT_DIR:-}" \
    bash "$installer" --status
}

_ensure_coord_pulse() {
  local reason="${1:-startup}"
  local installer; installer="$(_coord_pulse_script)"
  if [ "${ORAMA_COORD_PULSE:-1}" = "0" ]; then
    _info "coord-pulse" "auto-install disabled (ORAMA_COORD_PULSE=0)"
    return 0
  fi
  if [ ! -f "$installer" ]; then
    _warn "coord-pulse" "installer missing: $installer"
    return 1
  fi
  if [ "${_OS_NAME:-$(uname -s 2>/dev/null || echo Unknown)}" != "Darwin" ]; then
    _info "coord-pulse" "non-macOS host; use cron or the Windows Task Scheduler counterpart"
    return 0
  fi
  _info "coord-pulse" "ensuring 15-minute Mac coord pulse (${reason})"
  PERPETUA_TOOLS_ROOT="${PT_DIR:-}" PERPETUA_TOOLS_PATH="${PT_DIR:-}" \
    COORD_PULSE_INTERVAL_SEC="${COORD_PULSE_INTERVAL_SEC:-900}" \
    bash "$installer" 2>&1 | while IFS= read -r line; do _info "coord-pulse" "$line"; done
}

# ── graceful shutdown ──────────────────────────────────────────────────────────
# SIGTERM/SIGINT handler.  Sends USR1 to orama engine to flush gossip/context
# to SQLite, then stops MCP server and all three services.
# Logs and SQLite state are preserved; in-flight requests drain for 2s.

_graceful_shutdown() {
  _info "shutdown" "signal received — flushing context before exit..."

  # Ask orama engine to flush gossip/state to SQLite (USR1 = soft flush)
  local orama_pid; orama_pid="$(pid_on_port "${US_PORT:-8001}" 2>/dev/null || true)"
  if [ -n "$orama_pid" ]; then
    kill -USR1 "$orama_pid" 2>/dev/null || true
    sleep 2
  fi

  # Stop MCP server
  if [ -f "${LOG_DIR}/mcp.pid" ]; then
    kill "$(cat "${LOG_DIR}/mcp.pid")" 2>/dev/null || true
    rm -f "${LOG_DIR}/mcp.pid"
  fi

  # Stop all orama services
  for _p in "${PT_PORT:-8000}" "${US_PORT:-8001}" "${PORTAL_PORT:-8002}"; do
    local _pid; _pid="$(pid_on_port "$_p" 2>/dev/null || true)"
    [ -n "$_pid" ] && kill "$_pid" 2>/dev/null || true
  done

  _info "shutdown" "all services stopped. logs preserved at ${LOG_DIR}/"
  exit 0
}

trap '_graceful_shutdown' SIGTERM SIGINT

# ── ASCII art banner ───────────────────────────────────────────────────────────
# Displays at every startup (not --stop/--status). Shows live tier + agent grid.
_print_banner() {
  local mode="${PT_MODE:-offline}"
  local mac_ip="${MAC_IP:-localhost}"
  local win_ip="${WIN_IP:-?}"
  local tier="?"
  local tier_label=""
  # tier_color: reserved for future ANSI colour output

  # Determine tier from reachability (-w 1 = 1s timeout per probe, avoids 30s OS hang)
  # All three probes run in parallel background subshells; total wall time = max(1s) not 3s.
  local mac_up=0 win_up=0 oc_up=0
  local _mac_f _win_f _oc_f
  _mac_f="$(mktemp /tmp/.orama_probe_mac_XXXXXX)"
  _win_f="$(mktemp /tmp/.orama_probe_win_XXXXXX)"
  _oc_f="$(mktemp /tmp/.orama_probe_oc_XXXXXX)"
  # _nc_probe: cross-platform 1-second TCP probe (nc -w1 on macOS/Linux, /dev/tcp fallback)
  _nc_probe() {
    local host="$1" port="$2"
    if command -v nc &>/dev/null; then
      nc -z -w 1 "$host" "$port" >/dev/null 2>&1
    else
      python3 - "$host" "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

try:
    with socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=1):
        pass
except OSError:
    raise SystemExit(1)
PY
    fi
  }
  ( _nc_probe localhost   1234  && echo 1 || echo 0 ) > "$_mac_f" &
  ( _nc_probe "$win_ip"   1234  && echo 1 || echo 0 ) > "$_win_f" &
  ( _nc_probe localhost   18789 && echo 1 || echo 0 ) > "$_oc_f"  &
  wait
  mac_up="$(cat "$_mac_f" 2>/dev/null || echo 0)"
  win_up="$(cat "$_win_f" 2>/dev/null || echo 0)"
  oc_up="$(cat  "$_oc_f"  2>/dev/null || echo 0)"
  rm -f "$_mac_f" "$_win_f" "$_oc_f"

  if   [ "$mac_up" -eq 1 ] && [ "$win_up" -eq 1 ]; then tier=1; tier_label="FULL  · Mac + Win (both nodes)"
  elif [ "$mac_up" -eq 1 ];                          then tier=2; tier_label="MAC   · Mac only"
  elif [ "$win_up" -eq 1 ];                          then tier=4; tier_label="WIN   · Win only"
  else                                                    tier=3; tier_label="LOCAL DOWN · cloud fallback (check network)"
  fi

  local oc_status="●"; [ "$oc_up" -eq 0 ] && oc_status="○"

  # Agent readiness per tier
  local mac_agents="main  mac-researcher  orchestrator"
  local win_agents="win-researcher  coder  autoresearcher"
  local mac_mark="✓"; [ "$mac_up" -eq 0 ] && mac_mark="✗"
  local win_mark="✓"; [ "$win_up" -eq 0 ] && win_mark="✗"

  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║                                                                  ║"
  printf "║   ██████╗ ██████╗  █████╗ ███╗   ███╗ █████╗                     ║\n"
  printf "║  ██╔═══██╗██╔══██╗██╔══██╗████╗ ████║██╔══██╗                    ║\n"
  printf "║  ██║   ██║██████╔╝███████║██╔████╔██║███████║                    ║\n"
  printf "║  ██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║██╔══██║                    ║\n"
  printf "║  ╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║██║  ██║                    ║\n"
  printf "║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝  v1.1.0.0          ║\n"
  echo "║                                                                  ║"
  echo "║  ὅραμα — vision/revelation · Layer 3 orchestration/meta-intel    ║"
  echo "╠══════════════════════════════════════════════════════════════════╣"
  printf "║  OpenClaw  %s %-8s  AlphaClaw → Perpetua-Tools → orama           ║\n" "$oc_status" ":18789"
  printf "║  Tier %-1s    %-52s║\n" "$tier" "$tier_label"
  printf "║  Mode      %-52s║\n" "$mode"
  echo "╠══════════════════════════════════════════════════════════════════╣"
  printf "║  Mac %s  %-9s  %-45s║\n" "$mac_mark" "localhost" "qwen3.5-9b-mlx (MLX · ctx 56k)"
  printf "║       %-63s║\n" "agents: $mac_agents"
  printf "║  Win %s  %-9s  %-45s║\n" "$win_mark" "$win_ip" "qwen3.5-27b (GGUF RTX 3080 · ctx 131k)"
  printf "║       %-63s║\n" "agents: $win_agents"
  echo "╠══════════════════════════════════════════════════════════════════╣"
  printf "║  PT   :%-5s   orama :%-5s   Portal :%-5s                         ║\n" \
    "${PT_PORT:-8000}" "${US_PORT:-8001}" "${PORTAL_PORT:-8002}"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
}

# ── start services ────────────────────────────────────────────────────────────

# Ollama model warm-up — loads model into GPU VRAM (different from pull/install).
# Hard install checks already ran above in ensure_requirements.sh.
_ollama_ensure_ready

# Activate per-profile openclaw config (no-op if OPENCLAW_PROFILE unset)
_openclaw_select_profile

_print_banner

# 1. Perpetua-Tools (PT) orchestrator
if [ -n "$PT_DIR" ] && [ -f "$PT_DIR/orchestrator/fastapi_app.py" ]; then
  if pid_on_port "$PT_PORT" | grep -q .; then
    echo "  PT   :$PT_PORT already running"
  else
    echo "  PT   starting → $LOG_DIR/pt.log"
    (cd "$PT_DIR" && PYTHONPATH="$PT_DIR/src:$PT_DIR" "$PT_PYTHON" -m uvicorn orchestrator.fastapi_app:app \
      --host "$PT_HOST" --port "$PT_PORT" \
      >> "$LOG_DIR/pt.log" 2>&1) &
    wait_for_port "$PT_PORT" "PT"
  fi
else
  echo "  PT   skipped (not found at ${PT_DIR:-unknown})"
fi

# 2. orama-system reasoning engine
if pid_on_port "$US_PORT" | grep -q .; then
  echo "  orama :$US_PORT already running"
else
  echo "  orama starting → $LOG_DIR/us.log"
  (cd "$SCRIPT_DIR" && PYTHONPATH="$SCRIPT_DIR/src:$SCRIPT_DIR" "$US_PYTHON" -m uvicorn orama_system.api_server:app \
    --host "$US_HOST" --port "$US_PORT" \
    >> "$LOG_DIR/us.log" 2>&1) &
  wait_for_port "$US_PORT" "orama"
fi

# 3. Portal
if pid_on_port "$PORTAL_PORT" | grep -q .; then
  echo "  Portal :$PORTAL_PORT already running"
else
  echo "  Portal starting → $LOG_DIR/portal.log"
  (cd "$SCRIPT_DIR" && PYTHONPATH="$SCRIPT_DIR/src:$SCRIPT_DIR" "$US_PYTHON" -m uvicorn orama_system.portal_server:app \
    --host "$PORTAL_HOST" --port "$PORTAL_PORT" \
    >> "$LOG_DIR/portal.log" 2>&1) &
  wait_for_port "$PORTAL_PORT" "Portal"
fi

echo "── services ready ───────────────────────────────────────────────────"
printf "  ●  PT      http://localhost:%s/health\n" "$PT_PORT"
printf "  ●  orama   http://localhost:%s/health\n" "$US_PORT"
printf "  ●  Portal  %s\n" "$PORTAL_URL"
printf "  ○  JSON    %s/api/status\n" "$PORTAL_URL"
echo ""
printf "  Logs  : %s/\n" "$LOG_DIR"
printf "  Stop  : ./start.sh --stop\n"
printf "  Debug : ORAMA_DEBUG=1 ./start.sh\n"
printf "  MCP   : ./start.sh --with-mcp  (exposes swarm to Claude/Codex/Gemini)\n"
printf "  Profile: OPENCLAW_PROFILE=mac-orchestrator ./start.sh\n"
printf "  LAN   : ./start.sh --lan-peer  (bind 0.0.0.0 + probe peer after start)\n"
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Register MCP endpoints after all services are confirmed up
_register_mcp_endpoints

if [ "${_LAN_PEER_MODE:-0}" = "1" ]; then
  _ensure_coord_pulse "--lan-peer" || true
fi

if [ "${_LAN_PEER_MODE:-0}" = "1" ]; then
  _run_lan_peer_probe || true
  _flush_lan_peer_outbox || true
fi

# ── network watcher install (--install-watcher flag or first-time setup) ──────
_WATCHER_SCRIPT="$SCRIPT_DIR/scripts/install_network_watch.sh"
if [[ "${INSTALL_NETWORK_WATCHER:-0}" == "1" ]] && [[ -f "$_WATCHER_SCRIPT" ]]; then
  _info "watcher" "Installing launchd network-change watcher..."
  bash "$_WATCHER_SCRIPT" 2>&1 | while IFS= read -r line; do _info "watcher" "$line"; done
elif ! launchctl list 2>/dev/null | grep -q "com.orama.network-watch"; then
  # Watcher not installed — nudge user once
  _warn "watcher" "Network-change watcher not installed. Run: ./start.sh --install-watcher"
  _warn "watcher" "Without it, IP changes after power cycle require manual ./start.sh --discover"
fi

if [ "$NO_OPEN" != "1" ]; then
  open_browser "$PORTAL_URL"
fi
