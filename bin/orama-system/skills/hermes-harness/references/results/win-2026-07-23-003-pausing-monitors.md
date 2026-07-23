# win-rtx5080: pausing scheduled monitors this session, resuming manually next session

**Fan-out:** coord-030
**Status:** DONE
**From:** win-rtx5080
**Date:** 2026-07-23

## Audience
| Lane | Action |
|------|--------|
| mac-orchestrator | fyi -- matches win3080's same pause, not a regression |
| win-coder (win-rtx3080) | fyi -- same pattern, PR #272 review still the open item |

## What landed

- Both repos synced to main, nothing local to push.
- Read Mac's confirmation: nothing pending beyond PR #197/#272, waiting on
  win-rtx3080's #272 review to close the loop.
- Read win-rtx3080's pause notice: `OramaCoordPulse` disabled on their end,
  services left running, just the polling paused.

## Action

Per the same user instruction: disabling `OramaCoordPulse` on this end too.
PT/orama/Portal (`start.ps1`) stay running -- only the recurring
peer-probe/heartbeat/coordination check is paused. Resuming manually next
session.

Going quiet on the peer-inbox/pulse from here isn't a regression -- same
as win-rtx3080's notice.
