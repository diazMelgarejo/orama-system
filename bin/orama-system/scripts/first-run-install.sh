#!/usr/bin/env bash
# first-run-install.sh — Idempotent first-run bootstrap for orama-system stack
# Full reference: bin/orama-system/references/first-run-install.md
# MCP workers (ai-cli, gemini): bin/orama-system/scripts/install-mcp-stack.sh
#
# Usage:
#   bash first-run-install.sh status
#   bash first-run-install.sh install [--dry-run] [--force]
#   bash first-run-install.sh run [--dry-run] [--force]   # alias of install
#
# Markers: ~/.orama-system/first-run.done  +  ~/.orama-system/first-run.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ORAMA_REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
if git -C "$BIN_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  ORAMA_REPO_ROOT="$(git -C "$BIN_ROOT" rev-parse --show-toplevel)"
fi
# shellcheck source=lib/openclaw-env.sh
source "$SCRIPT_DIR/lib/openclaw-env.sh"

DRY_RUN=false
FORCE=false
CMD="${1:-status}"
shift || true
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

STATE_DIR="${ORAMA_STATE_DIR:-$HOME/.orama-system}"
STATE_JSON="$STATE_DIR/first-run.json"
DONE_MARKER="$STATE_DIR/first-run.done"
mkdir -p "$STATE_DIR"

NVM_NODE_BIN="${NVM_NODE_BIN:-$HOME/.nvm/versions/node/v22.22.2/bin}"
OLLAMA_MODELS=(qwen3.5:9b-nvfp4 bge-m3)

_log()  { echo "[first-run] $*"; }
_ok()   { echo "[first-run] ✓ $*"; }
_warn() { echo "[first-run] ! $*" >&2; }
_skip() { echo "[first-run] → skip: $*"; }
_fail() { echo "[first-run] ✗ $*" >&2; }
_run()  { $DRY_RUN && echo "[dry-run] $*" || eval "$*"; }

OPENCLAW_ROOT="$(detect_openclaw_root || true)"
MCP_JSON="$(resolve_openclaw_mcp_json || true)"

# ── JSON state helpers (minimal, no jq dependency for writes) ───────────────
_json_get_component_status() {
  local comp="$1"
  if [ ! -f "$STATE_JSON" ]; then echo ""; return; fi
  python3 -c "
import json, sys
p = sys.argv[1]
c = sys.argv[2]
try:
    d = json.load(open(p))
    print(d.get('components', {}).get(c, {}).get('status', ''))
except Exception:
    print('')
" "$STATE_JSON" "$comp" 2>/dev/null || echo ""
}

_json_get_model_status() {
  local model="$1"
  if [ ! -f "$STATE_JSON" ]; then echo ""; return; fi
  python3 -c "
import json, sys
p, m = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(p))
    print(d.get('components', {}).get('ollama', {}).get('models', {}).get(m, ''))
except Exception:
    print('')
" "$STATE_JSON" "$model" 2>/dev/null || echo ""
}

