# How to Harden gstack/gbrain/CRG Skills (ADR-045 Implementation)

**Updated:** 2026-07-04  
**Related:** `ADR-045-gstack-gbrain-crg-error-resilience.md`  
**Maintenance:** When skills are added or updated, apply these patterns.

## Overview

This guide shows how to update orama-system skills to use the error-resilience framework (ADR-045). The framework ensures:
- Pre-flight error detection
- Timeout safety on all external calls
- Retry logic with exponential backoff
- Actionable error messages for new agents
- Central diagnostic logging
- Post-operation health checks

## Framework Components

**Library:** `bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh`
**Documentation:** `bin/orama-system/scripts/lib/README.md`
**ADR:** `docs/adr/ADR-045-gstack-gbrain-crg-error-resilience.md`

## Step-by-Step Implementation

### 1. Identify Skills to Update

Skills that need updating are those that call:
- `gbrain` (search, sync, code-def, code-refs, doctor, etc.)
- `gstack-*` commands (gstack-gbrain-detect, gstack-config, etc.)
- CRG tools via MCP (detect_changes_tool, semantic_search_nodes_tool, etc.)

**Current priority list:**
1. `code-review/SKILL.md` — uses CRG tools
2. `mcp-install/SKILL.md` — sets up gstack/gbrain
3. `using-git-worktrees/SKILL.md` — registers worktree sources
4. `first-run-setup/SKILL.md` — bootstraps gstack/gbrain/CRG
5. `orama-gstack/SKILL.md` — gstack routing

### 2. Update Skill Preamble (Add Safety Hook)

Add this IMMEDIATELY after the `---` frontmatter, BEFORE any other code:

```bash
# Safety: Load error-resilience library for gstack/gbrain/CRG operations
SAFETY_LIB="$(cd "$(dirname "$BASH_SOURCE")" && pwd)/../../scripts/lib/gstack-gbrain-crg-safe.sh"
if [ ! -f "$SAFETY_LIB" ]; then
  SAFETY_LIB="$ORAMA_ROOT/bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh"
fi
if [ -f "$SAFETY_LIB" ]; then
  source "$SAFETY_LIB" || { echo "ERR: cannot load safety library"; exit 1; }
else
  echo "WARN: safety library not found at $SAFETY_LIB"
fi
```

### 3. Add Pre-Flight Checks

Add this BEFORE the first gstack/gbrain/CRG call:

```bash
# Pre-flight: Validate gstack/gbrain configuration
echo "=== Pre-flight checks ==="
if ! _detect_errors; then
  _err_actionable \
    "gstack/gbrain configuration invalid" \
    "$(gstack-gbrain-detect 2>&1 || echo 'gstack-gbrain-detect not found')" \
    "Run: /setup-gbrain or /mcp-install"
  return 1
fi
echo "✓ Pre-flight checks passed"
```

### 4. Guard External Calls

Wrap all gstack/gbrain/CRG calls with guards:

**Pattern A: Simple Command (No Arguments)**
```bash
# Before (UNSAFE):
gbrain search "pattern"

# After (SAFE):
_retry_with_backoff gbrain search "pattern" || {
  _err_actionable \
    "gbrain search failed" \
    "Network timeout or gbrain unavailable" \
    "Check: gbrain doctor --fast"
  return 1
}
```

**Pattern B: State-Modifying Command (Needs Lock)**
```bash
# Before (UNSAFE):
gbrain sync --repo . --source my-repo

# After (SAFE):
_with_lock ~/.gstack/.gbrain-sync-state.json \
  gbrain sync --repo . --source my-repo || {
  local ret=$?
  [ $ret -eq 8 ] && {
    _log_diagnostic "WARN" "sync locked; waiting 30s"
    sleep 30
    return 8  # Signal to caller to retry
  }
  return $ret
}
```

**Pattern C: Query with Error Handling**
```bash
# Before (UNSAFE):
local status=$(gbrain doctor --fast --json | jq -r '.status')

# After (SAFE):
local status=$(timeout ${GBRAIN_TIMEOUT} gbrain doctor --fast --json 2>/dev/null | \
  jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
if [ "$status" = "unknown" ]; then
  _err_actionable "cannot query gbrain status" "gbrain not responding" \
    "gbrain doctor --fast"
  return 1
fi
```

### 5. Add Post-Operation Health Checks

Add this after important operations:

```bash
echo "=== Health verification ==="
if _health_check "gbrain sync"; then
  echo "✓ gbrain is healthy after sync"
else
  _log_diagnostic "WARN" "health degraded after sync (may retry)"
fi
```

### 6. Centralize Error Handling

Replace ad-hoc error messages with actionable ones:

```bash
# Before (VAGUE):
if [ $ret -ne 0 ]; then
  echo "Error: command failed"
  return 1
fi

# After (ACTIONABLE):
if [ $ret -ne 0 ]; then
  _err_actionable \
    "gbrain source registration failed" \
    "Source already exists or permissions issue" \
    "gbrain sources list && grep -i 'my-repo'"
  return 1
fi
```

