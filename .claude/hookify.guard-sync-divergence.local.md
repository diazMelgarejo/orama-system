---
name: guard-sync-divergence
enabled: true
event: bash
action: block
pattern: "sync-attribution-guard-scripts\\.sh"
---

# Guard sync divergence

Guard sync blocked until sibling divergence check passes.

Run:

```bash
WORKSPACE_ROOT=/agent/repos bash scripts/git/check-guard-sync-divergence.sh --workspace
```

If siblings carry guard mutations absent from orama canonical history, **stop** and
AskUserQuestions (HITL): commit sibling work, promote to orama on the **one open PR**
per repo, merge canonical, then sync downstream.

Never open fragmented one-file PRs. See
`bin/orama-system/skills/guard-sync-divergence-guard/SKILL.md`.
