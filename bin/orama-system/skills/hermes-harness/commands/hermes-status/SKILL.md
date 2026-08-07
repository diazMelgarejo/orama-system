---
name: hermes-status
description: >
  Read-only Hermes health rollup: PT root, spawn session, partner canaries, profiles,
  plus Appendix C platform gaps as not_yet_implemented stub rows. Use --json for
  canonical envelope output.
argument-hint: "[--json] [--skip-canaries]"
disable-model-invocation: true
---
```bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export REPO_ROOT
exec python3 "${REPO_ROOT}/bin/orama-system/skills/hermes-harness/scripts/hermes_status.py" "$@"
```

**Dispatch lane:** L-PT — [`references/hermes-dispatch-taxonomy.md`](../../references/hermes-dispatch-taxonomy.md)
