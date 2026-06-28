# Subagent Git branch policy — co-orchestration mutations

**Date:** 2026-06-28  
**Review:** operator merges via PR after cycle; do not merge to `main` without review.

## Naming

```
subagent/<role>/<short-topic>
```

Examples:
- `subagent/mac-researcher/h4-mac-benchmark`
- `subagent/mac-orchestrator/self-improve-memory`
- `subagent/win-autoresearcher/h5-gpu-harness`
- `subagent/win-coder/bridge-http-local`

## Rules

1. Branch from latest `origin/main` in the repo you touch (orama-system and/or Perpetua-Tools).
2. One branch per subagent task; push with `git push -u origin <branch>`.
3. Drop `BRANCH.md` in assignment reply listing branch URL and files changed.
4. Coordination stays on `main` via file inbox — branches are for **mutations only**.
5. No force-push; no secrets in commits.

## Review later

Operator runs `gh pr create` from each branch when ready.
