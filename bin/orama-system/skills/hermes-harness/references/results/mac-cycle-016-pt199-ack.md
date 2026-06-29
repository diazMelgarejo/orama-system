# Mac cycle 016 — Win PT #199 merge ack + pulse parity closed

**Date:** 2026-06-29  
**Fan-out:** coord-016

## Received

- `win-pt199-merge-ack.md` — 53/53 on Win `main` after Mac merge
- `win-mac-pulse-comparison.md` — gap list (pre P2.1)

## Mac verify

- `test_frugality_router.py` + `test_autoresearch_bridge.py`: **53/53** on Mac PT `main`
- P2.1 landed coord-013: pulse-gate, flock, blocked list, job-specific spawn

## Dropped

Ack to Win peer; listen uses `job_cycle_listen.sh` (reset timer on each job_done).
