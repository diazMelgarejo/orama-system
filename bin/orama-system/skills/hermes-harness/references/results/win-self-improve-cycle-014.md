# Win self-improve cycle 014 — Win/Mac pulse parity

**Date:** 2026-06-29

## Shipped

- Pulse comparison doc (`win-mac-pulse-comparison.md`)
- Mac `coord_pulse.sh` idle exit fix
- Mac `mac_job_queue` bold priority parse
- Cycle 014 drop to Mac peer

## Key insight

Win pulse is **queue-gated** (no spawn without actionable `win_job_queue` job). Mac pulse was **agent-always** after idle check; now exits when queue busy, still uses generic agent card when idle (inbox/backlog scan).

## Lessons batch

See PT `.agent` — 5 new graduated lessons from this cycle.
