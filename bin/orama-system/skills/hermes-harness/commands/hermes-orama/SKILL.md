---
name: hermes-orama
description: >
  Run the complete Orama 5-stage pipeline (Context → Architect → Refiner →
  Executor/Verifier → Crystallizer) by spawning Hermes AIAgent instances for
  each stage. Use for any complex task that benefits from multi-agent breakdown.
argument-hint: "<task description>"
disable-model-invocation: true
---
```bash
PERP_SCRIPT="$(git rev-parse --show-toplevel)/perpetua-tools/src/hermes_harness.py"
TASK="$*"
[ -z "$TASK" ] && echo "Usage: /hermes-orama <task description>" && exit 1
echo "🧠 Starting Orama 5-stage pipeline via Hermes for: $TASK"
python3 "$PERP_SCRIPT" "$TASK"
```