_json_set_component() {
  local comp="$1" status="$2" detail="${3:-}"
  $DRY_RUN && return 0
  python3 -c "
import json, os, sys
from datetime import datetime, timezone
path, comp, status, detail = sys.argv[1:5]
data = {'version': 2, 'components': {}}
if os.path.isfile(path):
    try:
        data = json.load(open(path))
    except Exception:
        pass
data.setdefault('version', 2)
data.setdefault('components', {})[comp] = {
    'status': status,
    'detail': detail,
    'checked_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
if comp == 'ollama':
    data['components'][comp].setdefault('models', {})
json.dump(data, open(path, 'w'), indent=2)
" "$STATE_JSON" "$comp" "$status" "$detail"
}

_json_set_model_status() {
  local model="$1" status="$2"
  $DRY_RUN && return 0
  python3 -c "
import json, os, sys
from datetime import datetime, timezone
path, model, status = sys.argv[1:4]
data = {'version': 2, 'components': {}}
if os.path.isfile(path):
    try:
        data = json.load(open(path))
    except Exception:
        pass
ollama = data.setdefault('components', {}).setdefault('ollama', {})
models = ollama.setdefault('models', {})
models[model] = {
    'status': status,
    'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
json.dump(data, open(path, 'w'), indent=2)
" "$STATE_JSON" "$model" "$status"
}

_heavy_step_satisfied() {
  local comp="$1"
  [ "$(_json_get_component_status "$comp")" = "ok" ]
}

_run_component_check() {
  local id="$1" fn="$2"
  if [ "$(_json_get_component_status "$id")" = "ok" ] && ! $FORCE; then
    _skip "$id (satisfied, use --force to re-validate)"
    return 0
  fi
  "$fn" || { HARD_FAIL=1; return 1; }
}

_ollama_fetch_tags() {
  curl -sf --max-time 5 http://localhost:11434/api/tags 2>/dev/null || echo ""
}

_ollama_model_in_tags() {
  local model="$1" tags="$2"
  echo "$tags" | grep -q "$model"
}

# Fast probe only — never pulls (safe for `status`, <5s)
probe_ollama() {
  local missing="" tags
  if ! command -v ollama >/dev/null 2>&1; then
    _fail "0.3 ollama: binary not on PATH"
    _json_set_component "ollama" "fail" "no binary"
    return 1
  fi
  if ! curl -sf --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
    _fail "0.3 ollama: API not reachable at localhost:11434"
    _json_set_component "ollama" "fail" "api down"
    return 1
  fi
  tags="$(_ollama_fetch_tags)"
  for m in "${OLLAMA_MODELS[@]}"; do
    if _ollama_model_in_tags "$m" "$tags"; then
      _json_set_model_status "$m" "ok"
    else
      missing="${missing} ${m}"
      local prior
      prior="$(_json_get_model_status "$m")"
      if [ "$prior" = "pulling" ]; then
        _json_set_model_status "$m" "interrupted"
      fi
    fi
  done
  if [ -n "$missing" ]; then
    _fail "0.3 ollama: missing models:$missing — run: first-run-install.sh run"
    _json_set_component "ollama" "fail" "missing:$missing"
    return 1
  fi
  _ok "0.3 ollama: API up; qwen3.5:9b-nvfp4 + bge-m3 present"
  _json_set_component "ollama" "ok" "models present"
  return 0
}

# Heavy step — visible progress, per-model resume (run only)
run_ollama_models() {
  if _heavy_step_satisfied "ollama"; then
    _skip "0.3 ollama (models satisfied; --force does not re-pull)"
    return 0
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    _fail "0.3 ollama: binary not on PATH"
    _json_set_component "ollama" "fail" "no binary"
    return 1
  fi
  if ! curl -sf --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
    _fail "0.3 ollama: start Ollama (open app or: ollama serve)"
    _json_set_component "ollama" "fail" "api down"
    return 1
  fi

  local tags fail=0 m prior
  tags="$(_ollama_fetch_tags)"
  _log "0.3 ollama: ensuring required models (pull shows progress; safe to interrupt and re-run)"

  for m in "${OLLAMA_MODELS[@]}"; do
    if _ollama_model_in_tags "$m" "$tags"; then
      _json_set_model_status "$m" "ok"
      _ok "0.3 ollama: $m already present"
      continue
    fi
    prior="$(_json_get_model_status "$m")"
    case "$prior" in
      ok)
        _warn "0.3 ollama: $m marked ok in state but missing from API — re-pulling"
        ;;
      pulling|interrupted)
        _log "0.3 ollama: resuming pull for $m (prior state: $prior)"
        ;;
    esac
    _log "0.3 ollama: pulling $m ..."
    _json_set_model_status "$m" "pulling"
    if $DRY_RUN; then
      echo "[dry-run] ollama pull $m"
      _json_set_model_status "$m" "ok"
      continue
    fi
    if ! ollama pull "$m"; then
      _fail "0.3 ollama: pull failed for $m"
      _json_set_model_status "$m" "fail"
      fail=1
      continue
    fi
    _json_set_model_status "$m" "ok"
    _ok "0.3 ollama: $m pull complete"
    tags="$(_ollama_fetch_tags)"
  done

  if [ "$fail" -ne 0 ]; then
    _json_set_component "ollama" "fail" "pull incomplete"
    return 1
  fi
  if ! probe_ollama; then
    return 1
  fi
  return 0
}

