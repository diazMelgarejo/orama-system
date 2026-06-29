# Mac cycle 013 — coord_pulse P2.1 Mac parity

**Date:** 2026-06-29  
**Fan-out:** coord-013

## Shipped

- `coord_pulse.sh` — Win parity: `pulse-gate`, flock lock, git fetch, idle exit, job-specific spawn
- `mac_job_queue.py` — `pulse-gate`, `BLOCKED_PENDING`, blocked skip in `next`
- **7/7** unit tests

## Verify

```bash
./bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh --dry-run
```

Mac launchd pulse is now safe for unattended Tier-1 spawn (operator opt-in per autoplan P3).
