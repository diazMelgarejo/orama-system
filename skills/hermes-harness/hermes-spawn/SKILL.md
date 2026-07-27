---
name: hermes-spawn
description: >
  Start, stop, or check a Hermes AIAgent session programmatically.
  Use when you need to spawn a Hermes agent for a task, check its status,
  or stop a running session. Resolves all credentials from .env automatically.
argument-hint: "<start|stop|status> [task description]"
disable-model-invocation: true
---
```bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_ROOT="$(python3 -c "import hermes; print(hermes.__file__)" 2>/dev/null | sed 's|/hermes/__init__.py||' || echo "${HERMES_HOME:-$HOME/.hermes}")"
PERP_SCRIPT="${REPO_ROOT}/perpetua-tools/src/hermes_harness.py"
PID_FILE="${TMPDIR:-/tmp}/hermes-spawn.pid"

ACTION="${1:-status}"
shift || true
TASK="$*"

case "$ACTION" in
  start)
    if [[ -z "$TASK" ]]; then
      echo "Usage: start <task description>" >&2
      exit 1
    fi
    echo "🚀 Spawning Hermes agent for: $TASK"
    (cd "$HARNESS_ROOT" && python3 "$PERP_SCRIPT" "$TASK") &
    echo $! >"$PID_FILE"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]]; then
      pid="$(cat "$PID_FILE")"
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" && echo "✅ Hermes stopped (pid $pid)"
      else
        echo "ℹ️ No active Hermes process for pid $pid"
      fi
      rm -f "$PID_FILE"
    else
      echo "ℹ️ No Hermes pid file at $PID_FILE"
    fi
    ;;
  status)
    (cd "$HARNESS_ROOT" && python3 -c "from run_agent import AIAgent; a = AIAgent(quiet_mode=True, skip_memory=True); print(a.chat('Reply with: HERMES_OK'))")
    ;;
  *)
    echo "Unknown action: $ACTION (expected start|stop|status)" >&2
    exit 1
    ;;
esac
```
