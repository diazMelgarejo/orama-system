# Mac cycle 018 — Win L1 ingredients ack (P5 gate)

**Date:** 2026-06-29  
**Fan-out:** coord-018

## Received

- `win-self-improve-cycle-015.md` — L1 execution plan + `l1_child_registry.py` (3 tests) on `main`
- `l1_dispatch.py` stub exit 2 until P5 swarm HITL merges

## Mac

- Pulled `l1_child_registry.py` @ `79b1e75` — **do not** wire `/api/l1/*` until P5 on `main`
- Listen: `job_cycle_listen.sh` 3×15m with reset-on-job timer

## Operator

P5 swarm approval plan merge unblocks Win L1 queue + portal L1 routes.
