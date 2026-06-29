# Win P5 swarm HITL preflight — gap on main

**Date:** 2026-06-29  
**Fan-out:** 2026-06-29-coord-016-mac  
**Job:** win-coder-p5-swarm-preflight.md

## Findings

| Check | Result |
|-------|--------|
| `sign_operator_payload` on `main` | **Absent** |
| `api_swarm_launch` | Still requires client `approved: true` (portal_server.py:2078) |
| L1 `l1_dispatch.py` gate | Exit 2 — correct until P5 lands |

## Recommendation

**Operator priority:** merge `cursor/security-pr3-swarm-approval-f559` (P5 plan T1–T7) before L1 `/api/l1/*`.

## Mac

Unblocks Win `win-coder-l1-comms-autoplan-backlog` after P5 acceptance criteria green.
