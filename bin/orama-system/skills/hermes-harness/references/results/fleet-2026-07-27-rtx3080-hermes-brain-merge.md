# Fleet: RTX 3080 Hermes brain merge (operator now)

**Fan-out:** coord-035  
**Status:** ACTIVE — 3080 portal UP at **192.168.9.18** (DHCP drift from 192.168.9.240)  
**From:** mac-orchestrator  
**Date:** 2026-07-27

## Mac probe (now)

- `192.168.9.18:1234` LM Studio — **UP**
- `192.168.9.18:8002/health` — **UP**
- `192.168.9.240` (stale WIN_3080_IP) — **DOWN**

Update `WIN_3080_IP` + `LM_STUDIO_WIN_ENDPOINTS` in the repo-local env policy file after merge.

## On 3080 — run PowerShell script

Copy from Mac USB or pull from the operator references tree under `$OPENCLAW_ROOT/references/`:

`2026-07-27-rtx3080-hermes-brain-merge-runbook.ps1` (workspace-level operator doc; not tracked in this repo)

```powershell
powershell -ExecutionPolicy Bypass -File .\2026-07-27-rtx3080-hermes-brain-merge-runbook.ps1
```

## Hybrid merge summary

1. `hermes backup`
2. Paste Mac `GOSSIP_SHARED_SECRET` into orama repo-local env policy file
3. `install-hermes-harness.ps1 -RunDoctor` (profiles --sync + thin wrappers)
4. Optional: import `hermes-agent-openclaw-workspace-2026-07-27.zip` → `hermes-monitor` profile

SSoT catalogue: `2026-07-27-comprehensive-catalogue-hermes-profiles.md` under `$OPENCLAW_ROOT/references/` (workspace-level operator doc; not tracked in this repo)
