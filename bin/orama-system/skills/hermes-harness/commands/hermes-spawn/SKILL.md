---
name: hermes-spawn
description: >
  (L-PT) Start, stop, or check the Perpetua-Tools hermes_harness.py background
  session (PID-file lifecycle). Not native Hermes delegate_task (L-H1) and not
  fleet cursor-agent dispatch (L-Fleet). Requires credentials in the process
  environment; missing variables fail clearly (no automatic .env loading).
argument-hint: "<start|stop|status> [task description]"
disable-model-invocation: true
---
```bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
exec bash "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh" "$@"
```

**Dispatch lane:** L-PT — [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md)
