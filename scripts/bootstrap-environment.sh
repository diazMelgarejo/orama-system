#!/usr/bin/env bash
# bootstrap-environment.sh — idempotently apply the cross-cutting environment fixes
# the PT-orama stack depends on, so a FRESH clone/install reproduces them with no
# manual steps. Wired into start.sh; safe to run repeatedly. Repo-relative only
# (derives all tree paths from this script's location — no machine paths baked in).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"              # orama-system root
OPENCLAW_ROOT="$(cd "$REPO/.." && pwd)"               # umbrella tree (sibling repos under it)
PT_ROOT="$OPENCLAW_ROOT/perplexity-api/Perpetua-Tools"
CLAUDE_HOME="${HOME}/.claude"
log(){ printf '[bootstrap-env] %s\n' "$*"; }

# 1) Write-time path-hygiene PreToolUse guard (blocks workstation paths in tracked files)
install_hygiene_hook() {
  local src="$REPO/scripts/hooks/no-workstation-paths.py"
  local dst="$CLAUDE_HOME/hooks/no-workstation-paths.py"
  [ -f "$src" ] || { log "hygiene hook source missing — skip"; return; }
  mkdir -p "$CLAUDE_HOME/hooks"
  cmp -s "$src" "$dst" 2>/dev/null || { cp "$src" "$dst"; chmod +x "$dst"; log "installed hygiene hook"; }
  python3 - "$CLAUDE_HOME/settings.json" <<'PY'
import json,os,sys
p=sys.argv[1]
d=json.load(open(p)) if os.path.exists(p) else {}
pre=d.setdefault("hooks",{}).setdefault("PreToolUse",[])
if not any("no-workstation-paths" in h.get("command","") for e in pre for h in e.get("hooks",[])):
    pre.append({"matcher":"Write|Edit","hooks":[{"type":"command",
        "command":'python3 "$HOME/.claude/hooks/no-workstation-paths.py"'}]})
    json.dump(d,open(p,"w"),indent=2); print("[bootstrap-env] registered PreToolUse hygiene hook")
PY
}

# 2) PERPETUA_TOOLS_ROOT — discover.py / PT hardware_policy resolution after any tree move
ensure_pt_root_env() {
  export PERPETUA_TOOLS_ROOT="$PT_ROOT"
  local rc="${HOME}/.zshrc"
  grep -q 'PERPETUA_TOOLS_ROOT' "$rc" 2>/dev/null && return
  printf '\n# PT root for discover.py / PT hardware_policy (orama bootstrap)\nexport PERPETUA_TOOLS_ROOT="%s"\n' "$PT_ROOT" >> "$rc"
  log "ensured PERPETUA_TOOLS_ROOT in ~/.zshrc"
}

# 3) Warm the Mac orchestrator model, only through the Perpetua-Tools one-model gate. No gate, no load.
ensure_ollama_warm() {
  local pt="${PERPETUA_TOOLS_ROOT:-$PT_ROOT}"
  if [ ! -f "$pt/src/perpetua_tools/local_model_gate.py" ]; then
    log "one-model gate unavailable; not loading a model"
    return 0
  fi
  PYTHONPATH="$pt/src" python3 -m perpetua_tools.local_model_gate limits --apply >/dev/null 2>&1 \
    || log "could not set the engine limits"
  if PYTHONPATH="$pt/src" python3 -m perpetua_tools.local_model_gate ensure ollama qwen3.5:9b-mlx >/dev/null 2>&1; then
    log "ollama qwen3.5:9b-mlx is the loaded model"
  else
    log "gate declined; no model loaded (restart Ollama if the limits were only just set)"
  fi
}

# 4) Gateway agent routing — report only. The routes come from the OpenClaw defaults (live Perpetua-Tools file,
# else the stamped vendored copy, else fail closed). Start-up never writes openclaw.json: a change is applied
# deliberately, one reviewed patch at a time, through the staged restore steps.
report_gateway_routing() {
  local cfg="${HOME}/.openclaw/openclaw.json"
  local resolver="$REPO/scripts/lib/openclaw_defaults_resolver.py"
  [ -f "$cfg" ] || { log "openclaw.json absent — skip routing report"; return; }
  [ -f "$resolver" ] || { log "defaults resolver missing — skip routing report"; return; }
  local out rc=0
  out="$(python3 "$resolver" --check "$cfg" 2>&1)" || rc=$?
  case "$rc" in
    0) log "gateway routing matches the OpenClaw defaults" ;;
    1) log "gateway routing drift (nothing was changed): $(printf '%s\n' "$out" | tail -n 1)"
       log "review:  python3 scripts/lib/openclaw_defaults_resolver.py --check ~/.openclaw/openclaw.json"
       log "patch:   python3 scripts/lib/openclaw_defaults_resolver.py --render-patch --shape entries" ;;
    *) log "routing not checked: $(printf '%s\n' "$out" | tail -n 1)" ;;
  esac
}

# 5) Skills — keep .claude/skills as thin wrappers over the bin canonical
ensure_skills_wrappers() {
  [ -x "$REPO/scripts/consolidate-skills.sh" ] || return
  bash "$REPO/scripts/consolidate-skills.sh" --apply >/dev/null 2>&1 && log "skills consolidated (wrappers current)"
}

# 6) RAG MCP parity — gbrain + CRG wired in BOTH Claude Code CLI and the Desktop app.
# Single source of truth: scripts/ensure-rag-mcp.py (skills point here, never re-implement).
ensure_rag_mcp() {
  [ -f "$REPO/scripts/ensure-rag-mcp.py" ] || return
  python3 "$REPO/scripts/ensure-rag-mcp.py" --apply >/dev/null 2>&1 && log "RAG MCP wiring ensured (CLI + Desktop)"
}

install_hygiene_hook
ensure_pt_root_env
ensure_ollama_warm
report_gateway_routing
ensure_skills_wrappers
ensure_rag_mcp
log "done"