## Example: Updating code-review/SKILL.md

(This is a template — actual changes will vary per skill)

### Before (Unsafe):
```bash
# Step 3: Run code review using CRG
echo "Running code review..."
gstack-crg-probe --full || { echo "Error: CRG probe failed"; return 1; }
echo "Review complete"
```

### After (Safe with ADR-045):
```bash
# Safety: Load error-resilience library
SAFETY_LIB="$ORAMA_ROOT/bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh"
[ -f "$SAFETY_LIB" ] && source "$SAFETY_LIB" || { echo "ERR: safety lib missing"; exit 1; }

# Pre-flight checks
echo "=== Pre-flight checks ==="
if ! _detect_errors; then
  _err_actionable \
    "gstack/CRG configuration error" \
    "gbrain or gstack not properly configured" \
    "Run: /mcp-install"
  return 1
fi
echo "✓ Pre-flight passed"

# Step 3: Run code review using CRG (with guards)
echo "Running code review..."
_retry_with_backoff timeout ${GBRAIN_TIMEOUT} gstack-crg-probe --full || {
  local code=$?
  _err_actionable \
    "CRG probe failed" \
    "Code-review-graph unavailable or timeout" \
    "Check: semantic_search_nodes_tool status && gbrain doctor --fast"
  return 1
}

# Health check
if _health_check "code-review"; then
  echo "✓ Review complete, gstack/CRG healthy"
else
  _log_diagnostic "WARN" "CRG health degraded after review"
fi
```

## Testing Updates

After updating a skill, test it with these scenarios:

### Test 1: Normal Operation (Happy Path)
```bash
# Invoke skill normally
/skill-name

# Verify
grep "✓ Pre-flight" output
grep "✓ health" output
```

### Test 2: gbrain Offline
```bash
# Simulate offline
launchctl unload ~/Library/LaunchAgents/com.gbrain.* 2>/dev/null || true

# Invoke skill
/skill-name

# Expect: clear error message + recovery step
grep "gbrain configuration error\|cannot query gbrain" output
grep "Run: /setup-gbrain" output

# Restore
launchctl load ~/Library/LaunchAgents/com.gbrain.* 2>/dev/null || true
```

### Test 3: Lock Contention
```bash
# Simulate lock
touch ~/.gstack/.sync-gbrain.lock

# Invoke skill
timeout 5 /skill-name &
PID=$!

# Wait, then remove lock from another terminal
sleep 2
rm ~/.gstack/.sync-gbrain.lock

# Skill should retry after lock released
wait $PID
grep "lock contention\|waiting" output
```

### Test 4: Timeout
```bash
# Invoke with GBRAIN_TIMEOUT=2 (very short)
GBRAIN_TIMEOUT=2 /skill-name

# Expect: retry logic
grep "timed out\|retry" output
```

## Checklist for Skill Updates

- [ ] Source safety library in preamble
- [ ] Run `_detect_errors` before first external call
- [ ] Wrap `gbrain sync`, `gstack config set` with `_with_lock`
- [ ] Wrap read-only calls with `_retry_with_backoff`
- [ ] All external calls have timeout guards
- [ ] Error messages use `_err_actionable`
- [ ] Important operations have `_health_check`
- [ ] Central logging via `_log_diagnostic` for diagnostics
- [ ] Tested with gbrain offline (returns actionable error)
- [ ] Tested with lock contention (retries gracefully)
- [ ] Tested with timeout (retry + fallback)

## Maintenance

**When to update this guide:**
- New failure modes discovered → add to ADR-045 + library + here
- New helper function added → document in library README + here
- Skills added/updated → apply patterns + test

**How to test changes system-wide:**
```bash
# Run all gstack-based skills with safety checks
for skill in code-review mcp-install using-git-worktrees first-run-setup; do
  echo "Testing /orama-system:$skill ..."
  /orama-system:$skill --dry-run 2>&1 | grep -E "ERR|WARN|health" || echo "OK"
done
```

## References

- **ADR-045:** Full specification, root causes, solution rationale
- **Library README:** Function reference, exit codes, examples
- **Library source:** `bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh`
- **Logs:** `~/.openclaw/logs/gstack-gbrain-crg.log` (central diagnostic file)

## Questions?

- **"Where do I put the safety library?"** → `bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh` (tracked, shared by all skills)
- **"Can I modify the library?"** → Only if you've identified a NEW failure mode or bug. Document in ADR-045 first.
- **"What if my skill doesn't use gstack/gbrain/CRG?"** → Don't load the library (check will be automatic). This guide doesn't apply.
- **"How do I debug a timeout?"** → Check `~/.openclaw/logs/gstack-gbrain-crg.log` for the exact operation that timed out + stack.

---

**Last Updated:** 2026-07-04  
**Maintained By:** System Infrastructure Team  
**Status:** ACTIVE — apply to new skills immediately