# ── Component probes ───────────────────────────────────────────────────────
check_node() {
  local node_bin=""
  if [ -x "${NVM_NODE_BIN}/node" ]; then
    node_bin="${NVM_NODE_BIN}/node"
  elif command -v node >/dev/null 2>&1; then
    node_bin="$(command -v node)"
  else
    _fail "0.1 node: no node found (expected ${NVM_NODE_BIN}/node)"
    _json_set_component "node" "fail" "missing"
    return 1
  fi
  local ver major
  ver="$("$node_bin" --version 2>/dev/null || echo v0)"
  major="${ver#v}"; major="${major%%.*}"
  if [ "${major:-0}" -lt 20 ] 2>/dev/null; then
    _fail "0.1 node: $ver at $node_bin (need v20+; use NVM — see references/first-run-install.md §0.1)"
    _json_set_component "node" "fail" "$ver"
    return 1
  fi
  if $FORCE; then
    _log "0.1 node: re-validated $ver ($node_bin)"
  fi
  _ok "0.1 node: $ver"
  _json_set_component "node" "ok" "$ver"
  return 0
}

check_python313() {
  if ! command -v python3.13 >/dev/null 2>&1; then
    _fail "0.2 python3.13: not found (brew install python@3.13)"
    _json_set_component "python313" "fail" "missing"
    return 1
  fi
  local ver
  ver="$(python3.13 --version 2>&1)"
  _ok "0.2 $ver"
  _json_set_component "python313" "ok" "$ver"
  return 0
}

check_crg() {
  if ! command -v uvx >/dev/null 2>&1; then
    _fail "0.4 code-review-graph: uvx not on PATH"
    _json_set_component "crg" "fail" "no uvx"
    return 1
  fi
  if ! uvx code-review-graph --version >/dev/null 2>&1; then
    _fail "0.4 code-review-graph: uvx code-review-graph failed"
    _json_set_component "crg" "fail" "uvx failed"
    return 1
  fi
  if [ -z "$OPENCLAW_ROOT" ]; then
    _warn "0.4 code-review-graph: OPENCLAW_ROOT not found — set OPENCLAW_ROOT"
    _json_set_component "crg" "warn" "no openclaw root"
    return 0
  fi
  if [ ! -f "${MCP_JSON:-}" ]; then
    if $DRY_RUN; then
      _skip "0.4 would create $MCP_JSON"
    elif ensure_openclaw_mcp_json _log; then
      _ok "0.4 code-review-graph: created $MCP_JSON"
    else
      _warn "0.4 code-review-graph: could not create .mcp.json — set OPENCLAW_ROOT"
      _json_set_component "crg" "warn" "no mcp.json"
      return 0
    fi
  fi
  if command -v jq >/dev/null 2>&1; then
    if ! jq -e '.mcpServers["code-review-graph"]' "$MCP_JSON" >/dev/null 2>&1; then
      _warn "0.4 code-review-graph: not registered in .mcp.json — run: code-review-graph install --platform claude-code --repo \"$OPENCLAW_ROOT\""
      _json_set_component "crg" "warn" "not in mcp.json"
      return 0
    fi
  fi
  _ok "0.4 code-review-graph: uvx OK; MCP entry present"
  _json_set_component "crg" "ok" "registered"
  return 0
}

