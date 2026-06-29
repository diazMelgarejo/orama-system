# Win coder — L1 intra-machine comms (deferred autoplan)

**Assignee:** win (coder)  
**Topic:** code-review/bridge-merge  
**Fan-out:** backlog-2026-06-29-l1-comms  
**Priority:** 99 — run after P5 swarm HITL lands on main

## Prerequisite (hard gate)

Land [`docs/plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](../../../../../../docs/plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) on `main` first.

## Task (future)

1. Read draft: `docs/plans/2026-06-29-intra-machine-l1-comms-draft.md`
2. Run `/autoplan` on that plan (CEO + Eng; Design if portal UI)
3. Implement `/api/l1/preview` + `/api/l1/launch` piggybacking P5 HMAC helpers
4. Add `l1_dispatch.py` CLI + Ladder G in graceful-degradation.md

**Frugal:** no new broker; reuse portal + Hermes envelope + ActionValidator.

## Queue

```powershell
# Enqueued after coord-006; do not claim until P5 merged
python win_job_queue.py enqueue
python win_job_queue.py next coder
```
