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
  run "skill-scanner:$path" skill-scanner scan "$ROOT/$path"
done

if [[ -f config/mac-orchestrator.json ]]; then
  run mcp-scanner-config mcp-scanner scan config/mac-orchestrator.json || true
fi

if command -v ramparts >/dev/null 2>&1; then
  run ramparts ramparts scan "${SCAN_ROOTS[@]}"
else
  log "SKIP ramparts (install cargo package ramparts for local runs)"
fi

exit "$FAIL"
