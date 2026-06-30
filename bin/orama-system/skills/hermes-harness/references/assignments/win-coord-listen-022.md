# Win assignment — 3×15m coord listen (coord-022)

**Date:** 2026-06-29  
**Mac tag:** `coord-022-gossip`

## Do

1. `git pull --rebase origin main` (orama + PT)
2. Run **3×15m listen** on Windows:
   ```powershell
   .\bin\orama-system\skills\hermes-harness\scripts\coord_monitor.ps1 -Minutes 45
   ```
   (45m = three 15m ticks: probe Mac peer, sync, queue gate)
3. If queue actionable, run one job then re-arm listen.
4. Post: `learn.py` one line + `auto_dream.py` + push PT + drop ack to Mac inbox.

## Mac context

- Pushed `docs/v2/43-gossipbus-mesh-transport.md` — listen logs are **not** GossipBus transport.
- P5 T2 preview signing landed on branch; T3 next.
- Mac running `job_cycle_listen.sh --rounds 3 --tag coord-022-gossip` in parallel.

## Ack filename

`win-coord-022-mac-gossip-ack.md`
