# Win self-improve assignment

**Assignee:** win (autoresearcher + PT runtime)  
**Topic:** self-improve/gpu-runtime  
**Fan-out:** 2026-06-28-self-improve-001

## Objective

Document Win-side runtime lessons from LAN peer bring-up. Read Mac hypothesis/lessons from peer inbox before drafting.

## Scope (Win)

1. Pull orama `>= 86c90bc`, restart `start.ps1 --lan-peer`
2. P2P endpoints: `/api/peer-file`, `/api/peer-inbox`, `/ws/portal-peer`
3. PT `.state/control_plane_token` vs `ORAMA_CONTROL_PLANE_TOKEN` (joint mode)
4. GPU autoresearch routes + 27B stack readiness

## Steps

1. `git pull` orama-system; restart portal with `--lan-peer`
2. `probe_lan_peer.py --json` — target `ws-peer: PASS` after restart
3. `lan_peer_assign.py --peer list` — read `mac-self-improve-lessons.md` or autoresearch files
4. Draft `win-runtime-lessons.md` (PT memory landmark, no secrets)

## Deliverable

Drop `win-self-improve-runtime-results.md` to Mac peer inbox:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file .\win-runtime-lessons.md `
  --filename win-self-improve-runtime-results.md `
  --assignee mac --topic self-improve/review `
  --fanout-id 2026-06-28-self-improve-001
```
