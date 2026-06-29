# Win cycle 014 — pulse parity + PT #199 merge-ready

**Date:** 2026-06-29  
**Fan-out:** coord-014

## Deliverables

1. `win-mac-pulse-comparison.md` — Win vs Mac harness pulse diff table
2. `coord_pulse.sh` — exit when `mac_job_queue` not idle (parity with Win skip-on-active)
3. `mac_job_queue.py` — bold `**Priority:**` regex (parity with Win)

## PT #199

| Check | Result |
|-------|--------|
| State | OPEN, MERGEABLE |
| Win tests | 15/15 `test_frugality_router.py` (prior cycle) |
| Recommendation | Operator `gh pr ready 199` + merge |

## Mac

Please ack `win-pt199-frugality-reconcile.md` and merge #199 when green.

Win queue idle; listening +15m (`coord_monitor`).
