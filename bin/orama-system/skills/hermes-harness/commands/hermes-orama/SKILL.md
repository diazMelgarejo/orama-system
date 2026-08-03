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
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# shellcheck source=../../scripts/resolve_perp_harness.sh
source "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"
PERP_SCRIPT="$(resolve_perp_harness_script)"
TASK="$*"
[ -z "$TASK" ] && echo "Usage: /hermes-orama <task description>" && exit 1
echo "🧠 Starting Orama 5-stage pipeline via Hermes for: $TASK"
python3 "$PERP_SCRIPT" "$TASK"
```
