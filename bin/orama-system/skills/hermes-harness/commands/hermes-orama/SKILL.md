---
name: hermes-orama
description: >
  (L-PT) Run the Orama 5-stage pipeline via Perpetua-Tools hermes_harness.py —
  sequential AIAgent.chat stages, not native Hermes delegate_task children.
  Context → Architect → Refiner → Executor/Verifier (parallel) → Crystallizer.
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
echo "🧠 L-PT: Orama 5-stage pipeline (PT hermes_harness, not delegate_task): $TASK"
python3 "$PERP_SCRIPT" "$TASK"
```

**Dispatch lane:** L-PT — [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md)
