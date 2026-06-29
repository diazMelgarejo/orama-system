# Win coder — L1 intra-machine comms (deferred autoplan)

**Assignee:** win (coder)  
**Topic:** code-review/bridge-merge  
**Fan-out:** backlog-2026-06-29-l1-comms  
**Priority:** 99 — run after P5 swarm HITL lands on main

## Prerequisite (hard gate)

Land [`docs/plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](../../../../../../docs/plans/2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) on `main` first.

## Task (after P5 on main)

1. Read execution plan: `docs/plans/2026-06-29-intra-machine-l1-comms-execution-plan.md` (D1–D4 locked)
2. Run `/autoplan` on execution plan (CEO + Eng; Design for L1Composer UI)
3. Implement L1-T1..T9 (portal `/api/l1/*`, `l1_dispatch.py` un-gate, `L1Composer.tsx`)
4. Ingredients already on branch: schema, `l1_child_registry.py`, CLI stub

**Do not wire portal routes until P5 acceptance criteria green on `main`.**

**Frugal:** no new broker; reuse portal + Hermes envelope + ActionValidator.

## Queue

```powershell
# Enqueued after coord-006; do not claim until P5 merged
python win_job_queue.py enqueue
python win_job_queue.py next coder
```
