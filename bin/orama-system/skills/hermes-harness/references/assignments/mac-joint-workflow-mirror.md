# Mac → Win — joint workflow mirror (coord-005)

**Assignee:** win (orchestrator)  
**Topic:** ops/co-orchestration-active  
**Fan-out:** 2026-06-28-coord-005

## One job at a time (both sides)

| Host | Mechanism |
|------|-----------|
| Mac | Drop **one** Win assignment per role per round; autoresearcher before coder |
| Win | `win_job_queue.py` — one active job per role; LM Studio single-tenant |

## After each coord round (both hosts)

```powershell
cd $env:PERPETUA_TOOLS_PATH
python .agent/tools/learn.py "<one-line lesson from the round>" --rationale "coord-005 joint workflow"
python .agent/memory/auto_dream.py
git add .agent/memory && git commit -m "memory: coord round learn" && git push
```

## v1 scope guard

Stay inside `docs/plans/2026-05-29-03-v1.1-definitive.md` frugality tiers (0–2 local-first).  
LAN inbox is operational harness — not a new architecture track.

## Mac monitor

`http://localhost:8002/co-orchestration/macos` · poll `probe_lan_peer.py --json` every 2–3 min during active cycles.
