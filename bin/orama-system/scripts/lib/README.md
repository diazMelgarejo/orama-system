# Shared Script Libraries

## gstack-gbrain-crg-safe.sh

**Purpose:** Error-resilient utility functions for skills that use gstack, gbrain, or code-review-graph.

**Problem it solves:**
- gbrain/gstack calls fail silently or hang without clear error messages
- Concurrent writes corrupt state files
- Timeout handling inconsistent across skills
- New agents don't know how to recover from errors

**When to use:**
ANY skill that calls:
- `gstack-*` commands
- `gbrain` commands (search, sync, code-def, code-refs, etc.)
- CRG tools (detect_changes_tool, semantic_search_nodes_tool, etc.)

**How to use:**

```bash
#!/usr/bin/env bash
set -uo pipefail

# 1. Source the library at the start of your skill
source "$(dirname "$0")/lib/gstack-gbrain-crg-safe.sh" || exit 1

# 2. Run pre-flight checks BEFORE any gstack/gbrain work
if ! _detect_errors; then
  _err_actionable \
    "gbrain/gstack configuration error" \
    "$(gstack-gbrain-detect 2>&1 | grep -o '"gbrain_local_status":[^}]*')" \
    "Run /setup-gbrain or /mcp-install"
  return 1
fi

# 3. Use guards for sensitive operations
_with_lock ~/.gstack/.gbrain-sync-state.json \
  gbrain sync --repo . --source my-repo

# 4. Use retry logic for transient failures
_retry_with_backoff gbrain search "term" || {
  _err_actionable "gbrain search failed" "Network timeout" "Check internet connection"
  return 1
}

# 5. Handle errors with context
gbrain doctor --fast --json || {
  local code=$?
  local msg=$(_handle_error "$code" "gbrain doctor")
  case "$msg" in
    TIMEOUT) echo "gbrain timed out; retrying..."; sleep 2; return 7 ;;
    FAILED)  echo "gbrain is broken"; return 1 ;;
  esac
}

# 6. Verify after important operations
if _health_check "gbrain sync"; then
  echo "Success: gbrain is healthy"
else
  _log_diagnostic "WARN" "health check failed after gbrain sync"
fi
```

**All available functions:**

| Function | Usage | Returns |
|----------|-------|---------|
| `_detect_errors` | Pre-flight validation | 0=pass, 1=fatal error, else=warnings |
| `_retry_with_backoff <cmd> [args]` | Retry with exponential backoff | exit code of command |
| `_with_lock <file> <cmd> [args]` | Run under file lock | 0=success, 8=lock contention, else=command error |
| `_handle_error <code> <op>` | Interpret exit code | Prints `TIMEOUT`, `LOCK_CONTENTION`, `NOT_FOUND`, or `FAILED` |
| `_err_actionable <symptom> <cause> <fix>` | Print error + recovery steps | Always 0 (message to stderr) |
| `_log_diagnostic <level> <msg>` | Log to central file | 0 |
| `_health_check <op>` | Verify post-operation | 0=healthy, 1=degraded |

**Exit codes to expect:**

| Code | Meaning | Recovery |
|------|---------|----------|
| 0 | Success | None |
| 1 | Generic error | Check logs; consult ADR-045 |
| 7 | Timeout (gstack/gbrain) | Retry once; check network |
| 8 | Lock contention | Wait 30s; retry |
| 124 | Timeout (bash `timeout` cmd) | Same as 7 |
| 127 | Command not found | Run /setup-gbrain |

**Central diagnostic log:**

All operations log to `~/.openclaw/logs/gstack-gbrain-crg.log`:

```bash
# View recent entries
tail -20 ~/.openclaw/logs/gstack-gbrain-crg.log

# Filter by level
grep "ERR " ~/.openclaw/logs/gstack-gbrain-crg.log | tail -10

# Filter by operation
grep "gbrain sync" ~/.openclaw/logs/gstack-gbrain-crg.log
```

**See also:**
- `ADR-045-gstack-gbrain-crg-error-resilience.md` — full specification
- `bin/orama-system/skills/code-review/SKILL.md` — example usage (see Step X)
