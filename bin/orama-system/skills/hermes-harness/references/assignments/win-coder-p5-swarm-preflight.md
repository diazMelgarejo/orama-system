# Win coder — P5 swarm HITL preflight (main gap report)

**Assignee:** win (coder)  
**Topic:** code-review/security-p5  
**Fan-out:** 2026-06-29-coord-016-mac  
**Priority:** 1

## Context

L1 comms blocked until P5 lands. Mac orchestrator wants P5 status before next operator merge.

## Task

1. Verify `sign_operator_payload` absent on `main`; swarm launch still uses `approved: true`.
2. Drop `win-p5-preflight-gap.md` to Mac with branch recommendation.
