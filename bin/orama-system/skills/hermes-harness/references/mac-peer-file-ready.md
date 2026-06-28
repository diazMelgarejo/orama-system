# Mac peer-file READY — re-drop deliverables

**Assignee:** win (Hermes co-orchestrator)  
**Topic:** ops/peer-file-unblock  
**Fan-out:** 2026-06-28-coord-002  
**Source:** mac (OpenClaw)

## Status

Mac `POST /api/peer-file` returns **200** after `cda6a68` + `./start.sh --lan-peer --no-open`.  
Probe: L2 PASS (`portal-health`, `portal-status`, `peer-lmstudio`). `ws-peer` SKIP is OK.

## Re-drop now (copy-paste)

```powershell
cd $env:ORAMA_SYSTEM_PATH
$py = ".venv\Scripts\python.exe"
& $py bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file tasks\gpu-results.md --assignee mac --topic autoresearch/results `
  --fanout-id 2026-06-28-autoresearch-001
& $py bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file tasks\win-code-review.md --assignee mac --topic code-review/autoresearch-bridge-done `
  --fanout-id 2026-06-28-code-sections-001
& $py bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file tasks\win-self-improve-runtime-results.md --assignee mac --topic self-improve/review `
  --fanout-id 2026-06-28-self-improve-001
```

## Mac will read

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --name gpu-results.md
```

## Platform reminder

- **Win:** Hermes-only + cursor-agent (local)
- **Mac:** OpenClaw + cursor-agent (local)
- Coordination = file inbox only
