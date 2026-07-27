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
# Detect harness root (path-agnostic, follows symlink like cc-openclaw)
HARNESS_ROOT="$(python3 -c "import hermes; print(hermes.__file__)" 2>/dev/null | sed 's|/hermes/__init__.py||' || echo "$HOME/.hermes")"
PERP_SCRIPT="$(git rev-parse --show-toplevel 2>/dev/null)/perpetua-tools/src/hermes_harness.py"

ACTION="${1:-status}"
TASK="${2:-}"

case "$ACTION" in
  start)
    echo "🚀 Spawning Hermes agent for: $TASK"
    python3 "$PERP_SCRIPT" "$TASK"
    ;;
  stop)
    pkill -f "hermes" && echo "✅ Hermes stopped" || echo "ℹ️ No Hermes process found"
    ;;
  status)
    python3 -c "from run_agent import AIAgent; a = AIAgent(quiet_mode=True, skip_memory=True); print(a.chat('Reply with: HERMES_OK'))"
    ;;
esac
```
