# Win deliverable — mac co-orchestrator playbook update

**Date:** 2026-06-29  
**Fan-out:** coord-021  
**Branch:** `subagent/win-coder/mac-co-orchestrator-playbook`

## Change

Added § `swarm_state.md` ownership table to `mac-co-orchestrator-playbook.md`:

- Mac orchestrator owns swarm state when evaluator runs Mac-side
- Win coder updates via inbox handoff (`drop --peer`)
- SSH vs HTTP-local gap noted (ack only, no code change)

## Cross-read

- `mac-ack-win-code-review.md` — findings accepted
- `mac-hypothesis-h6-real-task.md` — Mac dropped real H6 autoresearch card (researcher backlog)
