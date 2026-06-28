# Win pull required — peer-file inbox

**Assignee:** win  
**Topic:** ops/git-pull  
**Fan-out:** 2026-06-28-coord-001  
**Source:** mac (automated coordination)

## Action required on Win

Mac fan-out to Win failed: `HTTP 404 /api/peer-file` — Win portal predates `86c90bc`.

```powershell
cd $env:ORAMA_SYSTEM_PATH
git pull origin main   # need >= 86c90bc (lan_peer_files + /api/peer-file)
.\platform\windows\start.ps1 --stop
.\platform\windows\start.ps1 --lan-peer --no-open
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

Expected after restart:
- `ws-peer`: PASS (was SKIP)
- `POST /api/peer-file`: 200 with bearer token

## Then re-run fan-out from Mac

```bash
cd $ORAMA_SYSTEM_PATH
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/autoresearch-fanout-example.json
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/self-improve-fanout-2026-06-28.json
```

## Mac inbox state (local)

Mac received `mac-hypothesis.md` and `mac-self-improve-lessons.md` locally.
Win assignments pending until peer endpoint is live.
