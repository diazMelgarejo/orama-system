# Win autoresearcher — finalize H5 cross-host (v1 frugality)

**Assignee:** win (autoresearcher)  
**Topic:** autoresearch/gpu-done  
**Fan-out:** 2026-06-28-coord-005  
**Priority:** 1 — **only active autoresearcher job this round**

## Task (v1 Tier 1 — no cloud)

1. Read Mac peer inbox: `mac-h5-comparison.md` (dropped coord-004).
2. Update `gpu-results-h5-cross.md` with closed H5 table (Mac 3/3 vs Win 3/3).
3. State one-line frugality tier used per step (Ladder B1).
4. Drop `gpu-results-h5-final.md` to Mac peer.

## Queue discipline

```powershell
python win_job_queue.py enqueue
python win_job_queue.py next autoresearcher
# complete only after drop:
python win_job_queue.py complete autoresearcher --note "gpu-results-h5-final.md"
```

**Do not start coder job** until autoresearcher `complete`. Mac sends coder card separately.

## Learn (mirror Mac)

After drop: `python .agent/tools/learn.py` one session lesson + `python .agent/memory/auto_dream.py`.
