#!/usr/bin/env bash
# Agent/MCP/skill security scans — Tier A bundle for CI.
#
# Runtime shape (2026-08-20): each scanner runs as its own parallel CI job
# (see .github/workflows/agent-security.yml), invoking this script with the
# scanner name as $1. Running with no argument (or "all") runs every scanner
# sequentially, for local use. Splitting the invocation, not the scan logic,
# fixed the runtime gap against gitleaks's own job (7s vs ~13m26s bundled) —
# see docs/v2/plans/2026-08-20-agent-security-ci-runtime-efficiency.md.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
SCAN_ROOTS=(bin/agents bin/orama-system/skills)
# WORK is per-invocation scratch (skill-dir lists, scan reports) -- fine to
# be PID-unique. CACHE_DIR is for content actions/cache is expected to
# restore between runs (the agent-audit clone, keyed on its pinned ref in
# the workflow) -- it must NOT include $$, or every run gets a fresh path
# the cache step's `path:` can never match, silently defeating the cache.
WORK="${RUNNER_TEMP:-/tmp}/agent-sec-$$"
CACHE_DIR="${RUNNER_TEMP:-/tmp}"
mkdir -p "$WORK"
FAIL=0

log() { echo "[agent-security] $*"; }
run() {
  local name="$1"; shift
  log "RUN $name"
  if "$@"; then log "OK $name"; else log "FAIL $name"; FAIL=1; fi
}

scan_aguara() {
  # v0.27.0 tag, pinned by commit SHA rather than "@latest" — this tool
  # audits supply-chain/agent-surface risk, so it must not itself be a
  # floating dependency. Bump AGUARA_REF deliberately (reviewed diff), never
  # silently. Do NOT pin to the "v1" tag: it resolves to aguara v0.6.0 (an
  # old Go major-version-branch tag), which predates --baseline and breaks
  # the skills scan below -- caught by running this script end-to-end
  # before shipping the pin, not by trusting the tag name.
  AGUARA_REF="${AGUARA_REF:-2ad546a95a03eb81f5255471c500ca326ee5220b}"
  if ! command -v aguara >/dev/null 2>&1; then
    if command -v go >/dev/null 2>&1; then
      go install "github.com/garagon/aguara/cmd/aguara@${AGUARA_REF}"
      GOPATH="$(go env GOPATH)"
      export PATH="${PATH}:${GOPATH}/bin"
    fi
  fi

  for path in "${SCAN_ROOTS[@]}"; do
    scan_root="$ROOT/$path"
    if [[ ! -d "$scan_root" || ! -r "$scan_root" ]]; then
      log "FAIL aguara:$path (missing or unreadable scan root)"
      FAIL=1
      continue
    fi
    aguara_args=(scan "$scan_root" --ci)
    if [[ "$path" == "bin/orama-system/skills" ]]; then
      baseline="$ROOT/config/agent-security/aguara-skills.baseline.json"
      if [[ ! -f "$baseline" ]]; then
        log "FAIL aguara:$path (missing baseline: config/agent-security/aguara-skills.baseline.json)"
        FAIL=1
        continue
      fi
      # TOXIC_CROSS_002 false-positives on internal env+subprocess coordination scripts.
      aguara_args+=(--baseline "$baseline" --disable-rule TOXIC_CROSS_002)
    fi
    run "aguara:$path" aguara "${aguara_args[@]}"
  done
}

scan_agent_audit() {
  python3 -m pip install -q --upgrade pip
  # CACHE_DIR/agent-audit, not WORK/agent-audit -- must match the path
  # cached by actions/cache in agent-security.yml exactly, so the clone
  # is actually restored between runs instead of re-cloned every time.
  AGENT_AUDIT_REF="${AGENT_AUDIT_REF:-d7b11f8bc02f0f212147a161e5d3bb10dcc117b2}"
  # Don't trust a restored/pre-existing checkout blindly -- verify its HEAD
  # actually matches AGENT_AUDIT_REF before scanning with it. A stale cache
  # entry, a corrupted restore, or a ref bump in this script without cache
  # invalidation would otherwise silently scan with the wrong tool version.
  if [[ -d "$CACHE_DIR/agent-audit" ]]; then
    current_head="$(git -C "$CACHE_DIR/agent-audit" rev-parse HEAD 2>/dev/null || echo "")"
    if [[ "$current_head" != "$AGENT_AUDIT_REF" ]]; then
      log "agent-audit cache HEAD ($current_head) != AGENT_AUDIT_REF ($AGENT_AUDIT_REF) -- reclone"
      rm -rf "$CACHE_DIR/agent-audit"
    fi
  fi
  if [[ ! -d "$CACHE_DIR/agent-audit" ]]; then
    git clone https://github.com/scadastrangelove/agent-audit "$CACHE_DIR/agent-audit"
    git -C "$CACHE_DIR/agent-audit" checkout --detach "$AGENT_AUDIT_REF"
  fi
  python3 -m pip install -q -e "$CACHE_DIR/agent-audit"

  run agent-audit agent-audit scan-project "$ROOT" \
    --min-severity high -y --output "$WORK/agent-audit-report"
}

scan_skill_scanner() {
  python3 -m pip install -q --upgrade pip
  python3 -m pip install -q cisco-ai-skill-scanner

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
}

scan_mcp_scanner() {
  python3 -m pip install -q --upgrade pip
  python3 -m pip install -q cisco-ai-mcp-scanner

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
}

scan_ramparts() {
  if command -v ramparts >/dev/null 2>&1; then
    :
  elif command -v cargo >/dev/null 2>&1; then
    RAMPARTS_VERSION="${RAMPARTS_VERSION:-0.8.2}"
    log "Installing ramparts@${RAMPARTS_VERSION} via cargo (requires Rust >= 1.91)"
    export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:${PATH}"
    if ! cargo install "ramparts@${RAMPARTS_VERSION}" --locked; then
      log "WARN ramparts install failed"
    fi
  fi

  if command -v ramparts >/dev/null 2>&1; then
    for path in "${SCAN_ROOTS[@]}"; do
      scan_root="$ROOT/$path"
      if [[ ! -d "$scan_root" || ! -r "$scan_root" ]]; then
        log "WARN ramparts:$path (missing or unreadable scan root — skipped)"
        continue
      fi
      # Skill trees are filesystem bundles, not live MCP HTTP endpoints.
      # Blocking (run, not warn_run): a Ramparts finding is a real scan
      # result like any other tool's, not an install/availability warning.
      if ramparts skills scan --help >/dev/null 2>&1; then
        run "ramparts-skills:$path" ramparts skills scan "$scan_root"
      else
        run "ramparts:$path" ramparts scan "$scan_root"
      fi
    done
  elif [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    log "FAIL ramparts (not installed — install: cargo install ramparts@${RAMPARTS_VERSION:-0.8.2} --locked)"
    FAIL=1
  else
    log "SKIP ramparts (install cargo package ramparts for local runs)"
  fi
}

TOOL="${1:-all}"
case "$TOOL" in
  aguara) scan_aguara ;;
  agent-audit) scan_agent_audit ;;
  skill-scanner) scan_skill_scanner ;;
  mcp-scanner) scan_mcp_scanner ;;
  ramparts) scan_ramparts ;;
  all)
    scan_aguara
    scan_agent_audit
    scan_skill_scanner
    scan_mcp_scanner
    scan_ramparts
    ;;
  *)
    echo "usage: $0 [aguara|agent-audit|skill-scanner|mcp-scanner|ramparts|all]" >&2
    exit 2
    ;;
esac

exit "$FAIL"
