#!/usr/bin/env bash
# bootstrap-environment.sh — idempotently apply the cross-cutting environment fixes
# the PT-orama stack depends on, so a FRESH clone/install reproduces them with no
# manual steps. Wired into start.sh; safe to run repeatedly. Repo-relative only.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OPENCLAW_ROOT="$(cd "$REPO/.." && pwd)"
PT_ROOT="$OPENCLAW_ROOT/perplexity-api/Perpetua-Tools"
CLAUDE_HOME="${HOME}/.claude"
log(){ printf '[bootstrap-env] %s\n' "$*"; }

# 0) Core ai-cli-mcp readiness. start.sh already delegates cross-cutting first-run
# work here, so keep package/registry mechanics in the canonical installer rather
# than duplicating npm/Claude commands in the launcher. Provider login/consent is
# intentionally never automated.
ensure_core_mcp() {
  if [ "${ORAMA_SKIP_MCP_BOOTSTRAP:-0}" = "1" ]; then
    log "MCP bootstrap bypassed by ORAMA_SKIP_MCP_BOOTSTRAP=1"
    return 0
  fi
  local installer="$REPO/bin/orama-system/scripts/install-mcp-stack.sh"
  [ -f "$installer" ] || { log "ERROR: canonical MCP installer missing: $installer"; return 1; }
  log "ensuring pinned ai-cli-mcp core readiness"
  bash "$installer" --core-only --non-interactive || {
    log "ERROR: ai-cli-mcp core readiness failed; external worker lane is unavailable"
    return 1
  }
}

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
    pre.append({"matcher":"Write|Edit","hooks":[{"type":"command","command":'python3 "$HOME/.claude/hooks/no-workstation-paths.py"'}]})
    json.dump(d,open(p,"w"),indent=2); print("[bootstrap-env] registered PreToolUse hygiene hook")
PY
}

ensure_pt_root_env() {
  export PERPETUA_TOOLS_ROOT="$PT_ROOT"
  local rc="${HOME}/.zshrc"
  grep -q 'PERPETUA_TOOLS_ROOT' "$rc" 2>/dev/null && return
  printf '\n# PT root for discover.py / PT hardware_policy (orama bootstrap)\nexport PERPETUA_TOOLS_ROOT="%s"\n' "$PT_ROOT" >> "$rc"
  log "ensured PERPETUA_TOOLS_ROOT in ~/.zshrc"
}

ensure_ollama_warm() {
  command -v launchctl >/dev/null 2>&1 && launchctl setenv OLLAMA_KEEP_ALIVE 30m 2>/dev/null || true
  if curl -s -o /dev/null --max-time 30 -d '{"model":"qwen3.5:9b-nvfp4","prompt":"","keep_alive":"30m","stream":false}' http://localhost:11434/api/generate 2>/dev/null; then
    log "ollama qwen3.5:9b-nvfp4 warmed (keep_alive 30m)"
  else log "ollama warm skipped (not reachable)"; fi
}

ensure_gateway_routing() {
  local cfg="${HOME}/.openclaw/openclaw.json"
  [ -f "$cfg" ] || { log "openclaw.json absent — skip routing"; return; }
  python3 - "$cfg" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); ch=False
for a in d.get("agents",{}).get("list",[]):
    if not isinstance(a,dict): continue
    if a.get("id")=="orchestrator" and a.get("model",{}).get("primary")!="ollama/qwen3.5:9b-nvfp4":
        a["model"]={"primary":"ollama/qwen3.5:9b-nvfp4","fallbacks":["lmstudio-mac/qwen3.5-9b-mlx"]}; ch=True
    if a.get("id")=="coder" and "fallbacks" not in a.get("model",{}):
        a.setdefault("model",{})["fallbacks"]=["ollama/qwen3.5:9b-nvfp4","lmstudio-mac/qwen3.5-9b-mlx"]; ch=True
    _coder="lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"
    if a.get("id")=="autoresearcher" and a.get("model",{}).get("primary")!=_coder:
        a["model"]={"primary":_coder,"fallbacks":["ollama/qwen3.5:9b-nvfp4","lmstudio-mac/qwen3.5-9b-mlx"]}; ch=True
if ch: json.dump(d,open(p,"w"),indent=2); print("[bootstrap-env] gateway routing: orchestrator ollama-primary, coder+autoresearcher routed")
PY
}

ensure_skills_wrappers() {
  [ -x "$REPO/scripts/consolidate-skills.sh" ] || return
  bash "$REPO/scripts/consolidate-skills.sh" --apply >/dev/null 2>&1 && log "skills consolidated (wrappers current)"
}

ensure_rag_mcp() {
  [ -f "$REPO/scripts/ensure-rag-mcp.py" ] || return
  python3 "$REPO/scripts/ensure-rag-mcp.py" --apply >/dev/null 2>&1 && log "RAG MCP wiring ensured (CLI + Desktop)"
}

# MCP is attempted first. start.sh currently treats this bootstrap layer as
# fail-soft, preserving base-service resilience; the failure is explicit and the
# worker lane is never reported ready. A future launcher hard-gate can call the
# same canonical installer without changing this ownership boundary.
ensure_core_mcp || true
install_hygiene_hook
ensure_pt_root_env
ensure_ollama_warm
ensure_gateway_routing
ensure_skills_wrappers
ensure_rag_mcp
log "done"
