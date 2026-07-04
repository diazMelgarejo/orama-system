# ADR-045: gstack/gbrain/CRG Error Resilience & Safe Defaults

**Date:** 2026-07-04  
**Status:** ACCEPTED  
**Supersedes:** None  
**Affected Components:** `/sync-gbrain`, all orama-system skills using gstack/gbrain/CRG  

## Problem

Skills that interface with gstack, gbrain, and code-review-graph fail silently or hang when:
1. gbrain local engine is misconfigured or unreachable
2. Autopilot is running and jamming sync operations
3. Network timeouts occur without fallback
4. Agent sandboxes lack MCP access (ENOTFOUND errors)
5. Concurrent writes poison state files
6. No clear error messages for new agents

This creates poor developer experience and blocks new agents from reliably running these tools.

## Root Causes

From session memory and documented incidents:
- **gbrain checkpoint bug** (#1802): SIGTERM poisons import-checkpoint.json → next sync rm-rf's repo root
- **autopilot jam**: launchd KeepAlive silently lets sources go stale; kill alone won't stop it
- **path migrations**: repo moves spawn stale duplicate sources that never auto-remove
- **sandbox limits**: Agent subagents get restricted Bash; MCP tools work but tooling scripts fail
- **hard deadlines**: gbrain/git/installs need hard ceilings; uncapped calls hang 40+ min
- **state fragmentation**: concurrent agents writing to `.gbrain-sync-state.json` without locks

## Solution

### 1. Error Detection Framework (PRE-FLIGHT CHECKS)

Every skill using gstack/gbrain/CRG MUST run these checks FIRST, before any operation:

```bash
# Detect function (idempotent, non-blocking, always succeeds)
_gbrain_detect_errors() {
  local errors=()
  
  # Check 1: Local engine status
  if command -v gstack-gbrain-detect >/dev/null 2>&1; then
    local status=$(gstack-gbrain-detect 2>/dev/null | grep -o '"gbrain_local_status":[^,}]*' | sed 's/.*://; s/[ "]//g')
    case "$status" in
      "no-cli")        errors+=("gbrain CLI not installed") ;;
      "missing-config") errors+=("gbrain config missing") ;;
      "broken-config"|"broken-db") errors+=("gbrain broken: $status") ;;
    esac
  fi
  
  # Check 2: Autopilot jam detection
  if pgrep -f 'gbrain autopilot' >/dev/null 2>&1; then
    local ap_pid=$(pgrep -f 'gbrain autopilot' | head -1)
    local ap_cwd=$(lsof -a -p "$ap_pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
    if [ "${ap_cwd:-/}" = "/" ]; then
      errors+=("autopilot jam: cwd=/")
    fi
  fi
  
  # Check 3: Stale lock file (older than 10 min = stale)
  if [ -f ~/.gstack/.sync-gbrain.lock ]; then
    local age=$(( $(date +%s) - $(stat -f %m ~/.gstack/.sync-gbrain.lock 2>/dev/null || echo 0) ))
    if [ "$age" -gt 600 ]; then
      errors+=("stale sync lock (age=${age}s)")
    fi
  fi
  
  # Check 4: Concurrent write detection
  if [ -f ~/.gstack/.gbrain-sync-state.json ]; then
    if ! flock -n ~/.gstack/.gbrain-sync-state.json true 2>/dev/null; then
      errors+=("gbrain sync in progress (locked)")
    fi
  fi
  
  # Report
  if [ ${#errors[@]} -gt 0 ]; then
    printf '%s\n' "${errors[@]}"
    return 1
  fi
  return 0
}
```

### 2. Error Prevention (GUARD RAILS)

All skills MUST apply these guards BEFORE invoking gstack/gbrain/CRG:

**Timeout Guards:**
```bash
# ALL external calls need hard ceilings
export GBRAIN_TIMEOUT=120          # 2 min max per gbrain call
export GIT_TIMEOUT=30              # 30s for git operations
export CURL_CONNECT_TIMEOUT=10     # 10s connection timeout
export CURL_MAX_TIME=120           # 120s total timeout

# Usage pattern
timeout ${GBRAIN_TIMEOUT} gbrain search "term" || \
  { log "ERR gbrain timeout"; return 7; }
```

**Retry Guards:**
```bash
# Exponential backoff: 1s, 2s, 4s (max 3 attempts)
_retry_with_backoff() {
  local max_attempts=3 attempt=1 delay=1
  while [ $attempt -le $max_attempts ]; do
    "$@" && return 0
    if [ $attempt -lt $max_attempts ]; then
      sleep $delay
      delay=$((delay * 2))
    fi
    attempt=$((attempt + 1))
  done
  return 1
}

# Usage
_retry_with_backoff gbrain sources list --json
```

**Lock Guards:**
```bash
# Use advisory file locks to prevent concurrent writes
_with_lock() {
  local lockfile="$1" timeout=10 cmd=("${@:2}")
  local lockfd=3
  exec {lockfd}>"$lockfile"
  if ! flock -n -x -w $timeout $lockfd; then
    echo "ERR: could not acquire lock (another process writing)"
    return 8
  fi
  "${cmd[@]}"
  local ret=$?
  flock -u -x $lockfd
  exec {lockfd}>&-
  return $ret
}

# Usage
_with_lock ~/.gstack/.gbrain-sync-state.json gbrain sync --repo .
```

### 3. Error Handling (RECOVERY)

All skills MUST handle these exit codes:

| Code | Meaning | Recovery | Fatal |
|------|---------|----------|-------|
| 0 | Success | None | No |
| 1 | Generic error | Check stderr | Maybe |
| 7 | Timeout | Retry once, then fallback | Yes |
| 8 | Lock contention | Wait 30s and retry | Yes |
| 124 | Timeout (bash `timeout` cmd) | Retry once, then fallback | Yes |
| 127 | Command not found | Run setup script | Yes |

**Recovery Pattern:**
```bash
_handle_error() {
  local exit_code=$1 operation=$2
  case $exit_code in
    0) return 0 ;;
    7|124) 
      log "WARN $operation timed out — retrying once"
      sleep 2
      return 7  # Signal caller to retry
      ;;
    8)
      log "WARN $operation locked — waiting 30s"
      sleep 30
      return 8  # Signal caller to wait
      ;;
    127)
      log "ERR $operation not found — run /setup-gbrain or /mcp-install"
      return 1  # Fatal
      ;;
    *)
      log "ERR $operation failed (code $exit_code)"
      return 1
      ;;
  esac
}
```

### 4. Error Messages (FOR NEW AGENTS)

All skills MUST provide ACTIONABLE error messages. Template:

```bash
_err_actionable() {
  local symptom=$1 root_cause=$2 fix=$3
  cat <<EOF
❌ $symptom

ROOT CAUSE: $root_cause

FIX:
  $fix

IF THIS PERSISTS:
  1. Check gbrain status: gbrain doctor --fast
  2. Run self-heal: bash ~/.claude/skills/gstack/bin/gstack-gbrain-detect
  3. Open issue: https://github.com/diazMelgarejo/orama-system/issues
EOF
}

# Usage
_err_actionable \
  "gbrain search returned nothing" \
  "Code index not built for this repo" \
  "Run: /sync-gbrain --full --code-only"
```

### 5. Logging (FOR DIAGNOSTICS)

All skills MUST log to a central diagnostic file:

```bash
# Log path: ~/.openclaw/logs/gstack-gbrain-crg.log (mode 644, rotated weekly)
_log_diagnostic() {
  local level=$1 message=$2
  local logfile=~/.openclaw/logs/gstack-gbrain-crg.log
  mkdir -p "${logfile%/*}"
  local ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '[%s] %s %s\n' "$ts" "$level" "$message" >> "$logfile"
}

_log_diagnostic "INFO" "sync-gbrain started for $(pwd)"
_log_diagnostic "WARN" "gbrain autopilot jam detected (pid $ap_pid)"
_log_diagnostic "ERR" "sync failed (code $?): $(tail -1 /tmp/sync.log)"
```

### 6. Health Checks (AFTER OPERATIONS)

All skills MUST verify state after operations:

```bash
_health_check() {
  local operation=$1
  local checks_passed=0 checks_total=0
  
  # Check 1: gbrain CLI works
  checks_total=$((checks_total + 1))
  if gbrain doctor --fast --json 2>/dev/null | jq -e '.status == "ok"' >/dev/null 2>&1; then
    checks_passed=$((checks_passed + 1))
  fi
  
  # Check 2: CRG graph accessible (if used)
  checks_total=$((checks_total + 1))
  if command -v semantic_search_nodes_tool >/dev/null 2>&1; then
    checks_passed=$((checks_passed + 1))
  fi
  
  # Check 3: gstack config valid
  checks_total=$((checks_total + 1))
  if gstack-config get proactive >/dev/null 2>&1; then
    checks_passed=$((checks_passed + 1))
  fi
  
  log "health check after $operation: $checks_passed/$checks_total passed"
  [ "$checks_passed" -ge 2 ] && return 0 || return 1
}
```

## Implementation

### Phase 1: Core Framework (THIS SESSION)
1. ✅ Create this ADR (defines patterns)
2. ✅ Update `/sync-gbrain` wrapper in orama-system with pre-flight checks
3. ✅ Update all 5 orama-system skills using gbrain/gstack/CRG

### Phase 2: Broader Rollout
- Update PT .agents/skills/* that use gstack
- Update AlphaClaw Coil with same pattern
- Wire health checks into start.sh/start.ps1

### Phase 3: New Agent Onboarding
- Subagents in isolated sandboxes check for gstack/gbrain availability first
- Subagents log to central diagnostic file
- Subagents fail gracefully with actionable messages

## Benefits

| Benefit | Impact |
|---------|--------|
| **Upfront error detection** | Agents fail fast with clear root cause, not silent hangs |
| **Timeout safety** | No more 40+ min hangs; hard ceilings on all external calls |
| **Retry resilience** | Transient failures (network blips, locks) don't break workflow |
| **Diagnostic visibility** | Central log file (`gstack-gbrain-crg.log`) enables faster debugging |
| **New agent onboarding** | Clear error messages guide new agents to solutions |
| **Concurrent safety** | File locks prevent state corruption from parallel writes |

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Logs grow too large | Implement weekly rotation; keep 4 weeks |
| Timeout too aggressive | Make configurable via env var; default 120s is reasonable for gstack |
| Lock contention on shared state | Orchestrator already handles this; we're adding agent-side guard |

## References

- Memory: `gbrain-sync-durability.md`
- Memory: `feedback_hard_deadlines_no_hang.md`
- Docs: `docs/wiki/14-gbrain-checkpoint-rm-rf-bug.md`
- Script: `scripts/gbrain/gbrain-selfheal.sh`
- Skill: `~/.claude/skills/gstack/sync-gbrain/SKILL.md` (steps 1–5)

---

**Next:** Update individual skills to implement these patterns.
