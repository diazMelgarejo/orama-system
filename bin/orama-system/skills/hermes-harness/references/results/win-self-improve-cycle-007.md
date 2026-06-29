# Win self-improve cycle 007 — Hermes coord pulse (Win P3)

**Date:** 2026-06-29  
**AFRP:** Type C | Practitioner | Mode 2

## Shipped (plan + scripts)

- `coord_pulse.ps1` — Win one-shot pulse: lock, probe, enqueue, skip blocked L1, cursor-agent ONE job
- `install_coord_pulse.ps1` — Task Scheduler `OramaCoordPulse` every 900s
- `coord-pulse-plan.md` — bidirectional Hermes pulse table (Mac launchd + Win task)

## Pending queue (no execution)

| Job | Status |
|-----|--------|
| `win-coder-l1-comms-autoplan-backlog.md` | **Blocked** on P5 swarm HITL — pulse skips via `$BlockedPending` |

## Operator install (Win)

```powershell
$env:ORAMA_SYSTEM_PATH = "C:\...\orama-system"
$env:PERPETUA_TOOLS_PATH = "C:\...\Perpetua-Tools"
.\scripts\install_coord_pulse.ps1 -Status
.\scripts\install_coord_pulse.ps1
```

Dry-run: `.\bin\orama-system\skills\hermes-harness\scripts\coord_pulse.ps1 -DryRun`

## Mac parity

Mac already has `install_coord_pulse.sh` + `coord_pulse.sh`. Both hosts listen via `probe_lan_peer.py`; transport remains file inbox + `win_job_queue`.
