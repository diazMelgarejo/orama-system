---
name: guard-sync-divergence
enabled: true
event: bash
action: warn
pattern: "sync-attribution-guard-scripts\\.sh"
---

# Guard sync divergence

Before syncing attribution guards, the divergence checker must pass (built into
`sync-attribution-guard-scripts.sh` unless `GUARD_SYNC_SKIP_DIVERGENCE_CHECK=1`).

Manual preflight:

```bash
bash scripts/git/check-guard-sync-divergence.sh --workspace
```

Optional explicit workspace root (defaults to parent of repo root):

```bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$REPO_ROOT/..}" \
  bash scripts/git/check-guard-sync-divergence.sh --workspace
```

If siblings carry guard mutations absent from orama canonical history, **stop** and
AskUserQuestions (HITL): commit sibling work, promote to orama on the **one open PR**
per repo, merge canonical, then sync downstream.

Never open fragmented one-file PRs. See
`bin/orama-system/skills/guard-sync-divergence-guard/SKILL.md`.
