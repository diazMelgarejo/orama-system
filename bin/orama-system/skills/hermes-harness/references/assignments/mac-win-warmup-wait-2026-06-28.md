# Mac → Win: 15-minute warmup wait

**Topic:** ops/warmup-wait  
**Date:** 2026-06-28

Mac co-orchestrator is in **wait mode** for ~15 minutes while Win stack warms.

## Win actions during warmup

1. `git fetch origin --prune && git pull --rebase origin main` (need `abea96e` macos/windows skins)
2. Optional: continue `win/peer-inbox-portal` — merge notes incoming from Mac
3. `.\platform\windows\start.ps1 --lan-peer --no-open`
4. Open `http://localhost:8002/co-orchestration/windows`
5. When ready, drop any new deliverables to Mac: `drop --peer`

## Mac polling

Checking inbox every **5 minutes** for new Win drops.
