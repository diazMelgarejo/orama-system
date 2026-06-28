# Win coder — bridge PR verify (v1, after autoresearcher)

**Assignee:** win (coder)  
**Topic:** code-review/bridge-merge  
**Fan-out:** 2026-06-28-coord-005  
**Priority:** 2 — **only after autoresearcher complete** (gpu-results-h5-final.md received)

## Task (v1 scope)

1. Confirm `subagent/win-coder/bridge-http-local` PR ready for operator review.
2. Run `preflight()` — expect `http-local` on Win GPU host.
3. Drop `win-bridge-pr-ready.md` to Mac peer.

## Queue

```powershell
python win_job_queue.py enqueue
python win_job_queue.py next coder
python win_job_queue.py complete coder --note "win-bridge-pr-ready.md"
```

## Learn

`learn.py` + `auto_dream.py` after drop (mirror `mac-joint-workflow-mirror.md`).
