#!/usr/bin/env bash
# Agent/MCP/skill security scans — Tier A bundle for CI.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
SCAN_ROOTS=(bin/agents bin/orama-system/skills)
WORK="${RUNNER_TEMP:-/tmp}/agent-sec-$$"
mkdir -p "$WORK"
FAIL=0

log() { echo "[agent-security] $*"; }
run() {
  local name="$1"; shift
  log "RUN $name"
  if "$@"; then log "OK $name"; else log "FAIL $name"; FAIL=1; fi
}

python3 -m pip install -q --upgrade pip
python3 -m pip install -q cisco-ai-skill-scanner cisco-ai-mcp-scanner

if ! command -v aguara >/dev/null 2>&1; then
  if command -v go >/dev/null 2>&1; then
    go install github.com/garagon/aguara/cmd/aguara@latest
    export PATH="${PATH}:$(go env GOPATH)/bin"
  fi
fi

if [[ ! -d "$WORK/agent-audit" ]]; then
  git clone --depth 1 https://github.com/scadastrangelove/agent-audit "$WORK/agent-audit"
fi
python3 -m pip install -q -e "$WORK/agent-audit"

run aguara aguara scan "${SCAN_ROOTS[@]}"

run agent-audit agent-audit scan-project "$ROOT" \
  --min-severity high -y --output "$WORK/agent-audit-report"

for path in "${SCAN_ROOTS[@]}"; do
  found=0
  while IFS= read -r skill_dir; do
    found=1
    rel="${skill_dir#$ROOT/}"
    run "skill-scanner:$rel" skill-scanner scan "$skill_dir"
  done < <(find "$ROOT/$path" -name SKILL.md -exec dirname {} \; 2>/dev/null | sort -u)
  if [[ "$found" -eq 0 ]]; then
    log "SKIP skill-scanner:$path (no SKILL.md under root)"
  fi
done

if [[ -f config/mac-orchestrator.json ]]; then
  MCP_SCAN_ARGS=(--analyzers yara --log-level error)
  if [[ -n "${MCP_SCANNER_API_KEY:-}" && -n "${MCP_SCANNER_LLM_API_KEY:-}" ]]; then
    MCP_SCAN_ARGS=(--analyzers api,yara,llm)
  fi
  run mcp-scanner-config mcp-scanner "${MCP_SCAN_ARGS[@]}" config --config-path config/mac-orchestrator.json
fi

if command -v ramparts >/dev/null 2>&1; then
  run ramparts ramparts scan "${SCAN_ROOTS[@]}"
else
  log "SKIP ramparts (install cargo package ramparts for local runs)"
fi

exit "$FAIL"
