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
    GOPATH="$(go env GOPATH)"
    export PATH="${PATH}:${GOPATH}/bin"
  fi
fi

if [[ ! -d "$WORK/agent-audit" ]]; then
  git clone --depth 1 https://github.com/scadastrangelove/agent-audit "$WORK/agent-audit"
fi
python3 -m pip install -q -e "$WORK/agent-audit"

for path in "${SCAN_ROOTS[@]}"; do
  scan_root="$ROOT/$path"
  if [[ ! -d "$scan_root" || ! -r "$scan_root" ]]; then
    log "FAIL aguara:$path (missing or unreadable scan root)"
    FAIL=1
    continue
  fi
  run "aguara:$path" aguara scan "$scan_root" --ci
done

run agent-audit agent-audit scan-project "$ROOT" \
  --min-severity high -y --output "$WORK/agent-audit-report"

for path in "${SCAN_ROOTS[@]}"; do
  scan_root="$ROOT/$path"
  if [[ ! -d "$scan_root" || ! -r "$scan_root" ]]; then
    log "FAIL skill-scanner:$path (missing or unreadable scan root)"
    FAIL=1
    continue
  fi
  skill_dirs_file="$WORK/skill-dirs-${path//\//-}.txt"
  if ! find "$scan_root" -name SKILL.md -exec dirname {} \; | sort -u >"$skill_dirs_file"; then
    log "FAIL skill-scanner:$path (find failed)"
    FAIL=1
    continue
  fi
  if [[ ! -s "$skill_dirs_file" ]]; then
    log "SKIP skill-scanner:$path (no SKILL.md under root)"
    continue
  fi
  while IFS= read -r skill_dir; do
    rel="${skill_dir#"$ROOT"/}"
    run "skill-scanner:$rel" skill-scanner scan "$skill_dir"
  done <"$skill_dirs_file"
done

if [[ ! -f config/mac-orchestrator.json ]]; then
  log "FAIL mcp-scanner-config (config/mac-orchestrator.json missing)"
  FAIL=1
else
  MCP_SCAN_ARGS=(--analyzers yara --log-level error)
  if [[ -n "${MCP_SCANNER_API_KEY:-}" && -n "${MCP_SCANNER_LLM_API_KEY:-}" ]]; then
    MCP_SCAN_ARGS=(--analyzers api,yara,llm)
  fi
  run mcp-scanner-config mcp-scanner "${MCP_SCAN_ARGS[@]}" config --config-path config/mac-orchestrator.json
fi

if command -v ramparts >/dev/null 2>&1; then
  for path in "${SCAN_ROOTS[@]}"; do
    scan_root="$ROOT/$path"
    if [[ ! -d "$scan_root" || ! -r "$scan_root" ]]; then
      log "FAIL ramparts:$path (missing or unreadable scan root)"
      FAIL=1
      continue
    fi
    run "ramparts:$path" ramparts scan "$scan_root"
  done
else
  log "SKIP ramparts (install cargo package ramparts for local runs)"
fi

exit "$FAIL"