check_gbrain() {
  if ! command -v gbrain >/dev/null 2>&1; then
    _fail "0.5 gbrain: not on PATH"
    _json_set_component "gbrain" "fail" "missing"
    return 1
  fi
  if [ ! -f "$HOME/.gbrain/config.json" ]; then
    _warn "0.5 gbrain: ~/.gbrain/config.json missing — run /setup-gbrain"
    _json_set_component "gbrain" "warn" "no config"
    return 0
  fi
  _ok "0.5 gbrain: CLI + config present"
  _json_set_component "gbrain" "ok" "config present"
  return 0
}

check_embeddings() {
  if [ -z "${MCP_JSON:-}" ] || [ ! -f "$MCP_JSON" ]; then
    _warn "0.5.1 embeddings: .mcp.json not found — run setup-embeddings after OPENCLAW_ROOT is set"
    _json_set_component "embeddings" "warn" "no mcp.json"
    return 0
  fi
  if command -v jq >/dev/null 2>&1; then
    local model
    model="$(jq -r '.mcpServers["code-review-graph"].env.CRG_OPENAI_MODEL // ""' "$MCP_JSON" 2>/dev/null || echo "")"
    if [ "$model" = "bge-m3" ]; then
      _ok "0.5.1 embeddings: CRG wired to bge-m3"
      _json_set_component "embeddings" "ok" "bge-m3"
      return 0
    fi
  fi
  _warn "0.5.1 embeddings: CRG not on bge-m3 — run: bash bin/orama-system/mcp-install/scripts/setup-embeddings"
  _json_set_component "embeddings" "warn" "not bge-m3"
  return 0
}

run_embeddings() {
  local setup="$BIN_ROOT/mcp-install/scripts/setup-embeddings"
  if [ ! -x "$setup" ] && [ ! -f "$setup" ]; then
    _warn "0.5.1 embeddings: setup-embeddings script missing"
    _json_set_component "embeddings" "warn" "no script"
    return 0
  fi
  if _heavy_step_satisfied "embeddings"; then
    _skip "0.5.1 embeddings (satisfied; --force does not re-run setup-embeddings)"
    return 0
  fi
  _log "0.5.1 running setup-embeddings (idempotent; output below)..."
  if $DRY_RUN; then
    echo "[dry-run] OPENCLAW_DIR=\"$OPENCLAW_ROOT\" bash \"$setup\""
    return 0
  fi
  _json_set_component "embeddings" "running" "setup-embeddings"
  if [ -z "$OPENCLAW_ROOT" ]; then
    _warn "0.5.1 embeddings: OPENCLAW_ROOT not set — skip setup-embeddings"
    _json_set_component "embeddings" "warn" "no openclaw root"
    return 0
  fi
  if OPENCLAW_DIR="$OPENCLAW_ROOT" bash "$setup"; then
    _ok "0.5.1 embeddings: setup-embeddings complete"
    _json_set_component "embeddings" "ok" "bge-m3 wired"
    return 0
  fi
  _warn "0.5.1 setup-embeddings reported issues (non-fatal if Ollama warming up)"
  _json_set_component "embeddings" "warn" "setup-embeddings warnings"
  return 0
}

check_claude() {
  if ! command -v claude >/dev/null 2>&1; then
    _warn "0.6 claude: not on PATH (npm install -g @anthropic-ai/claude-code)"
    _json_set_component "claude" "warn" "missing"
    return 0
  fi
  local profiles="$BIN_ROOT/skills/code-review/profiles/J-drona23-v5"
  if [ ! -d "$profiles" ]; then
    _warn "0.6 profiles: $profiles not found"
    _json_set_component "claude" "warn" "profiles missing"
    return 0
  fi
  _ok "0.6 claude: CLI present; profiles at code-review skill"
  _json_set_component "claude" "ok" "profiles present"
  return 0
}

check_precompact() {
  local settings="${OPENCLAW_ROOT:+$OPENCLAW_ROOT/.claude/settings.local.json}"
  if [ -z "$settings" ] || [ ! -f "$settings" ]; then
    _warn "0.7 PreCompact: settings.local.json not found under OPENCLAW_ROOT"
    _json_set_component "precompact" "warn" "no settings.local.json"
    return 0
  fi
  if grep -q '"PreCompact"' "$settings" 2>/dev/null; then
    _ok "0.7 PreCompact hook present"
    _json_set_component "precompact" "ok" "hook found"
    return 0
  fi
  _warn "0.7 PreCompact: hook not found in $settings"
  _json_set_component "precompact" "warn" "hook missing"
  return 0
}

