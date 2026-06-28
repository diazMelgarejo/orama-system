# Mac self-improve cycle 003 — summary

**Fan-out:** `2026-06-28-coord-003`  
**Author:** mac (orchestrator)  
**Branch:** `subagent/mac-orchestrator/self-improve-memory`  
**Topic:** self-improve/lessons

## Done

| Item | Result |
|------|--------|
| Inbox read | `win-self-improve-runtime-results.md`, `self-improve-merge-final-proposed.md` |
| Portal merge notes | `references/results/mac-win-portal-merge-notes.md` (local ref; not in inbox) |
| PT landmark | `.agent/memory/working/COORDINATED_CYCLE_003_2026-06-28.md` |
| Branch pushed | `subagent/mac-orchestrator/self-improve-memory` |

## Branch policy (applied)

- `subagent/<role>/<short-topic>` from latest `origin/main`
- One branch per subagent; coordination via file inbox on `main`
- Operator PR merge after cycle; **`approve lessons`** gate for `docs/LESSONS.md`

## Cycle 003 subagents

| Host | Subagent | Branch | Deliverable |
|------|----------|--------|-------------|
| Mac | mac-researcher | `subagent/mac-researcher/h4-mac-benchmark` | `mac-h4-comparison.md` |
| Mac | orchestrator | `subagent/mac-orchestrator/self-improve-memory` | this file |
| Win | autoresearcher | `subagent/win-autoresearcher/h5-gpu-harness` | `gpu-results-h5.md` |
| Win | coder | `subagent/win-coder/bridge-http-local` | `win-bridge-spike-notes.md` |

## Self-improve status

- Win runtime results: PROPOSED merge with Mac lessons draft
- Final merge proposal: PROPOSED — operator **`approve lessons`** required
- No `docs/LESSONS.md` commit this cycle (operator gate)

## Files changed (Mac orchestrator branch)

- `Perpetua-Tools/.agent/memory/working/COORDINATED_CYCLE_003_2026-06-28.md`
- Optional: `.agent/memory/` learn.py lesson for subagent branch policy