probe_omniroute() {
  local url="${OMNIROUTE_URL:-http://127.0.0.1:20128/api/mcp/stream}"
  local tok="${OMNIROUTE_TOKEN:-}"
  if [ -z "$tok" ]; then
    _skip "A.1 omniroute: no OMNIROUTE_TOKEN (optional)"
    _json_set_component "omniroute" "skip" "optional"
    return 0
  fi
  if curl -sf --max-time 2 "$url" -H "Authorization: Bearer $tok" >/dev/null 2>&1; then
    _ok "A.1 omniroute: reachable (optional)"
    _json_set_component "omniroute" "ok" "up"
  else
    _skip "A.1 omniroute: unavailable (optional — OK)"
    _json_set_component "omniroute" "skip" "unavailable"
  fi
  return 0
}

HARD_FAIL=0

cmd_status() {
  _log "orama-system first-run status (fast probes only — no pulls)"
  _log "ORAMA_REPO_ROOT=$ORAMA_REPO_ROOT"
  _log "OPENCLAW_ROOT=${OPENCLAW_ROOT:-<unset>}"
  _log "STATE=$STATE_JSON"
  echo ""
  if [ -f "$DONE_MARKER" ]; then
    _ok "first-run.done marker present"
  else
    _log "first-run.done: not set"
  fi
  echo ""
  HARD_FAIL=0
  check_node || true
  check_python313 || true
  probe_ollama || true
  check_crg || true
  check_gbrain || true
  check_embeddings || true
  check_claude || true
  check_precompact || true
  probe_omniroute || true
  echo ""
  _log "Next: bash bin/orama-system/scripts/install-mcp-stack.sh (MCP workers, separate)"
  if [ -f "$STATE_JSON" ]; then
    echo ""
    echo "State file: $STATE_JSON"
    cat "$STATE_JSON"
  fi
  return 0
}

cmd_run() {
  _log "orama-system first-run install"
  _log "Dry-run: $DRY_RUN | Force: $FORCE"
  _log "ORAMA_REPO_ROOT=$ORAMA_REPO_ROOT"
  _log "OPENCLAW_ROOT=${OPENCLAW_ROOT:-<unset>}"
  echo ""

  HARD_FAIL=0
  _run_component_check node check_node || true
  _run_component_check python313 check_python313 || true
  run_ollama_models || true
  _run_component_check crg check_crg || true
  _run_component_check gbrain check_gbrain || true
  run_embeddings || true
  _run_component_check claude check_claude || true
  _run_component_check precompact check_precompact || true
  probe_omniroute || true

  echo ""
  if [ "$HARD_FAIL" -eq 0 ]; then
    if ! $DRY_RUN; then
      touch "$DONE_MARKER"
      STATE_JSON="$STATE_JSON" python3 -c "
import json, os
from datetime import datetime, timezone
p = os.environ['STATE_JSON']
data = {'version': 2, 'components': {}}
if os.path.isfile(p):
    try:
        data = json.load(open(p))
    except Exception:
        pass
data['completed_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(data, open(p, 'w'), indent=2)
" 2>/dev/null || true
    fi
    _ok "First-run complete — marker: $DONE_MARKER"
    _log "Run MCP stack separately: bash bin/orama-system/scripts/install-mcp-stack.sh"
  else
    _fail "First-run incomplete — fix failures above and re-run (resume picks up incomplete steps)"
    exit 1
  fi
}

case "$CMD" in
  status) cmd_status ;;
  install|run) cmd_run ;;
  *)
    echo "Usage: $0 {status|install|run} [--dry-run] [--force]" >&2
    exit 2
    ;;
esac
